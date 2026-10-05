import { citationHref, sourceFilename, pageLabel, shouldSubmitOnEnter } from './presentation.mjs';

// Edit these constants when connecting to another backend or changing mock mode.
// The backend serves /frontend/ on the same origin; standalone previews use 8000.
const API_BASE = window.location.pathname.startsWith("/frontend/")
  ? window.location.origin
  : "http://localhost:8000";
const USE_MOCK = false;
const REQUEST_TIMEOUT_MS = 30_000;
const SLOW_THRESHOLD_MS = 5_000;
const MAX_HISTORY_ITEMS = 5;

// Curriculum and version options live in one editable array.
const CURRICULUM_OPTIONS = [
  {
    value: "AIT",
    label: "AIT — เทคโนโลยีปัญญาประดิษฐ์",
    versions: [
      { value: "latest", label: "ฉบับปัจจุบัน (พ.ศ. 2566)" },
    ],
  },
  {
    value: "DSBA",
    label: "DSBA — วิทยาการข้อมูลและการวิเคราะห์เชิงธุรกิจ",
    versions: [
      { value: "latest", label: "ฉบับล่าสุด (พ.ศ. 2565)" },
      { value: "old", label: "ฉบับเก่า (พ.ศ. 2560)" },
      { value: "all versions", label: "ทุกฉบับ" },
    ],
  },
  {
    value: "IT",
    label: "IT — เทคโนโลยีสารสนเทศ",
    versions: [
      { value: "latest", label: "ฉบับล่าสุด (พ.ศ. 2565)" },
      { value: "old", label: "ฉบับเก่า (พ.ศ. 2560)" },
      { value: "all versions", label: "ทุกฉบับ" },
    ],
  },
  {
    value: "BIT",
    label: "BIT — เทคโนโลยีสารสนเทศทางธุรกิจ",
    versions: [
      { value: "latest", label: "ฉบับล่าสุด (พ.ศ. 2565)" },
      { value: "old", label: "ฉบับเก่า (พ.ศ. 2560)" },
      { value: "all versions", label: "ทุกฉบับ" },
    ],
  },
];

// Examples use the source rubric's levels; unsupported L4 sources are not invented.
const EXAMPLE_QUESTIONS = [
  { level: "L1", text: "วิชาการเขียนโปรแกรมมีกี่หน่วยกิต" },
  { level: "L2", text: "ปี 2 ภาคการศึกษาที่ 1 มีวิชาบังคับอะไรบ้าง" },
  { level: "L2", text: "วิชา X มีวิชาบังคับก่อนอะไร และถ้ายังไม่ผ่านสามารถลงทะเบียนได้หรือไม่" },
  { level: "L3", text: "วิชาใดมีในหลักสูตรเดิม แต่ไม่มีในหลักสูตรฉบับปรับปรุง" },
];

// Query every DOM element once.
const elements = {
  form: document.querySelector("#question-form"),
  modeBadge: document.querySelector("#mode-badge"),
  curriculum: document.querySelector("#curriculum-select"),
  version: document.querySelector("#version-select"),
  question: document.querySelector("#question-input"),
  characterCount: document.querySelector("#character-count"),
  askButton: document.querySelector("#ask-button"),
  questionCard: document.querySelector(".question-card"),
  exampleList: document.querySelector("#example-list"),
  idleState: document.querySelector("#idle-state"),
  loadingState: document.querySelector("#loading-state"),
  successState: document.querySelector("#success-state"),
  errorState: document.querySelector("#error-state"),
  answerText: document.querySelector("#answer-text"),
  confidenceWarning: document.querySelector("#confidence-warning"),
  sourceWarning: document.querySelector("#source-warning"),
  sourceCount: document.querySelector("#source-count"),
  sourceList: document.querySelector("#source-list"),
  modelValue: document.querySelector("#model-value"),
  serverLatencyValue: document.querySelector("#server-latency-value"),
  roundTripValue: document.querySelector("#round-trip-value"),
  slowBadge: document.querySelector("#slow-badge"),
  errorMessage: document.querySelector("#error-message"),
  errorAction: document.querySelector("#error-action"),
  historyList: document.querySelector("#history-list"),
  historyEmpty: document.querySelector("#history-empty"),
  selectionContext: document.querySelector("#selection-context"),
  answerContext: document.querySelector("#answer-context"),
  questionError: document.querySelector("#question-error"),
  retryButton: document.querySelector("#retry-button"),
  resultCard: document.querySelector(".result-card"),
};

