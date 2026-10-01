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
      { value: "latest", label: "ฉบับปัจจุบัน" },
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

// One editable example is provided for each difficulty level.
const EXAMPLE_QUESTIONS = [
  { level: "L1", text: "วิชาการเขียนโปรแกรมมีกี่หน่วยกิต" },
  { level: "L2", text: "ปี 2 ภาคการศึกษาที่ 1 มีวิชาบังคับอะไรบ้าง" },
  { level: "L3", text: "วิชา X มีวิชาบังคับก่อนอะไร และถ้ายังไม่ผ่านสามารถลงทะเบียนได้หรือไม่" },
  { level: "L4", text: "วิชาใดมีในหลักสูตรเดิม แต่ไม่มีในหลักสูตรฉบับปรับปรุง" },
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
  elements.curriculum.disabled = isLoading;
  elements.version.disabled = isLoading;
  elements.question.disabled = isLoading;
  elements.askButton.disabled = isLoading;
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
    const pageLabel = source.book_page && source.book_page !== source.page
      ? `PDF หน้า ${source.page} (หน้า ${source.book_page} ในเล่ม)`
      : `PDF หน้า ${source.page}`;
    title.textContent = `${pageLabel} · ${source.section}`;
    item.append(title);
    if (source.quote) {
      const quote = document.createElement("p");
      quote.className = "source-quote";
      quote.textContent = `“${source.quote}”`;
      item.append(quote);
    }
    elements.sourceList.append(item);
  });
}

// Render a successful response and its timing metadata.
function renderSuccess(data, roundTripMs) {
  const sources = Array.isArray(data.sources) ? data.sources : [];
  const hasLowConfidence = typeof data.confidence === "number" && data.confidence < 0.5;
  elements.answerText.textContent = data.answer || "เซิร์ฟเวอร์ไม่ได้ส่งข้อความคำตอบกลับมา";
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
  showState("error");
}

// Submit one validated question and move through Loading to Success or Error.
async function handleSubmit(event) {
  event.preventDefault();
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
    renderSuccess(data, performance.now() - startedAt);
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
  if (event.key === "Enter" && !event.shiftKey) {
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
}

initializeApp();
