"""
Handwritten Digit Recognizer
----------------------------
Draw a digit (0-9) on the canvas and press "Predict" to see what the
model thinks you wrote.  On first launch the model is trained on MNIST
(~30 s on CPU); subsequent launches reuse the saved weights.
"""

import os
import tkinter as tk
from tkinter import ttk, font as tkfont
import threading

import numpy as np
from PIL import Image, ImageDraw, ImageOps
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, transforms

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
MODEL_PATH = os.path.join(os.path.dirname(__file__), "mnist_cnn.pt")
CANVAS_SIZE = 280          # pixels shown to the user
IMG_SIZE    = 28           # MNIST standard size
BRUSH_WIDTH = 18           # drawing brush radius in canvas pixels
DEVICE      = torch.device("mps" if torch.backends.mps.is_available()
                            else "cpu")


# ---------------------------------------------------------------------------
# Model definition — small but effective CNN
# ---------------------------------------------------------------------------
class DigitCNN(nn.Module):
    """Two-block convolutional network for 28×28 greyscale digit images."""

    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),   # 28×28 → 28×28
            nn.ReLU(),
            nn.MaxPool2d(2),                               # → 14×14
            nn.Conv2d(32, 64, kernel_size=3, padding=1),  # 14×14
            nn.ReLU(),
            nn.MaxPool2d(2),                               # → 7×7
        )
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(64 * 7 * 7, 128),
            nn.ReLU(),
            nn.Dropout(0.4),
            nn.Linear(128, 10),
        )

    def forward(self, x):
        return self.classifier(self.features(x))


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------
def train_model(status_callback=None):
    """Download MNIST and train for a few epochs; save weights to disk."""

    def log(msg):
        if status_callback:
            status_callback(msg)
        print(msg)

    log("Downloading MNIST dataset...")
    tfm = transforms.Compose([transforms.ToTensor(),
                               transforms.Normalize((0.1307,), (0.3081,))])
    train_ds = datasets.MNIST("./data", train=True,  download=True, transform=tfm)
    test_ds  = datasets.MNIST("./data", train=False, download=True, transform=tfm)

    train_loader = DataLoader(train_ds, batch_size=256, shuffle=True,  num_workers=0)
    test_loader  = DataLoader(test_ds,  batch_size=512, shuffle=False, num_workers=0)

    model = DigitCNN().to(DEVICE)
    optimizer = optim.Adam(model.parameters(), lr=1e-3)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=3, gamma=0.5)
    criterion = nn.CrossEntropyLoss()

    epochs = 5
    for epoch in range(1, epochs + 1):
        model.train()
        running_loss = 0.0
        for imgs, labels in train_loader:
            imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
            optimizer.zero_grad()
            loss = criterion(model(imgs), labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item()

        # Evaluate on test set
        model.eval()
        correct = total = 0
        with torch.no_grad():
            for imgs, labels in test_loader:
                imgs, labels = imgs.to(DEVICE), labels.to(DEVICE)
                preds = model(imgs).argmax(dim=1)
                correct += (preds == labels).sum().item()
                total   += labels.size(0)
        acc = correct / total * 100
        log(f"Epoch {epoch}/{epochs}  loss={running_loss/len(train_loader):.4f}  "
            f"test acc={acc:.2f}%")
        scheduler.step()

    torch.save(model.state_dict(), MODEL_PATH)
    log(f"Model saved → {MODEL_PATH}")
    return model


def load_model():
    """Load trained weights from disk."""
    model = DigitCNN().to(DEVICE)
    model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE,
                                     weights_only=True))
    model.eval()
    return model


# ---------------------------------------------------------------------------
# Preprocessing: canvas image → model input tensor
# ---------------------------------------------------------------------------
def preprocess_canvas(pil_image: Image.Image) -> torch.Tensor:
    """
    Resize the drawn image to 28×28, invert colours (black bg → white digit),
    normalise, and return a (1,1,28,28) tensor ready for inference.
    """
    img = pil_image.convert("L")                    # greyscale
    img = img.resize((IMG_SIZE, IMG_SIZE), Image.LANCZOS)

    # Canvas background is white; MNIST digits are white-on-black.
    # Invert so the drawn stroke becomes white on black background.
    img = ImageOps.invert(img)

    arr = np.array(img, dtype=np.float32) / 255.0
    arr = (arr - 0.1307) / 0.3081                   # same normalisation as training
    tensor = torch.tensor(arr).unsqueeze(0).unsqueeze(0)  # (1,1,28,28)
    return tensor.to(DEVICE)


