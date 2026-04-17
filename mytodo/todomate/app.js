// Created: 2026-04-17 16:35:53
const STORAGE_KEY = "todomate.todos";
const CATEGORY_LABEL = { work: "업무", personal: "개인", study: "공부" };
const EMPTY_MESSAGE = {
  all: "아직 할 일이 없어요. 위에서 추가해보세요 ✨",
  work: "업무 할 일이 없어요 ✨",
  personal: "개인 할 일이 없어요 ✨",
  study: "공부 할 일이 없어요 ✨",
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
  document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
  document.querySelector('.tab[data-filter="all"]').classList.add("active");
  render();
}

// ── 렌더링 ──

// XSS 방지: innerHTML에 삽입되는 모든 사용자 입력에 적용
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
      <li data-id="${t.id}" class="todo-item editing${t.completed ? " completed" : ""}">
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
    <li data-id="${t.id}" class="todo-item${t.completed ? " completed" : ""}">
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

  document.querySelector(".progress-text").textContent =
    `${completed} / ${total} 완료 · ${percent}%${isComplete ? " 🎉" : ""}`;

  const fill = document.querySelector(".progress-bar-fill");
  fill.style.width = `${percent}%`;
  fill.classList.toggle("complete", isComplete);

  // 접근성: progressbar aria 값 갱신
  const track = document.querySelector(".progress-bar-track");
  track.setAttribute("aria-valuenow", percent);
}

function renderFilterCounts() {
  ["all", "work", "personal", "study"].forEach((f) => {
    const tab = document.querySelector(`.tab[data-filter="${f}"]`);
    if (tab) tab.querySelector(".tab-count").textContent = getTodos(f).length;
  });
}

function renderFooter() {
  const hasCompleted = state.todos.some((t) => t.completed);
  document.getElementById("clear-completed-btn").hidden = !hasCompleted;
}

function render() {
  renderProgress();
  renderFilterCounts();
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

  // DOM에서 이미 사라진 경우 (삭제 직후 등) 조용히 종료
  if (!editInput) {
    state.editingId = null;
    return;
  }

  const newText = editInput.value.trim().slice(0, 100);
  if (!newText) {
    // 빈 내용 → 원래 값 유지하고 편집 취소
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

  function handleAdd() {
    commitEdit();
    const result = addTodo(input.value, select.value);
    if (result) {
      input.value = "";
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

  // 클릭 위임: 체크박스 / 수정 버튼 / 삭제 버튼
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

  // 더블클릭: 텍스트 영역 → 편집 시작
  list.addEventListener("dblclick", (e) => {
    if (!e.target.classList.contains("todo-text")) return;
    const li = e.target.closest(".todo-item");
    if (li) startEdit(li.dataset.id);
  });

  // 편집 입력창 키보드 (Enter 저장 / ESC 취소)
  list.addEventListener("keydown", (e) => {
    if (!e.target.classList.contains("edit-input")) return;
    if (e.key === "Enter") {
      e.preventDefault();
      commitEdit();
    } else if (e.key === "Escape") {
      cancelEdit();
    }
  });

  // 편집 입력창 포커스 이탈 → 저장
  // focusout은 버블링되므로 list에 위임 가능
  list.addEventListener("focusout", (e) => {
    if (!e.target.classList.contains("edit-input")) return;
    // edit-select로 포커스가 이동하는 경우 → 아직 편집 중, 저장 보류
    const goingToSelect =
      e.relatedTarget && e.relatedTarget.classList.contains("edit-select");
    if (!goingToSelect) commitEdit();
  });

  // 필터 탭
  document.querySelector(".filter-tabs").addEventListener("click", (e) => {
    const tab = e.target.closest(".tab");
    if (!tab) return;
    commitEdit();
    state.currentFilter = tab.dataset.filter;
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    render();
  });

  // 푸터 버튼
  document.getElementById("clear-completed-btn").addEventListener("click", clearCompleted);
  document.getElementById("reset-btn").addEventListener("click", resetApp);
}

// ── 초기화 ──

state.todos = loadTodos();

document.addEventListener("DOMContentLoaded", () => {
  bindEvents();
  render();
  console.log("TodoMate loaded");
});
