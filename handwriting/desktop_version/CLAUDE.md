# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Run the app from the terminal
python3 app.py

# Launch via Finder (double-click)
open HandwritingRecognizer.app

# Re-train the model (delete weights first)
rm mnist_cnn.pt && python3 app.py

# Register the .app with macOS after any bundle change
xattr -cr HandwritingRecognizer.app
/System/Library/Frameworks/CoreServices.framework/Versions/A/Frameworks/LaunchServices.framework/Versions/A/Support/lsregister -f HandwritingRecognizer.app
```

## Dependencies

Python 3.14 (Homebrew). Install with:

```bash
pip3 install torch torchvision numpy pillow --break-system-packages
```

`tkinter` ships with Homebrew Python. TensorFlow does **not** support Python 3.14 — use PyTorch only.

## Architecture

Everything lives in `app.py` as a single file with four logical sections:

| Section | Key names | Purpose |
|---|---|---|
| Config | `MODEL_PATH`, `CANVAS_SIZE`, `DEVICE` | Constants; `DEVICE` auto-selects Apple MPS |
| Model | `DigitCNN` | 2-block CNN: Conv→ReLU→MaxPool ×2, FC(128)→Dropout(0.4)→FC(10) |
| Training / loading | `train_model()`, `load_model()` | Downloads MNIST to `./data/`, trains 5 epochs, saves `mnist_cnn.pt` |
| GUI | `App(tk.Tk)` | Tkinter window; model init runs in a background thread |

**Inference pipeline:** the Tkinter canvas (280×280, white bg, black strokes) is mirrored to an off-screen `PIL.Image`. On "Predict", `preprocess_canvas()` resizes it to 28×28, **inverts** colours (canvas is white-on-black; MNIST expects white digit on black), and applies `(mean=0.1307, std=0.3081)` normalisation before passing to the model.

**Dual-write pattern:** every brush stroke is drawn on both the `tk.Canvas` (display) and a `PIL.Image` (inference source). Keeping these in sync is critical — if only one is updated, predictions will be wrong.

## macOS .app bundle

`HandwritingRecognizer.app` is a shell-launcher bundle (not a PyInstaller bundle) — Python and packages are **not** embedded. The launcher at `Contents/MacOS/HandwritingRecognizer`:

1. Searches Homebrew Python paths for a working interpreter
2. Verifies `torch`, `PIL`, `numpy`, `tkinter` are importable; pops an `osascript` alert if not
3. `cd`s into `desktop_version/` and `exec`s `app.py`

`APP_DIR` is resolved as three `..` levels up from `Contents/MacOS/`, which correctly points to `desktop_version/`. If the bundle is moved, this still works as long as `app.py` stays beside it.

## Model file

`mnist_cnn.pt` — saved PyTorch `state_dict`. Delete it to trigger re-training on next launch. The MNIST raw data in `data/` is reused automatically.

<!-- AUTO-GENERATED START -->
_Last auto-updated: 2026-04-17 16:41:51_

## `app.py` — Code Structure

### Dependencies
- `os`
- `tkinter`
- `tkinter (ttk, font)`
- `threading`
- `numpy`
- `PIL (Image, ImageDraw, ImageOps)`
- `torch`
- `torch.nn`
- `torch.optim`
- `torch.utils.data (DataLoader)`
- `torchvision (datasets, transforms)`

### Constants
- `MODEL_PATH` = `os.path.join(os.path.dirname(__file__), 'mnist_cnn.pt')`
- `CANVAS_SIZE` = `280`
- `IMG_SIZE` = `28`
- `BRUSH_WIDTH` = `18`
- `DEVICE` = `torch.device('mps' if torch.backends.mps.is_available() e...`

### Classes
- **`DigitCNN`**(nn.Module)
  - `forward()`
- **`App`**(tk.Tk)
  - `_build_ui()`
  - `_initialize_model()`
  - `_set_status()`
  - `_on_click()`
  - `_on_paint()`
  - `_on_release()`
  - `_clear()`
  - `_predict()`

### Functions
- `train_model(status_callback)`
- `load_model()`
- `preprocess_canvas(pil_image)`

<!-- AUTO-GENERATED END -->
