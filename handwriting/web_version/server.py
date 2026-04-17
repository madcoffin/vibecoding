# Created: 2026-04-17 14:35:00
"""
FastAPI backend for the Handwritten Digit Recognizer web version.
Serves the static frontend and exposes a /predict endpoint.
"""

import base64
import io
import os
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR   = Path(__file__).parent
MODEL_PATH = BASE_DIR.parent / "desktop_version" / "mnist_cnn.pt"
STATIC_DIR = BASE_DIR / "static"

# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------
DEVICE = torch.device("mps" if torch.backends.mps.is_available() else "cpu")

# ---------------------------------------------------------------------------
# Model — identical architecture to desktop_version/app.py
# ---------------------------------------------------------------------------
class DigitCNN(nn.Module):
    """Two-block CNN for 28×28 greyscale digit images."""

    def __init__(self):
        super().__init__()
        self.features = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2),
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
# Load model at startup
# ---------------------------------------------------------------------------
model = DigitCNN().to(DEVICE)
model.load_state_dict(torch.load(MODEL_PATH, map_location=DEVICE, weights_only=True))
model.eval()
print(f"Model loaded from {MODEL_PATH}  (device: {DEVICE})")

# ---------------------------------------------------------------------------
# Preprocessing — must match desktop_version/app.py :: preprocess_canvas()
# ---------------------------------------------------------------------------
def preprocess(data_url: str) -> torch.Tensor:
    """
    Convert a base64 PNG data-URL from the browser canvas into a
    (1, 1, 28, 28) normalised tensor ready for inference.
    """
    # Strip "data:image/png;base64," header
    header, encoded = data_url.split(",", 1)
    img_bytes = base64.b64decode(encoded)

    img = Image.open(io.BytesIO(img_bytes)).convert("L")   # greyscale
    img = img.resize((28, 28), Image.LANCZOS)
    img = ImageOps.invert(img)                              # white bg → black, stroke → white

    arr = np.array(img, dtype=np.float32) / 255.0
    arr = (arr - 0.1307) / 0.3081                           # MNIST normalisation
    return torch.tensor(arr).unsqueeze(0).unsqueeze(0).to(DEVICE)  # (1,1,28,28)


# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(title="Handwritten Digit Recognizer")


class PredictRequest(BaseModel):
    image: str   # base64 PNG data-URL


class Top3Item(BaseModel):
    digit: int
    probability: float


class PredictResponse(BaseModel):
    digit: int
    confidence: float
    top3: list[Top3Item]


@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    tensor = preprocess(req.image)
    with torch.no_grad():
        probs = torch.softmax(model(tensor), dim=1)[0]

    top3 = probs.topk(3)
    return PredictResponse(
        digit=int(probs.argmax()),
        confidence=float(probs.max()),
        top3=[
            Top3Item(digit=int(idx), probability=float(val))
            for val, idx in zip(top3.values, top3.indices)
        ],
    )


# Serve static files — index.html at root
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