// This array is intentionally in memory only.
const questionHistory = [];

// Build both selectors from CURRICULUM_OPTIONS.
function populateCurriculumOptions() {
  CURRICULUM_OPTIONS.forEach((curriculum) => {
    const option = document.createElement("option");
    option.value = curriculum.value;
    option.textContent = curriculum.label;
    elements.curriculum.append(option);
  });
  populateVersionOptions();
}

// Update versions when the selected curriculum changes.
function populateVersionOptions() {
  const selected = CURRICULUM_OPTIONS.find(
    (curriculum) => curriculum.value === elements.curriculum.value,
  );
  elements.version.replaceChildren();
  selected.versions.forEach((version) => {
    const option = document.createElement("option");
    option.value = version.value;
    option.textContent = version.label;
    elements.version.append(option);
  });
  elements.selectionContext.textContent = selected.label;
}

// Return the Thai label while keeping the API value unchanged.
function getVersionLabel(curriculumValue, versionValue) {
  const curriculum = CURRICULUM_OPTIONS.find((item) => item.value === curriculumValue);
  const version = curriculum.versions.find((item) => item.value === versionValue);
  return version ? version.label : versionValue;
}

// Build safe clickable example chips with DOM nodes.
function populateExamples() {
  EXAMPLE_QUESTIONS.forEach((example) => {
    const button = document.createElement("button");
    const level = document.createElement("span");
    const text = document.createElement("span");
    button.type = "button";
    button.className = "example-chip";
    level.className = "chip-level";
    level.textContent = example.level;
    text.textContent = example.text;
    button.append(level, text);
    button.addEventListener("click", () => {
      elements.question.value = example.text;
      updateCharacterCount();
      elements.question.focus();
    });
    elements.exampleList.append(button);
  });
}

// Display exactly one of the four application states.
function showState(stateName) {
  elements.resultCard.dataset.state = stateName;
  const stateMap = {
    idle: elements.idleState,
    loading: elements.loadingState,
    success: elements.successState,
    error: elements.errorState,
  };
  Object.entries(stateMap).forEach(([name, element]) => {
    element.classList.toggle("hidden", name !== stateName);
  });
}

// Lock controls while a request is running.
function setLoading(isLoading) {
  elements.resultCard.setAttribute('aria-busy', String(isLoading));
  elements.curriculum.disabled = isLoading;
  elements.version.disabled = isLoading;
  elements.question.disabled = isLoading;
  elements.askButton.disabled = isLoading;
  elements.retryButton.disabled = isLoading;
  elements.exampleList.querySelectorAll('button').forEach((button) => { button.disabled = isLoading; });
  elements.questionCard.classList.toggle("loading", isLoading);
}

// Keep the visible character count synchronized with the input.
function updateCharacterCount() {
  elements.characterCount.textContent = `${elements.question.value.length} / 500`;
}

// Validate before sending anything to the backend.
function validateQuestion(question) {
  if (!question) {
    return "กรุณาพิมพ์คำถามก่อนกดปุ่มถาม";
  }
  if (question.length > 500) {
    return "คำถามยาวเกิน 500 ตัวอักษร กรุณาย่อคำถามให้สั้นลง";
  }
  return "";
}

// Add one question and keep only the latest five.
function addHistory(question, curriculum, version) {
  questionHistory.unshift({ question, curriculum, version });
  questionHistory.splice(MAX_HISTORY_ITEMS);
  renderHistory();
}

// Render history as text-only DOM nodes.
function renderHistory() {
  elements.historyList.replaceChildren();
  elements.historyEmpty.classList.toggle("hidden", questionHistory.length > 0);
  questionHistory.forEach((item) => {
    const row = document.createElement("li");
    const question = document.createElement("div");
    const context = document.createElement("div");
    row.className = "history-item";
    question.textContent = item.question;
    context.className = "history-context";
    context.textContent = `${item.curriculum} · ${item.version}`;
    row.append(question, context);
    elements.historyList.append(row);
  });
}

