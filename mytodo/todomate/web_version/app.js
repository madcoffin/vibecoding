// Created: 2026-04-21 16:52:50
const STORAGE_KEY = "todomate.todos";
const CATEGORY_LABEL = { work: "업무", personal: "개인", study: "공부" };
const FILTER_TITLE = { all: "전체 할 일", work: "업무 할 일", personal: "개인 할 일", study: "공부 할 일" };
const EMPTY_MESSAGE = {
  all: "아직 할 일이 없어요. 위에서 추가해보세요 ✨",
  work: "업무 할 일이 없어요 ✨",
  personal: "개인 할 일이 없어요 ✨",
  study: "공부 할 일이 없어요 ✨",
};

const RING_CIRCUMFERENCE = 201; // 2 * π * 32

const CATEGORY_KEYWORDS = {
  work: [
    "회의", "미팅", "보고서", "보고", "발표", "프로젝트", "업무", "출근", "퇴근",
    "클라이언트", "고객", "기획", "문서", "메일", "이메일", "계획서", "제안서",
    "견적", "계약", "팀장", "부장", "대리", "과장", "면접", "채용", "출장",
    "영업", "마케팅", "홍보", "배포", "릴리즈", "코드리뷰", "피드백", "기안",
    "결재", "슬랙", "slack", "zoom", "줌", "스프린트", "sprint", "deadline",
    "데드라인", "mtg", "ppt", "보안", "개발",
  ],
  study: [
    "공부", "학습", "강의", "수업", "과제", "숙제", "시험", "복습", "예습",
    "독서", "책 읽", "읽기", "노트", "강좌", "교재", "교과서", "도서관",
    "암기", "단어", "영어", "수학", "과학", "역사", "논문", "레포트", "report",
    "lecture", "study", "퀴즈", "quiz", "자격증", "토익", "토플", "인강",
    "유데미", "udemy", "코딩 공부", "알고리즘", "정리",
  ],
};

let state = {
  todos: [],
  currentFilter: "all",
  editingId: null,
};

// ── 데이터 계층 ──

function loadTodos() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveTodos(todos) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(todos));
  } catch (e) {
    if (e.name === "QuotaExceededError") {
      alert("저장 공간이 부족합니다. 완료된 할 일을 삭제해 공간을 확보해주세요.");
    }
  }
}

function addTodo(text, category) {
  const trimmed = text.trim().slice(0, 100);
  if (!trimmed) return false;

  const todo = {
    id:
      typeof crypto !== "undefined" && crypto.randomUUID
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    text: trimmed,
    category,
    completed: false,
    createdAt: Date.now(),
  };

  state.todos = [todo, ...state.todos];
  saveTodos(state.todos);
  return todo;
}

function updateTodo(id, updates) {
  state.todos = state.todos.map((t) => (t.id === id ? { ...t, ...updates } : t));
  saveTodos(state.todos);
}

function deleteTodo(id) {
  state.todos = state.todos.filter((t) => t.id !== id);
  saveTodos(state.todos);
}

function toggleTodo(id) {
  updateTodo(id, {
    completed: !state.todos.find((t) => t.id === id)?.completed,
  });
}

function getTodos(filter) {
  const filtered =
    filter === "all" ? state.todos : state.todos.filter((t) => t.category === filter);
  return [...filtered].sort((a, b) => b.createdAt - a.createdAt);
}

function getProgress(filter) {
  const todos = getTodos(filter);
  const total = todos.length;
  const completed = todos.filter((t) => t.completed).length;
  const percent = total === 0 ? 0 : Math.round((completed / total) * 100);
  return { total, completed, percent };
}

function inferCategory(text) {
  const lower = text.toLowerCase();
  for (const [category, keywords] of Object.entries(CATEGORY_KEYWORDS)) {
    if (keywords.some((kw) => lower.includes(kw))) return category;
  }
  return null;
}

