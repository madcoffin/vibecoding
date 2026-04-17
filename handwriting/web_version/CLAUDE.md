# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Planned stack

| Layer | Technology | Rationale |
|---|---|---|
| Backend | FastAPI (Python 3.14) | Async, auto-docs at `/docs`, easy model serving |
| ML model | PyTorch — same `DigitCNN` CNN as the desktop version | Reuse trained weights from `../desktop_version/mnist_cnn.pt` |
| Frontend | HTML5 Canvas + vanilla JS | No build step, runs in any browser |
| Styling | Plain CSS (dark theme matching desktop) | No framework dependency |

## Planned file layout

```
web_version/
├── server.py          # FastAPI app — model loading + /predict endpoint
├── static/
│   ├── index.html     # Single-page UI with drawing canvas
│   ├── style.css
│   └── app.js         # Canvas drawing logic + fetch to /predict
└── requirements.txt   # fastapi uvicorn torch torchvision pillow numpy
```

## Commands (once implemented)

```bash
# Install dependencies
pip3 install fastapi uvicorn torch torchvision pillow numpy --break-system-packages

# Start dev server (auto-reload)
uvicorn server:app --reload --port 8000

# Open in browser
open http://localhost:8000
```

## Architecture plan

**Backend (`server.py`)**
- On startup: load `DigitCNN` weights from `../desktop_version/mnist_cnn.pt`
- `POST /predict` — accepts a base64-encoded PNG of the drawn canvas, returns `{ digit, confidence, top3 }`
- The same `preprocess_canvas()` logic as the desktop version: greyscale → resize 28×28 → invert → normalise `(0.1307, 0.3081)`

**Frontend (`app.js`)**
- 280×280 `<canvas>` with mouse/touch drawing (black strokes on white bg)
- On "Predict": export canvas as PNG with `canvas.toDataURL()`, POST base64 to `/predict`, render result
- On "Clear": reset canvas

**Shared model weights**
The web backend reads `../desktop_version/mnist_cnn.pt` at startup. If you want the web version to be self-contained, copy the file to `web_version/mnist_cnn.pt` and update the path in `server.py`.

## Key design constraint

The preprocessing pipeline (colour inversion + normalisation constants) **must match** what was used during training (`desktop_version/app.py :: preprocess_canvas()`). Deviating from this is the most common source of poor web predictions.

<!-- AUTO-GENERATED START -->
_Last auto-updated: 2026-04-17 16:41:51_

## `server.py` — Code Structure

### Dependencies
- `base64`
- `io`
- `os`
- `pathlib (Path)`
- `numpy`
- `torch`
- `torch.nn`
- `fastapi (FastAPI)`
- `fastapi.responses (HTMLResponse)`
- `fastapi.staticfiles (StaticFiles)`
- `PIL (Image, ImageOps)`
- `pydantic (BaseModel)`

### Constants
- `BASE_DIR` = `Path(__file__).parent`
- `MODEL_PATH` = `BASE_DIR.parent / 'desktop_version' / 'mnist_cnn.pt'`
- `STATIC_DIR` = `BASE_DIR / 'static'`
- `DEVICE` = `torch.device('mps' if torch.backends.mps.is_available() e...`

### Classes
- **`DigitCNN`**(nn.Module)
  - `forward()`
- **`PredictRequest`**(BaseModel)
- **`Top3Item`**(BaseModel)
- **`PredictResponse`**(BaseModel)

### Functions
- `preprocess(data_url)`
- `predict(req)`

<!-- AUTO-GENERATED END -->
