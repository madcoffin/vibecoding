// Created: 2026-04-17 15:45:41
// Canvas drawing + API calls for Handwritten Digit Recognizer

const canvas     = document.getElementById("canvas");
const ctx        = canvas.getContext("2d");
const predictBtn = document.getElementById("predictBtn");
const clearBtn   = document.getElementById("clearBtn");
const digitEl    = document.getElementById("digit");
const confEl     = document.getElementById("confidence");
const barsEl     = document.getElementById("bars");

const BRUSH_RADIUS = 9;  // px, matches desktop version feel

// ---------------------------------------------------------------------------
// Canvas state
// ---------------------------------------------------------------------------
let drawing = false;
let lastX = 0;
let lastY = 0;

function initCanvas() {
  ctx.fillStyle = "#ffffff";
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.strokeStyle = "#000000";
  ctx.lineWidth   = BRUSH_RADIUS * 2;
  ctx.lineCap     = "round";
  ctx.lineJoin    = "round";
}
initCanvas();

// ---------------------------------------------------------------------------
// Pointer position helpers (works for mouse and touch)
// ---------------------------------------------------------------------------
function getPos(e) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width  / rect.width;
  const scaleY = canvas.height / rect.height;
  const src = e.touches ? e.touches[0] : e;
  return {
    x: (src.clientX - rect.left) * scaleX,
    y: (src.clientY - rect.top)  * scaleY,
  };
}

// ---------------------------------------------------------------------------
// Drawing event handlers
// ---------------------------------------------------------------------------
function startDraw(e) {
  e.preventDefault();
  drawing = true;
  const { x, y } = getPos(e);
  lastX = x;
  lastY = y;
  // Draw a dot on click/tap with no movement
  ctx.beginPath();
  ctx.arc(x, y, BRUSH_RADIUS, 0, Math.PI * 2);
  ctx.fillStyle = "#000000";
  ctx.fill();
}

function draw(e) {
  e.preventDefault();
  if (!drawing) return;
  const { x, y } = getPos(e);
  ctx.beginPath();
  ctx.moveTo(lastX, lastY);
  ctx.lineTo(x, y);
  ctx.stroke();
  lastX = x;
  lastY = y;
}

function stopDraw() { drawing = false; }

canvas.addEventListener("mousedown",  startDraw);
canvas.addEventListener("mousemove",  draw);
canvas.addEventListener("mouseup",    stopDraw);
canvas.addEventListener("mouseleave", stopDraw);
canvas.addEventListener("touchstart", startDraw, { passive: false });
canvas.addEventListener("touchmove",  draw,      { passive: false });
canvas.addEventListener("touchend",   stopDraw);

// ---------------------------------------------------------------------------
// Clear
// ---------------------------------------------------------------------------
clearBtn.addEventListener("click", () => {
  initCanvas();
  digitEl.textContent    = "—";
  digitEl.style.color    = "#a6e3a1";
  confEl.textContent     = "";
  confEl.className       = "confidence";
  barsEl.innerHTML       = "";
});

// ---------------------------------------------------------------------------
// Predict
// ---------------------------------------------------------------------------
predictBtn.addEventListener("click", async () => {
  predictBtn.disabled    = true;
  predictBtn.textContent = "…";

  try {
    const dataURL = canvas.toDataURL("image/png");
    const res = await fetch("/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ image: dataURL }),
    });

    if (!res.ok) throw new Error(`Server error ${res.status}`);
    const data = await res.json();
    renderResult(data);
  } catch (err) {
    digitEl.textContent = "!";
    confEl.textContent  = err.message;
  } finally {
    predictBtn.disabled    = false;
    predictBtn.textContent = "Predict";
  }
});

// ---------------------------------------------------------------------------
// Render result
// ---------------------------------------------------------------------------
function renderResult({ digit, confidence, top3 }) {
  digitEl.textContent = String(digit);
  digitEl.style.color = "#a6e3a1";

  const pct = (confidence * 100).toFixed(1);
  confEl.textContent  = `Confidence: ${pct}%`;
  confEl.className    = "confidence" + (confidence < 0.5 ? " low" : "");

  // Top-3 bar chart
  barsEl.innerHTML = "";
  top3.forEach(({ digit: d, probability: p }) => {
    const isBest = d === digit;
    const row = document.createElement("div");
    row.className = "bar-row";
    row.innerHTML = `
      <span class="bar-digit">${d}</span>
      <div class="bar-track">
        <div class="bar-fill${isBest ? " best" : ""}"
             style="width:${(p * 100).toFixed(1)}%"></div>
      </div>
      <span class="bar-pct">${(p * 100).toFixed(1)}%</span>
    `;
    barsEl.appendChild(row);
  });
}
