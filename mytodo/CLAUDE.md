# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Overview

This is a multi-project workspace with two independent Python applications. There is no monorepo build system — each project is self-contained.

```
mytodo/
├── handwriting/
│   ├── desktop_version/   # Tkinter + PyTorch digit recognizer (macOS .app bundle)
│   ├── web_version/       # FastAPI + HTML5 Canvas digit recognizer
│   └── CLAUDE.md          # Shared model/preprocessing context
└── query/                 # Tkinter CSV-to-SQL query generator
```

Each subdirectory has its own `CLAUDE.md` with project-specific details — read those when working within a project.

## Running Projects

**Desktop handwriting recognizer:**
```bash
cd handwriting/desktop_version
python3 app.py                  # trains model on first run, then opens GUI
rm mnist_cnn.pt && python3 app.py  # force retrain
```

**Web handwriting recognizer:**
```bash
cd handwriting/web_version
pip3 install fastapi uvicorn torch torchvision pillow numpy --break-system-packages
uvicorn server:app --reload --port 8000
```

**SQL query generator:**
```bash
cd query
python3 query_generator.py
```

## Language & Dependencies

- **Python 3.14** (Homebrew) — all projects
- **PyTorch** (not TensorFlow — unsupported on Python 3.14)
- Install packages with `pip3 install ... --break-system-packages`
- No requirements.txt, pyproject.toml, or Makefile — dependencies are listed in each project's CLAUDE.md

## Architecture Notes

**Shared handwriting model**: `DigitCNN` — 2-block CNN (Conv2d 32→64 filters), FC(128)→Dropout(0.4)→FC(10), trained 5 epochs on MNIST. Weights live at `handwriting/desktop_version/mnist_cnn.pt`. The web version must use identical preprocessing (280×280 → 28×28, color invert, normalize mean=0.1307 std=0.3081).

**Query generator**: Reads CSV (UTF-8, columns `이메일` + `상품코드`), outputs a PostgreSQL CTE query joining `members`/`products`/`my_contents`. Row order is preserved via an `idx` column in the VALUES clause. Uses `FlatBtn` (Label-based) instead of `tk.Button` to work around macOS Tk color limitations.

**UI theme**: Both handwriting apps use the Catppuccin dark palette (`#1e1e2e` bg, `#a6e3a1` green, `#89b4fa` blue).