// Pause mock responses so the loading state is visible.
function wait(milliseconds) {
  return new Promise((resolve) => window.setTimeout(resolve, milliseconds));
}

// Return contract-shaped mock data and support required test triggers.
async function requestMock(payload) {
  const trigger = payload.question.trim().toLowerCase();
  await wait(trigger === "slow" ? 5_300 : 1_300);
  if (trigger === "error") {
    throw new Error("ระบบจำลองส่งข้อผิดพลาดสำหรับคำถามทดสอบนี้");
  }

  const response = {
    answer: `นี่คือคำตอบจำลองสำหรับทดสอบหน้าจอหลักสูตร ${payload.curriculum} (${getVersionLabel(payload.curriculum, payload.version)}) ไม่ใช่คำตอบจากฐานข้อมูลจริง`,
    sources: [
      { page: 12, section: "แหล่งอ้างอิงตัวอย่าง", quote: "ข้อมูลจำลองสำหรับทดสอบการแสดงผลเท่านั้น" },
      { page: 18, section: "แหล่งอ้างอิงตัวอย่าง" },
    ],
    model: "qwen3:4b (จำลอง)",
    latency_ms: trigger === "slow" ? 5_120 : 840,
    confidence: 0.91,
  };

  if (trigger === "nosource") {
    response.sources = [];
  }
  if (trigger === "xss") {
    response.answer = "<script>alert(1)</script>";
  }
  if (trigger === "lowconf") {
    response.confidence = 0.3;
  }
  return response;
}

// Fetch the real API with a hard 30-second timeout.
async function requestApi(payload) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const response = await fetch(`${API_BASE}/ask`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(data.error || `เซิร์ฟเวอร์ตอบกลับด้วย HTTP ${response.status}`);
    }
    return data;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

// Render citations with textContent so model text cannot execute as HTML.
function renderSources(sources) {
  elements.sourceList.replaceChildren();
  elements.sourceCount.textContent = `${sources.length} แหล่ง`;
  elements.sourceWarning.classList.toggle("hidden", sources.length > 0);
  sources.forEach((source) => {
    const item = document.createElement("li");
    const title = document.createElement("p");
    item.className = "source-item";
    title.className = "source-title";
    title.textContent = `${pageLabel(source.page, source.book_page)} · ${source.section || 'ยังไม่ยืนยันหัวข้อ'}`;
    item.append(title);
    if (source.quote) {
      const quote = document.createElement("p");
      quote.className = "source-quote";
      quote.textContent = `“${source.quote}”`;
      item.append(quote);
    }
    const href = citationHref(API_BASE, sourceFilename(source.section), source.page);
    if (href) {
      const link = document.createElement('a');
      link.className = 'source-link';
      link.textContent = 'เปิดหน้าที่อ้างอิงใน PDF (แท็บใหม่)';
      link.href = href;
      link.target = '_blank';
      link.rel = 'noopener noreferrer';
      item.append(link);
    }
    elements.sourceList.append(item);
  });
}