function clearCompleted() {
  if (state.editingId) {
    const editing = state.todos.find((t) => t.id === state.editingId);
    if (editing?.completed) state.editingId = null;
  }
  state.todos = state.todos.filter((t) => !t.completed);
  saveTodos(state.todos);
  render();
}

function resetApp() {
  if (!confirm("모든 할 일을 삭제하고 앱을 초기화할까요?")) return;
  state.todos = [];
  state.editingId = null;
  state.currentFilter = "all";
  localStorage.removeItem(STORAGE_KEY);
  document.querySelectorAll(".nav-item").forEach((t) => t.classList.remove("active"));
  document.querySelector('.nav-item[data-filter="all"]').classList.add("active");
  render();
}

// ── 렌더링 ──

function escapeHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function todoItemHtml(t) {
  const safeText = escapeHtml(t.text);
  const checkLabel = `${safeText} ${t.completed ? "완료 취소" : "완료로 표시"}`;

  if (state.editingId === t.id) {
    return `
      <li data-id="${t.id}" data-category="${t.category}" class="todo-item editing${t.completed ? " completed" : ""}">
        <input type="checkbox" class="todo-check" ${t.completed ? "checked" : ""} aria-label="${checkLabel}">
        <input type="text" class="edit-input" value="${safeText}" maxlength="100" aria-label="할 일 수정">
        <select class="edit-select" aria-label="카테고리 선택">
          <option value="work"${t.category === "work" ? " selected" : ""}>업무</option>
          <option value="personal"${t.category === "personal" ? " selected" : ""}>개인</option>
          <option value="study"${t.category === "study" ? " selected" : ""}>공부</option>
        </select>
        <button class="todo-delete" aria-label="${safeText} 삭제">✕</button>
      </li>`;
  }

  return `
    <li data-id="${t.id}" data-category="${t.category}" class="todo-item${t.completed ? " completed" : ""}">
      <input type="checkbox" class="todo-check" ${t.completed ? "checked" : ""} aria-label="${checkLabel}">
      <span class="todo-text">${safeText}</span>
      <span class="todo-category cat-${t.category}">${CATEGORY_LABEL[t.category]}</span>
      <button class="todo-edit" aria-label="${safeText} 수정">수정</button>
      <button class="todo-delete" aria-label="${safeText} 삭제">✕</button>
    </li>`;
}

function renderTodos() {
  const list = document.getElementById("todo-list");
  const todos = getTodos(state.currentFilter);

  if (todos.length === 0) {
    list.innerHTML = `<li class="todo-empty">${EMPTY_MESSAGE[state.currentFilter]}</li>`;
    return;
  }

  list.innerHTML = todos.map(todoItemHtml).join("");
}

function renderProgress() {
  const { total, completed, percent } = getProgress(state.currentFilter);
  const isComplete = total > 0 && percent === 100;

  document.getElementById("progress-percent").textContent = `${percent}%`;
  document.getElementById("progress-label").textContent =
    `${completed} / ${total} 완료${isComplete ? " 🎉" : ""}`;

  const ringFill = document.getElementById("progress-ring-fill");
  ringFill.style.strokeDashoffset = RING_CIRCUMFERENCE * (1 - percent / 100);
  ringFill.classList.toggle("complete", isComplete);

  const ring = document.querySelector(".progress-ring");
  ring.setAttribute("aria-valuenow", percent);
}

function renderFilterCounts() {
  ["all", "work", "personal", "study"].forEach((f) => {
    const item = document.querySelector(`.nav-item[data-filter="${f}"]`);
    if (item) item.querySelector(".tab-count").textContent = getTodos(f).length;
  });
}

function renderFilterTitle() {
  document.getElementById("current-filter-title").textContent = FILTER_TITLE[state.currentFilter];
}

function renderFooter() {
  const hasCompleted = state.todos.some((t) => t.completed);
  document.getElementById("clear-completed-btn").hidden = !hasCompleted;
}

function render() {
  renderProgress();
  renderFilterCounts();
  renderFilterTitle();
  renderTodos();
  renderFooter();
}

