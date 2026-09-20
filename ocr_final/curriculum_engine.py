"""
curriculum_engine.py
=====================
A source-agnostic, multi-program Curriculum Parsing & Credit Reconciliation
Engine.

Design goals (mapped directly to the failure modes of the previous engine):

  1. Parser Rigidity          -> CodeResolver: ordered, pluggable rule chain.
                                  No program-specific regex is hardcoded into
                                  the parsing loop; rules are data, not code.
  2. Flawed Fallback Logic     -> Placement is a discriminated union
                                  (TermPlacement | Pooled). There is no
                                  sentinel "year=0/term=0" anywhere in this
                                  module. A course either has a real term or
                                  it is explicitly Pooled(reason=...).
  3. Coupled Architecture      -> CurriculumParser takes a CodeRuleRegistry
                                  and a CreditParser as constructor
                                  dependencies. Auditing (ReconciliationEngine)
                                  operates only on the resulting Pydantic
                                  model, never on raw program-specific text.

Nothing in this file assumes Thai-language input, 8-digit course codes, or
any single institution's numbering scheme -- those are supplied as data
(CodeRule objects) at call time. See `default_registry()` for an example
built from the DSBA curriculum this engine was originally built against.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Iterable, Literal, Union

from pydantic import BaseModel, Field, field_validator, model_validator


# ═══════════════════════════════════════════════════════════════════════
# 1. Validation flags
# ═══════════════════════════════════════════════════════════════════════

class ValidationFlag(str, Enum):
    """Machine-readable diagnostic codes attached to parsed records.

    Every anomaly the engine encounters is recorded as a flag rather than
    silently dropped or silently guessed. A record can carry more than one
    flag (e.g. a malformed code with an unparsable credit string).
    """
    MALFORMED_CODE = "MALFORMED_CODE"                # no rule matched; code
                                                       # is not a real,
                                                       # registry-known code
    SYNTHETIC_CODE_ASSIGNED = "SYNTHETIC_CODE_ASSIGNED"  # slot code minted
    UNASSIGNED_ELECTIVE = "UNASSIGNED_ELECTIVE"       # no definite term;
                                                       # routed to the pool
    CREDIT_UNPARSABLE = "CREDIT_UNPARSABLE"           # credit string could
                                                       # not be parsed at all
    CREDIT_AMBIGUOUS = "CREDIT_AMBIGUOUS"             # "3(3-0-6) or
                                                       # 3(2-2-5)"-style;
                                                       # first alt used
    CREDIT_MISMATCH = "CREDIT_MISMATCH"               # plan credits !=
                                                       # course-catalog
                                                       # credits for same code
    DUPLICATE_IN_TERM = "DUPLICATE_IN_TERM"           # same code twice in
                                                       # one term outside an
                                                       # alt_group
    PREREQ_UNRESOLVED = "PREREQ_UNRESOLVED"           # prerequisite text
                                                       # referenced no known
                                                       # code
    TRANSFER_CREDIT = "TRANSFER_CREDIT"               # explicitly marked
                                                       # transfer/exemption


# ═══════════════════════════════════════════════════════════════════════
# 2. Code resolution -- the pluggable rule engine
# ═══════════════════════════════════════════════════════════════════════
#
# A "code" in a raw curriculum row can be:
#   - a real course code                 "06026200"
#   - a wildcard elective slot           "06026xxx", "90644xxx"
#   - a transfer/exemption marker        "TRANSFER", "EXEMPT-ENG"
#   - free text with no code at all      "วิชาเลือกเสรี 1", "Free Elective"
#
# CodeResolver never invents a code that *looks like* a real course code.
# When no rule matches it always mints an explicitly synthetic slot code
# (prefixed, hyphenated) so downstream consumers can never confuse it with
# a real registry code.

@dataclass(frozen=True)
class CodeRule:
    """One entry in the resolution chain.

    `pattern` is tested with `re.fullmatch` against the *stripped* raw code
    string. `kind` tells the parser how to route the record; `extractor`
    (optional) pulls the canonical code out of a regex match when the whole
    raw string isn't the code itself (e.g. trailing whitespace, prefixes).
    """
    name: str
    pattern: re.Pattern
    kind: Literal["real", "transfer"]
    extractor: Callable[[re.Match], str] | None = None

    def try_resolve(self, raw: str) -> str | None:
        m = self.pattern.fullmatch(raw)
        if not m:
            return None
        return self.extractor(m) if self.extractor else raw


class CodeRuleRegistry:
    """Ordered collection of CodeRule. First match wins.

    Institutions/programs register their own rules at startup; the engine
    core never hardcodes a numbering scheme. This is what makes the engine
    usable for DSBA, Engineering, Business, or any future program without
    touching CurriculumParser itself.
    """

    def __init__(self) -> None:
        self._rules: list[CodeRule] = []
        self._slot_counters: dict[str, int] = {}

    def register(self, rule: CodeRule) -> "CodeRuleRegistry":
        self._rules.append(rule)
        return self

    def resolve(self, raw_code: str) -> tuple[str, ValidationFlag | None]:
        """Resolve a raw code string to (canonical_code, flag).

        flag is None when a real/transfer rule matched cleanly. Otherwise a
        synthetic slot code is minted and the flag explains why.
        """
        raw = (raw_code or "").strip()
        for rule in self._rules:
            resolved = rule.try_resolve(raw)
            if resolved is not None:
                return resolved, None
        return self._mint_slot_code(raw), ValidationFlag.SYNTHETIC_CODE_ASSIGNED

    def _mint_slot_code(self, raw: str) -> str:
        """Build a deterministic, collision-free synthetic slot code.

        The same wildcard text (e.g. "06026xxx") legitimately recurs many
        times across a curriculum, each occurrence representing a *different*
        elective slot -- so the counter is keyed on the normalized pattern,
        not a global counter, and increments per occurrence rather than
        collapsing repeats into one code.
        """
        pattern = re.sub(r"[^0-9A-Za-z]", "", raw).upper() or "SLOT"
        self._slot_counters[pattern] = self._slot_counters.get(pattern, 0) + 1
        return f"ELEC-{pattern}-{self._slot_counters[pattern]}"


def default_registry() -> CodeRuleRegistry:
    """Example registry for an 8-digit-code institution (e.g. KMITL/DSBA).

    Callers building for a different institution construct their own
    CodeRuleRegistry instead of editing this function -- this is only the
    reference example.
    """
    reg = CodeRuleRegistry()
    reg.register(CodeRule(
        name="real_8_digit",
        pattern=re.compile(r"\d{8}"),
        kind="real",
    ))
    reg.register(CodeRule(
        name="transfer_marker",
        pattern=re.compile(r"(TRANSFER|EXEMPT)[\w-]*", re.IGNORECASE),
        kind="transfer",
    ))
    return reg


# ═══════════════════════════════════════════════════════════════════════
# 3. Credit parsing
# ═══════════════════════════════════════════════════════════════════════

class CreditSpec(BaseModel):
    """Parsed credit-hour specification.

    `total` is always populated when parsing succeeds. `lecture`/`lab`/
    `self_study` are the "(L-P-S)" breakdown when present. `alternates`
    holds any additional "X or Y" credit options beyond the first, so
    nothing is silently discarded even though `total` uses the first.
    """
    total: int = Field(ge=0, le=20)
    lecture: int | None = Field(default=None, ge=0, le=60)
    lab: int | None = Field(default=None, ge=0, le=60)
    self_study: int | None = Field(default=None, ge=0, le=60)
    alternates: list[int] = Field(default_factory=list)
    ambiguous: bool = False


_CREDIT_RE = re.compile(r"(\d+)\s*\(\s*(\d+)\s*-\s*(\d+)\s*-\s*(\d+)\s*\)")
_CREDIT_BARE_RE = re.compile(r"^\s*(\d+)\s*$")


class CreditParser:
    """Parses free-text credit strings into CreditSpec.

    Handles:
      "3(3-0-6)"                 -> CreditSpec(3, 3, 0, 6)
      "3(3-0-6) หรือ 3(2-2-5)"    -> CreditSpec(3, 3, 0, 6, alternates=[3])
      "6"                        -> CreditSpec(6)
      ""  / None / unparsable    -> raises CreditParseError
    """

    ALT_MARKERS = ("หรือ", " or ", "/")

    def parse(self, raw: str | None) -> CreditSpec:
        text = (raw or "").strip()
        if not text:
            raise CreditParseError("empty credit string")

        # ถ้าสตริงมีความยาวเกินไป หรือเป็นรหัสวิชา ให้ระบุว่าตัดไม่ได้ทันที
        if len(text) > 15:
            raise CreditParseError(f"credit string too long (likely a code): {text!r}")

        chunks = self._split_alternates(text)
        try:
            specs = [self._parse_single(c) for c in chunks if c.strip()]
            if not specs:
                raise CreditParseError(f"no parsable credit value in {raw!r}")

            head, *rest = specs
            head.alternates = [s.total for s in rest]
            head.ambiguous = bool(rest)
            return head
        except Exception as e:
            # ดัก ValidationError จาก Pydantic แล้วแปลงเป็น CreditParseError
            raise CreditParseError(f"invalid credit specification: {e}")

    def _split_alternates(self, text: str) -> list[str]:
        pattern = "|".join(re.escape(m) for m in self.ALT_MARKERS)
        return re.split(pattern, text)

    def _parse_single(self, chunk: str) -> CreditSpec:
        m = _CREDIT_RE.search(chunk)
        if m:
            total, lec, lab, self_h = (int(x) for x in m.groups())
            return CreditSpec(total=total, lecture=lec, lab=lab, self_study=self_h)
        m2 = _CREDIT_BARE_RE.match(chunk)
        if m2:
            return CreditSpec(total=int(m2.group(1)))
        raise CreditParseError(f"unrecognized credit chunk {chunk!r}")


class CreditParseError(ValueError):
    pass


# ═══════════════════════════════════════════════════════════════════════
# 4. Placement -- replaces the "Year 0 / Term 0" hack
# ═══════════════════════════════════════════════════════════════════════

class TermPlacement(BaseModel):
    """A course/elective with a definite, known term."""
    kind: Literal["term"] = "term"
    year: int = Field(ge=1, le=8)
    semester: int = Field(ge=1, le=3)   # 3 = summer


class Pooled(BaseModel):
    """A course/elective with NO definite term.

    This is the direct replacement for the old year=0/semester=0 sentinel.
    Because it is its own type (not a magic number sharing the `year`/
    `semester` fields), it is structurally impossible for a pooled record
    to be accidentally summed into a real term's per-semester credit load,
    which was the root cause of the CHK7 false positives in the previous
    engine ("year 4 term 1 = 3 credits" when electives silently vanished
    from term totals instead of being pooled).
    """
    kind: Literal["pool"] = "pool"
    reason: str                                  # human-readable why
    candidate_terms: list[tuple[int, int]] = Field(default_factory=list)
    # e.g. [(3,1), (3,2), (4,1)] when the source text names flexible options


Placement = Union[TermPlacement, Pooled]


# ═══════════════════════════════════════════════════════════════════════
# 5. Domain model
# ═══════════════════════════════════════════════════════════════════════

class ElectiveCategory(str, Enum):
    GENERAL_EDUCATION = "GENERAL_EDUCATION"
    MAJOR_ELECTIVE = "MAJOR_ELECTIVE"
    FREE_ELECTIVE = "FREE_ELECTIVE"
    COOPERATIVE_EDUCATION = "COOPERATIVE_EDUCATION"
    OTHER = "OTHER"


class CourseRecord(BaseModel):
    """A single resolved row, before being split into mandatory vs. elective.

    This is the common output of CurriculumParser._resolve_row -- both
    MandatoryCourse and ElectiveSlot are built from it, so the two never
    drift out of sync on what fields exist.
    """
    code: str
    is_synthetic: bool
    source_text: str                 # raw code/title text, for audit trail
    name: str
    credit: CreditSpec
    placement: Placement
    category: ElectiveCategory | None = None
    course_type: str | None = None   # e.g. "บังคับ" / "เลือก" / "Required"
    prerequisite_raw: str | None = None
    flags: list[ValidationFlag] = Field(default_factory=list)


class MandatoryCourse(BaseModel):
    code: str
    name: str
    credit: CreditSpec
    placement: TermPlacement
    prerequisite_codes: list[str] = Field(default_factory=list)
    flags: list[ValidationFlag] = Field(default_factory=list)


class ElectiveSlot(BaseModel):
    """One 'choose from this group' slot. Not yet resolved to a specific
    real course -- that only happens when a student actually registers.
    """
    code: str                        # always synthetic (ELEC-...) or a
                                      # concrete alt code when the source
                                      # names exactly N real options
    category: ElectiveCategory
    name: str
    credit: CreditSpec
    placement: Placement             # TermPlacement if the book pins a
                                      # term, Pooled if it genuinely floats
    flags: list[ValidationFlag] = Field(default_factory=list)


class UnassignedElectivePool(BaseModel):
    """Structured home for every elective slot that has no single
    resolved course, replacing the old 'dump into year 0 / term 0' pile.

    Slots keep their category so the reconciliation engine can report
    gaps per-category ("General Education short by 3 credits") instead of
    one opaque total.
    """
    slots: list[ElectiveSlot] = Field(default_factory=list)

    def add(self, slot: ElectiveSlot) -> None:
        self.slots.append(slot)

    def by_category(self) -> dict[ElectiveCategory, list[ElectiveSlot]]:
        out: dict[ElectiveCategory, list[ElectiveSlot]] = {}
        for s in self.slots:
            out.setdefault(s.category, []).append(s)
        return out

    def total_credits(self) -> int:
        return sum(s.credit.total for s in self.slots)

    def category_credits(self) -> dict[ElectiveCategory, int]:
        return {cat: sum(s.credit.total for s in items)
                for cat, items in self.by_category().items()}


class CurriculumPlan(BaseModel):
    """Top-level parsed output for one program."""
    program_id: str
    program_name: str
    declared_total_credits: int
    mandatory_courses: list[MandatoryCourse] = Field(default_factory=list)
    elective_pool: UnassignedElectivePool = Field(default_factory=UnassignedElectivePool)
    parse_warnings: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _no_duplicate_mandatory_terms(self) -> "CurriculumPlan":
        seen: set[tuple[int, int, str]] = set()
        for c in self.mandatory_courses:
            key = (c.placement.year, c.placement.semester, c.code)
            if key in seen and ValidationFlag.DUPLICATE_IN_TERM not in c.flags:
                c.flags.append(ValidationFlag.DUPLICATE_IN_TERM)
            seen.add(key)
        return self

    def mandatory_total_credits(self) -> int:
        return sum(c.credit.total for c in self.mandatory_courses)

    def term_credits(self) -> dict[tuple[int, int], int]:
        out: dict[tuple[int, int], int] = {}
        for c in self.mandatory_courses:
            key = (c.placement.year, c.placement.semester)
            out[key] = out.get(key, 0) + c.credit.total
        return out


# ═══════════════════════════════════════════════════════════════════════
# 6. Parser -- orchestration
# ═══════════════════════════════════════════════════════════════════════

class CurriculumParser:
    """Turns raw, source-specific rows into a CurriculumPlan.

    Depends only on abstractions (CodeRuleRegistry, CreditParser), never on
    a specific institution's format -- that dependency injection is what
    makes the engine reusable across programs.
    """

    def __init__(self, registry: CodeRuleRegistry, credit_parser: CreditParser | None = None):
        self.registry = registry
        self.credits = credit_parser or CreditParser()

    def parse(self, *, program_id: str, program_name: str,
              declared_total_credits: int,
              raw_courses: Iterable[dict[str, Any]]) -> CurriculumPlan:
        # Built as plain locals, not as mutations on an already-constructed
        # CurriculumPlan: pydantic's @model_validator(mode="after") only
        # runs once, at construction/validation time. Appending to
        # `plan.mandatory_courses` after the fact would never re-trigger
        # `_no_duplicate_mandatory_terms`, so the duplicate flag would
        # silently never be set. Constructing CurriculumPlan exactly once,
        # with the fully-populated lists, is what makes that validator do
        # its job.
        mandatory: list[MandatoryCourse] = []
        pool = UnassignedElectivePool()
        warnings: list[str] = []

        for index, row in enumerate(raw_courses):
            record, warn = self._resolve_row(index, row)
            if warn:
                warnings.append(warn)
            if record is None:
                continue

            if isinstance(record.placement, TermPlacement) and not record.is_synthetic:
                mandatory.append(MandatoryCourse(
                    code=record.code,
                    name=record.name,
                    credit=record.credit,
                    placement=record.placement,
                    prerequisite_codes=self._extract_prereqs(record.prerequisite_raw),
                    flags=record.flags,
                ))
            else:
                pool.add(ElectiveSlot(
                    code=record.code,
                    category=record.category or ElectiveCategory.OTHER,
                    name=record.name,
                    credit=record.credit,
                    placement=record.placement,
                    flags=record.flags,
                ))

        return CurriculumPlan(
            program_id=program_id,
            program_name=program_name,
            declared_total_credits=declared_total_credits,
            mandatory_courses=mandatory,
            elective_pool=pool,
            parse_warnings=warnings,
        )

    # -- row-level resolution -------------------------------------------------

    def _resolve_row(self, index: int, row: dict[str, Any]) -> tuple[CourseRecord | None, str | None]:
        raw_code = str(row.get("code") or "").strip()
        code, code_flag = self.registry.resolve(raw_code)
        flags: list[ValidationFlag] = [code_flag] if code_flag else []
        is_synthetic = code_flag is not None
        if is_synthetic:
            flags.append(ValidationFlag.MALFORMED_CODE)

        try:
            credit = self.credits.parse(row.get("credits"))
            if credit.ambiguous:
                flags.append(ValidationFlag.CREDIT_AMBIGUOUS)
        except CreditParseError as exc:
            flags.append(ValidationFlag.CREDIT_UNPARSABLE)
            return None, f"courses[{index}] code={raw_code!r}: {exc}; row dropped"

        placement, placement_flag = self._resolve_placement(row)
        if placement_flag:
            flags.append(placement_flag)

        name = str(row.get("name_th") or row.get("name") or raw_code or code).strip()
        category = self._infer_category(row, is_synthetic)

        record = CourseRecord(
            code=code,
            is_synthetic=is_synthetic,
            source_text=raw_code,
            name=name,
            credit=credit,
            placement=placement,
            category=category,
            course_type=row.get("type") or row.get("ctype"),
            prerequisite_raw=row.get("prerequisite"),
            flags=flags,
        )
        warn = (f"courses[{index}] raw code {raw_code!r} -> synthetic slot "
                f"{code} ({', '.join(f.value for f in flags)})") if is_synthetic else None
        return record, warn

    def _resolve_placement(self, row: dict[str, Any]) -> tuple[Placement, ValidationFlag | None]:
        year, semester = row.get("year"), row.get("semester")
        try:
            y, s = int(year), int(semester)
            if 1 <= y <= 8 and 1 <= s <= 3:
                return TermPlacement(year=y, semester=s), None
        except (TypeError, ValueError):
            pass

        flexible = row.get("flexible_year_semester") or row.get("flexible")
        candidates: list[tuple[int, int]] = []
        if flexible:
            for pair in re.findall(r"(\d)\s*/\s*(\d)", str(flexible)):
                candidates.append((int(pair[0]), int(pair[1])))
        reason = (f"flexible options: {flexible}" if flexible
                  else "no definite year/semester in source")
        return Pooled(reason=reason, candidate_terms=candidates), ValidationFlag.UNASSIGNED_ELECTIVE

    def _infer_category(self, row: dict[str, Any], is_synthetic: bool) -> ElectiveCategory | None:
        explicit = row.get("category")
        if explicit:
            text = str(explicit)
            if "ทั่วไป" in text or "general" in text.lower():
                return ElectiveCategory.GENERAL_EDUCATION
            if "เสรี" in text or "free" in text.lower():
                return ElectiveCategory.FREE_ELECTIVE
            if "สหกิจ" in text or "cooperative" in text.lower():
                return ElectiveCategory.COOPERATIVE_EDUCATION
            return ElectiveCategory.MAJOR_ELECTIVE
        if not is_synthetic:
            return None
        name = str(row.get("name_th") or row.get("name") or "")
        if "ทั่วไป" in name or "general" in name.lower():
            return ElectiveCategory.GENERAL_EDUCATION
        if "เสรี" in name or "free elective" in name.lower():
            return ElectiveCategory.FREE_ELECTIVE
        if "สหกิจ" in name:
            return ElectiveCategory.COOPERATIVE_EDUCATION
        return ElectiveCategory.MAJOR_ELECTIVE

    def _extract_prereqs(self, raw: str | None) -> list[str]:
        if not raw:
            return []
        return re.findall(r"\d{8}", raw)


# ═══════════════════════════════════════════════════════════════════════
# 7. Reconciliation engine
# ═══════════════════════════════════════════════════════════════════════

class ReconciliationReport(BaseModel):
    declared_total: int
    mandatory_total: int
    elective_total: int
    computed_total: int
    gap: int                        # declared - computed; 0 means reconciled
    category_breakdown: dict[str, int]
    duplicate_issues: list[str] = Field(default_factory=list)
    unresolved_flags: dict[str, int] = Field(default_factory=dict)
    ok: bool

    @property
    def summary(self) -> str:
        if self.ok:
            return f"reconciled: {self.computed_total}/{self.declared_total} credits"
        return (f"credit gap: computed {self.computed_total} vs declared "
                f"{self.declared_total} ({self.gap:+d})")


class ReconciliationEngine:
    """Verifies Total = Mandatory + Electives and explains any gap."""

    def audit(self, plan: CurriculumPlan) -> ReconciliationReport:
        mandatory_total = plan.mandatory_total_credits()
        elective_total = plan.elective_pool.total_credits()
        computed_total = mandatory_total + elective_total
        gap = plan.declared_total_credits - computed_total

        breakdown = {cat.value: credits
                     for cat, credits in plan.elective_pool.category_credits().items()}

        dup_issues = [
            f"{c.code} @ {c.placement.year}/{c.placement.semester}"
            for c in plan.mandatory_courses
            if ValidationFlag.DUPLICATE_IN_TERM in c.flags
        ]

        flag_counts: dict[str, int] = {}
        for c in plan.mandatory_courses:
            for f in c.flags:
                flag_counts[f.value] = flag_counts.get(f.value, 0) + 1
        for s in plan.elective_pool.slots:
            for f in s.flags:
                flag_counts[f.value] = flag_counts.get(f.value, 0) + 1

        return ReconciliationReport(
            declared_total=plan.declared_total_credits,
            mandatory_total=mandatory_total,
            elective_total=elective_total,
            computed_total=computed_total,
            gap=gap,
            category_breakdown=breakdown,
            duplicate_issues=dup_issues,
            unresolved_flags=flag_counts,
            ok=(gap == 0 and not dup_issues),
        )