// Render a successful response and its timing metadata.
function renderStudyPlan(payload) {
  const container = document.querySelector('#study-plan-cards');
  container.replaceChildren();
  const cards = Array.isArray(payload?.cards) ? payload.cards : [];
  container.classList.toggle('hidden', !cards.length);
  elements.answerText.classList.toggle('hidden', Boolean(cards.length));
  const add = (parent, tag, text, className) => {
    const node = document.createElement(tag);
    if (text != null) node.textContent = String(text);
    if (className) node.className = className;
    parent.append(node);
    return node;
  };
  cards.forEach((card) => {
    const article = add(container, 'article', null, 'study-plan-card');
    add(article, 'h3', `${card.program} พ.ศ. ${card.version} — ปี ${card.year} ภาคการศึกษาที่ ${card.semester}`);
    add(article, 'h4', card.plan_label, 'plan-label');
    if (card.printed_total != null) add(article, 'p', `รวมตามตาราง ${card.printed_total} หน่วยกิต โดยเลือกกลุ่มและตัวเลือกตามข้อกำหนด ไม่รวมทุกทางเลือกเข้าด้วยกัน`, 'plan-note');
    (card.notes || []).forEach((note) => add(article, 'p', note, 'plan-note'));
    (card.sections || []).forEach((section) => {
      const block = add(article, 'section', null, 'track-card');
      add(block, 'h5', section.title);
      const groupIds = section.rows.map((r) => r.alt_group).filter(Boolean);
      const alternatives = [...new Set(groupIds.filter((id) => groupIds.filter((other) => other === id).length > 1))];
      if (alternatives.length) add(block, 'p', 'รายวิชาที่เป็นชุดตัวเลือก “หรือ” ไม่ต้องเรียนทุกตัวเลือกในชุดเดียวกัน', 'plan-note');
      const table = add(block, 'table', null, 'plan-table');
      table.setAttribute('role', 'table');
      add(table, 'caption', `${card.program} พ.ศ. ${card.version} — ${card.plan_label} — ${section.title}`, 'sr-only');
      const head = add(add(table, 'thead'), 'tr');
      ['รหัสวิชา', 'ชื่อวิชา', 'หน่วยกิต'].forEach((text) => add(head, 'th', text).scope = 'col');
      const body = add(table, 'tbody');
      body.setAttribute('role', 'rowgroup');
      (section.rows || []).forEach((row) => {
        const tr = add(body, 'tr');
        tr.setAttribute('role', 'row');
        const placeholder = row.is_placeholder || /^ELEC-/i.test(row.code || '');
        const code = add(tr, 'td', row.raw_code || row.code_pattern || (placeholder ? 'ไม่กำหนดรหัส' : row.code), 'plan-code');
        code.setAttribute('role', 'cell');
        const name = add(tr, 'td', null, 'plan-name');
        name.setAttribute('role', 'cell');
        add(name, 'span', row.name_th || row.name_en || 'เลือกจากรายวิชาในหมวดนี้ (ยังไม่ยืนยันชื่อหมวดจากข้อมูลที่นำเข้า)');
        if (alternatives.includes(row.alt_group)) add(name, 'small', `ตัวเลือก “หรือ” ชุดที่ ${alternatives.indexOf(row.alt_group) + 1}`, 'plan-secondary');
        if (row.name_en || row.credits_raw || row.category || row.note) {
          const details = add(name, 'details');
          add(details, 'summary', 'รายละเอียดเพิ่มเติม');
          if (row.name_en) add(details, 'p', row.name_en);
          if (row.credits_raw) add(details, 'p', `หน่วยกิต (บรรยาย-ปฏิบัติ-ศึกษาด้วยตนเอง): ${row.credits_raw}`);
          if (row.category) add(details, 'p', `หมวดวิชา: ${row.category}`);
          if (row.note) add(details, 'p', row.note);
        }
        const credits = add(tr, 'td', row.credits ?? 'ยังไม่ยืนยัน', 'plan-credits');
        credits.setAttribute('role', 'cell');
        credits.dataset.label = 'หน่วยกิต';
        if (placeholder) add(credits, 'small', 'วิชาเลือก', 'plan-secondary');
        if (row.page_number) {
          const text = pageLabel(row.page_number, row.printed_page_number);
          const href = citationHref(API_BASE, row.source_file, row.page_number);
          if (href) {
            const link = add(name, 'a', text, 'plan-source');
            link.href = href;
            link.setAttribute('aria-label', `${text} · ${row.source_file} (เปิดแท็บใหม่)`);
            link.target = '_blank'; link.rel = 'noopener noreferrer';
          } else add(name, 'small', text, 'plan-secondary');
        }
      });
    });
  });
}