# ---------------------------------------------------------------------------
# GUI
# ---------------------------------------------------------------------------
class App(tk.Tk):
    """Main application window."""

    def __init__(self):
        super().__init__()
        self.title("Handwritten Digit Recognizer")
        self.resizable(False, False)
        self.configure(bg="#1e1e2e")

        self.model = None
        self._build_ui()
        self._initialize_model()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _build_ui(self):
        title_font  = tkfont.Font(family="Helvetica", size=16, weight="bold")
        label_font  = tkfont.Font(family="Helvetica", size=13)
        result_font = tkfont.Font(family="Helvetica", size=48, weight="bold")
        btn_font    = tkfont.Font(family="Helvetica", size=12, weight="bold")

        # ── Title ──────────────────────────────────────────────────────
        tk.Label(self, text="Handwritten Digit Recognizer",
                 font=title_font, bg="#1e1e2e", fg="#cdd6f4"
                 ).pack(pady=(16, 4))
        tk.Label(self, text="Draw a digit (0–9) in the box below",
                 font=label_font, bg="#1e1e2e", fg="#a6adc8"
                 ).pack(pady=(0, 8))

        # ── Drawing canvas ─────────────────────────────────────────────
        frame = tk.Frame(self, bg="#313244", bd=3, relief="ridge")
        frame.pack(padx=20)

        self.canvas = tk.Canvas(frame,
                                width=CANVAS_SIZE, height=CANVAS_SIZE,
                                bg="white", cursor="crosshair",
                                highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<B1-Motion>",      self._on_paint)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        self.canvas.bind("<Button-1>",       self._on_click)

        # Off-screen PIL image used for model inference
        self._pil_img  = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), "white")
        self._pil_draw = ImageDraw.Draw(self._pil_img)
        self._last_xy  = None

        # ── Buttons ────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg="#1e1e2e")
        btn_frame.pack(pady=12, padx=20, fill="x")

        self.predict_btn = tk.Button(
            btn_frame, text="Predict", command=self._predict,
            font=btn_font, bg="#89b4fa", fg="#1e1e2e",
            activebackground="#74c7ec", relief="flat",
            padx=20, pady=8, state="disabled"
        )
        self.predict_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))

        tk.Button(
            btn_frame, text="Clear", command=self._clear,
            font=btn_font, bg="#f38ba8", fg="#1e1e2e",
            activebackground="#eba0ac", relief="flat",
            padx=20, pady=8
        ).pack(side="left", expand=True, fill="x")

        # ── Result display ─────────────────────────────────────────────
        result_frame = tk.Frame(self, bg="#313244", bd=2, relief="groove")
        result_frame.pack(padx=20, pady=(0, 8), fill="x")

        tk.Label(result_frame, text="Prediction",
                 font=label_font, bg="#313244", fg="#a6adc8"
                 ).pack(pady=(8, 0))

        self.digit_label = tk.Label(result_frame, text="—",
                                    font=result_font,
                                    bg="#313244", fg="#a6e3a1")
        self.digit_label.pack()

        self.conf_label = tk.Label(result_frame, text="",
                                   font=label_font,
                                   bg="#313244", fg="#cdd6f4")
        self.conf_label.pack(pady=(0, 8))

        # ── Top-3 bar chart ────────────────────────────────────────────
        self.bar_frame = tk.Frame(result_frame, bg="#313244")
        self.bar_frame.pack(pady=(0, 10), padx=16, fill="x")
        self._bar_widgets = []

        # ── Status bar ─────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Loading model…")
        tk.Label(self, textvariable=self.status_var,
                 font=tkfont.Font(family="Helvetica", size=10),
                 bg="#1e1e2e", fg="#6c7086"
                 ).pack(pady=(0, 10))

    # ------------------------------------------------------------------
    # Model initialisation (runs in a background thread to keep UI alive)
    # ------------------------------------------------------------------
    def _initialize_model(self):
        def worker():
            if os.path.exists(MODEL_PATH):
                self._set_status("Loading saved model…")
                self.model = load_model()
                self._set_status("Model loaded. Start drawing!")
            else:
                self._set_status("No saved model found — training on MNIST…")
                self.model = train_model(status_callback=self._set_status)
                self._set_status("Training complete! Start drawing.")
            self.after(0, lambda: self.predict_btn.config(state="normal"))

        threading.Thread(target=worker, daemon=True).start()

    def _set_status(self, msg: str):
        """Thread-safe status bar update."""
        self.after(0, lambda: self.status_var.set(msg))

    # ------------------------------------------------------------------
    # Drawing callbacks
    # ------------------------------------------------------------------
    def _on_click(self, event):
        self._last_xy = (event.x, event.y)

    def _on_paint(self, event):
        x, y = event.x, event.y
        r = BRUSH_WIDTH // 2
        self.canvas.create_oval(x - r, y - r, x + r, y + r,
                                fill="black", outline="black")
        if self._last_xy:
            lx, ly = self._last_xy
            self.canvas.create_line(lx, ly, x, y,
                                    fill="black", width=BRUSH_WIDTH,
                                    capstyle=tk.ROUND, joinstyle=tk.ROUND)
        self._pil_draw.ellipse([x - r, y - r, x + r, y + r],
                               fill="black", outline="black")
        if self._last_xy:
            lx, ly = self._last_xy
            self._pil_draw.line([lx, ly, x, y],
                                fill="black", width=BRUSH_WIDTH)
        self._last_xy = (x, y)

    def _on_release(self, _event):
        self._last_xy = None

    # ------------------------------------------------------------------
    # Clear
    # ------------------------------------------------------------------
    def _clear(self):
        self.canvas.delete("all")
        self._pil_img  = Image.new("RGB", (CANVAS_SIZE, CANVAS_SIZE), "white")
        self._pil_draw = ImageDraw.Draw(self._pil_img)
        self.digit_label.config(text="—", fg="#a6e3a1")
        self.conf_label.config(text="")
        for w in self._bar_widgets:
            w.destroy()
        self._bar_widgets.clear()

    # ------------------------------------------------------------------
    # Prediction
    # ------------------------------------------------------------------
    def _predict(self):
        if self.model is None:
            return
        tensor = preprocess_canvas(self._pil_img)
        with torch.no_grad():
            logits = self.model(tensor)                   # (1, 10)
            probs  = torch.softmax(logits, dim=1)[0]      # (10,)

        best_digit = probs.argmax().item()
        confidence = probs[best_digit].item()

        # Main result
        self.digit_label.config(text=str(best_digit), fg="#a6e3a1")
        self.conf_label.config(
            text=f"Confidence: {confidence * 100:.1f}%",
            fg="#cdd6f4" if confidence >= 0.5 else "#f38ba8"
        )

        # Top-3 bar chart
        for w in self._bar_widgets:
            w.destroy()
        self._bar_widgets.clear()

        top3 = probs.topk(3)
        bar_font = tkfont.Font(family="Helvetica", size=10)
        for val, idx in zip(top3.values.tolist(), top3.indices.tolist()):
            row = tk.Frame(self.bar_frame, bg="#313244")
            row.pack(fill="x", pady=1)
            self._bar_widgets.append(row)

            tk.Label(row, text=f"  {idx}", width=3, font=bar_font,
                     bg="#313244", fg="#cdd6f4", anchor="e").pack(side="left")

            bar_bg = tk.Frame(row, bg="#45475a", height=14, width=200)
            bar_bg.pack(side="left", padx=6)
            bar_bg.pack_propagate(False)

            bar_fill = tk.Frame(bar_bg,
                                bg="#89b4fa" if idx == best_digit else "#74c7ec",
                                height=14, width=max(4, int(val * 200)))
            bar_fill.place(x=0, y=0)
            self._bar_widgets.append(bar_bg)

            tk.Label(row, text=f"{val * 100:.1f}%", font=bar_font,
                     bg="#313244", fg="#cdd6f4").pack(side="left")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app = App()
    app.mainloop()