// ── 편집 ──

function startEdit(id) {
  state.editingId = id;
  render();
  const editInput = document.querySelector(".edit-input");
  if (editInput) {
    editInput.focus();
    editInput.select();
  }
}

function commitEdit() {
  if (!state.editingId) return;
  const id = state.editingId;
  const editInput = document.querySelector(".edit-input");
  const editSelect = document.querySelector(".edit-select");

  if (!editInput) {
    state.editingId = null;
    return;
  }

  const newText = editInput.value.trim().slice(0, 100);
  if (!newText) {
    state.editingId = null;
    render();
    return;
  }

  const newCategory =
    editSelect?.value ?? state.todos.find((t) => t.id === id)?.category;
  updateTodo(id, { text: newText, category: newCategory });
  state.editingId = null;
  render();
}

function cancelEdit() {
  if (!state.editingId) return;
  state.editingId = null;
  render();
}

// ── 이벤트 바인딩 ──

function bindEvents() {
  const input = document.getElementById("todo-input");
  const select = document.getElementById("category-select");
  const addBtn = document.getElementById("add-btn");
  const list = document.getElementById("todo-list");
  const hint = document.getElementById("auto-hint");

  function showAutoHint(category) {
    hint.textContent = `✦ 자동 분류: ${CATEGORY_LABEL[category]}`;
    hint.className = `auto-hint visible cat-${category}`;
  }

  function hideAutoHint() {
    hint.className = "auto-hint";
  }

  input.addEventListener("input", () => {
    const inferred = inferCategory(input.value);
    if (inferred) {
      select.value = inferred;
      showAutoHint(inferred);
    } else {
      hideAutoHint();
    }
  });

  function handleAdd() {
    commitEdit();
    const result = addTodo(input.value, select.value);
    if (result) {
      input.value = "";
      hideAutoHint();
      input.focus();
      render();
    } else {
      input.classList.add("shake");
      input.addEventListener("animationend", () => input.classList.remove("shake"), {
        once: true,
      });
    }
  }

  addBtn.addEventListener("click", handleAdd);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") handleAdd();
  });

  list.addEventListener("click", (e) => {
    const li = e.target.closest(".todo-item");
    if (!li) return;
    const id = li.dataset.id;

    if (e.target.classList.contains("todo-check")) {
      commitEdit();
      toggleTodo(id);
      render();
    } else if (e.target.classList.contains("todo-delete")) {
      if (state.editingId === id) state.editingId = null;
      deleteTodo(id);
      render();
    } else if (e.target.classList.contains("todo-edit")) {
      startEdit(id);
    }
  });

  list.addEventListener("dblclick", (e) => {
    if (!e.target.classList.contains("todo-text")) return;
    const li = e.target.closest(".todo-item");
    if (li) startEdit(li.dataset.id);
  });

  list.addEventListener("keydown", (e) => {
    if (!e.target.classList.contains("edit-input")) return;
    if (e.key === "Enter") {
      e.preventDefault();
      commitEdit();
    } else if (e.key === "Escape") {
      cancelEdit();
    }
  });

  list.addEventListener("focusout", (e) => {
    if (!e.target.classList.contains("edit-input")) return;
    const goingToSelect =
      e.relatedTarget && e.relatedTarget.classList.contains("edit-select");
    if (!goingToSelect) commitEdit();
  });

  document.querySelector(".filter-nav").addEventListener("click", (e) => {
    const item = e.target.closest(".nav-item");
    if (!item) return;
    commitEdit();
    state.currentFilter = item.dataset.filter;
    document.querySelectorAll(".nav-item").forEach((t) => t.classList.remove("active"));
    item.classList.add("active");
    render();
  });

  document.getElementById("clear-completed-btn").addEventListener("click", clearCompleted);
  document.getElementById("reset-btn").addEventListener("click", resetApp);
}

// ── 초기화 ──

state.todos = loadTodos();

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  render();
  console.log("TodoMate (web_version) loaded");
});
