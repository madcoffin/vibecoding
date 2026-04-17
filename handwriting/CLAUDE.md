# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

```
handwriting/
├── desktop_version/   # Tkinter + PyTorch desktop app (macOS .app bundle)
└── web_version/       # FastAPI backend + HTML5 canvas frontend (planned)
```

Each sub-folder has its own `CLAUDE.md` with stack-specific details.

## Shared context

Both versions use the **same model architecture** (`DigitCNN` — a two-block CNN trained on MNIST) and the **same preprocessing pipeline** (greyscale → 28×28 → colour-invert → normalise with mean=0.1307, std=0.3081).

The trained weights live at `desktop_version/mnist_cnn.pt`. The web version reads them from there by default; copy the file if you need the web version to be standalone.

## Dependencies (both versions)

Python 3.14 (Homebrew). TensorFlow does **not** support Python 3.14 — use PyTorch only.

```bash
pip3 install torch torchvision pillow numpy --break-system-packages
# Web version also needs:
pip3 install fastapi uvicorn --break-system-packages
```