function renderSuccess(data, roundTripMs, payload) {
  elements.answerContext.textContent = `${payload.curriculum} · ${getVersionLabel(payload.curriculum, payload.version)} · ${payload.question}`;
  const sources = Array.isArray(data.sources) ? data.sources : [];
  const hasLowConfidence = typeof data.confidence === "number" && data.confidence < 0.5;
  elements.answerText.textContent = data.answer || "เซิร์ฟเวอร์ไม่ได้ส่งข้อความคำตอบกลับมา";
  renderStudyPlan(data.study_plan);
  elements.confidenceWarning.classList.toggle("hidden", !hasLowConfidence);
  elements.modelValue.textContent = data.model || "ไม่มีข้อมูล";
  elements.serverLatencyValue.textContent = Number.isFinite(data.latency_ms)
    ? `${Math.round(data.latency_ms)} ms`
    : "ไม่มีข้อมูล";
  elements.roundTripValue.textContent = `${Math.round(roundTripMs)} ms`;
  elements.slowBadge.classList.toggle("hidden", roundTripMs <= SLOW_THRESHOLD_MS);
  renderSources(sources);
  showState("success");
}

// Give the user a useful next action for each error category.
function renderError(error, category = "request") {
  const messages = {
    validation: "ตรวจสอบคำถามแล้วลองอีกครั้ง",
    timeout: "คำขอใช้เวลานานกว่า 30 วินาที ลองใช้คำถามที่สั้นลงหรือตรวจสอบโมเดลของ backend",
    network: `ตรวจสอบว่า backend ทำงานอยู่และค่า API_BASE ถูกต้อง: ${API_BASE}`,
    request: "ลองอีกครั้ง หากยังพบปัญหาให้ตรวจสอบรายละเอียดใน Terminal ของ backend",
  };
  elements.errorMessage.textContent = error.message;
  elements.errorAction.textContent = messages[category];
  elements.retryButton.classList.toggle('hidden', category === 'validation');
  if (category === 'validation') {
    elements.questionError.textContent = error.message;
    elements.questionError.classList.remove('hidden');
    elements.question.setAttribute('aria-invalid', 'true');
    elements.question.focus();
  }
  showState("error");
}

// Submit one validated question and move through Loading to Success or Error.
async function handleSubmit(event) {
  event.preventDefault();
  if (elements.askButton.disabled) return;
  const question = elements.question.value.trim();
  const validationError = validateQuestion(question);
  if (validationError) {
    renderError(new Error(validationError), "validation");
    return;
  }

  const payload = {
    question,
    curriculum: elements.curriculum.value,
    version: elements.version.value,
  };
  elements.questionError.classList.add('hidden');
  elements.question.removeAttribute('aria-invalid');
  addHistory(
    question,
    payload.curriculum,
    getVersionLabel(payload.curriculum, payload.version),
  );
  setLoading(true);
  showState("loading");
  const startedAt = performance.now();

  try {
    const data = USE_MOCK ? await requestMock(payload) : await requestApi(payload);
    renderSuccess(data, performance.now() - startedAt, payload);
  } catch (error) {
    if (error.name === "AbortError") {
      renderError(new Error("หมดเวลารอคำตอบจากเซิร์ฟเวอร์"), "timeout");
    } else if (error instanceof TypeError) {
      renderError(new Error("เบราว์เซอร์ไม่สามารถเชื่อมต่อกับ backend ได้"), "network");
    } else {
      renderError(error, "request");
    }
  } finally {
    setLoading(false);
  }
}

// Enter submits; Shift+Enter still creates a new line.
function handleQuestionKeydown(event) {
  if (shouldSubmitOnEnter(event, elements.askButton.disabled)) {
    event.preventDefault();
    elements.form.requestSubmit();
  }
}

// Initialize the page once.
function initializeApp() {
  elements.modeBadge.textContent = USE_MOCK
    ? "โหมดข้อมูลจำลอง — คำตอบไม่ใช่ข้อมูลจริง"
    : "โหมดเชื่อมต่อฐานข้อมูลจริง";
  elements.modeBadge.classList.toggle("live-mode", !USE_MOCK);
  populateCurriculumOptions();
  populateExamples();
  updateCharacterCount();
  showState("idle");
  elements.curriculum.addEventListener("change", populateVersionOptions);
  elements.question.addEventListener("input", updateCharacterCount);
  elements.question.addEventListener("keydown", handleQuestionKeydown);
  elements.form.addEventListener("submit", handleSubmit);
  elements.retryButton.addEventListener('click', () => elements.form.requestSubmit());
}

initializeApp();
