#!/usr/bin/env python3
"""
Auto-update the AUTO-GENERATED section of each project's CLAUDE.md
whenever a Python source file is edited.

Usage (called by Claude Code PostToolUse hook):
    python3 update_claude_md.py          # reads CLAUDE_TOOL_INPUT env var
    python3 update_claude_md.py <path>   # explicit file path (for testing)
"""

import ast
import json
import os
import sys
from datetime import datetime
from pathlib import Path

# ── Project registry ──────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent.parent  # /Users/kwan/vibecoding

PROJECTS: dict[Path, list[str]] = {
    BASE_DIR / "file_renamer":      ["file_renamer.py"],
    BASE_DIR / "youtube_downloader": ["youtube_downloader.py"],
}

START_MARKER = "<!-- AUTO-GENERATED START -->"
END_MARKER   = "<!-- AUTO-GENERATED END -->"


# ── AST analysis ──────────────────────────────────────────────────────────────

def _unparse(node) -> str:
    """ast.unparse with fallback for older Python versions."""
    if hasattr(ast, "unparse"):
        return ast.unparse(node)
    return "..."


def parse_python_file(filepath: Path) -> dict | None:
    try:
        source = filepath.read_text()
        tree = ast.parse(source, filename=str(filepath))
    except (SyntaxError, OSError):
        return None

    imports: list[str] = []
    constants: list[tuple[str, str]] = []
    classes: list[dict] = []
    functions: list[dict] = []

    for node in tree.body:
        # imports
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = [a.name for a in node.names]
            preview = ", ".join(names[:4])
            suffix = "..." if len(names) > 4 else ""
            imports.append(f"{mod} ({preview}{suffix})")

        # UPPER_CASE constants
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    val = _unparse(node.value)
                    if len(val) > 60:
                        val = val[:57] + "..."
                    constants.append((target.id, val))

        # classes
        elif isinstance(node, ast.ClassDef):
            bases = [_unparse(b) for b in node.bases]
            methods = [
                n.name
                for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not n.name.startswith("__")
            ]
            classes.append({"name": node.name, "bases": bases, "methods": methods})

        # top-level functions
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            args = [a.arg for a in node.args.args]
            functions.append({"name": node.name, "args": args})

    return {
        "imports":   imports,
        "constants": constants,
        "classes":   classes,
        "functions": functions,
    }


# ── Section generation ────────────────────────────────────────────────────────

def generate_auto_section(proj_dir: Path) -> str:
    lines: list[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"_Last auto-updated: {now}_\n")

    for fname in PROJECTS[proj_dir]:
        fpath = proj_dir / fname
        if not fpath.exists():
            continue

        info = parse_python_file(fpath)
        if info is None:
            lines.append(f"_`{fname}` — 파싱 실패 (SyntaxError?)_\n")
            continue

        lines.append(f"## `{fname}` — Code Structure\n")

        if info["imports"]:
            lines.append("### Dependencies")
            for imp in info["imports"]:
                lines.append(f"- `{imp}`")
            lines.append("")

        if info["constants"]:
            lines.append("### Constants")
            for name, val in info["constants"]:
                lines.append(f"- `{name}` = `{val}`")
            lines.append("")

        if info["classes"]:
            lines.append("### Classes")
            for cls in info["classes"]:
                bases_str = f"({', '.join(cls['bases'])})" if cls["bases"] else ""
                lines.append(f"- **`{cls['name']}`**{bases_str}")
                for m in cls["methods"]:
                    lines.append(f"  - `{m}()`")
            lines.append("")

        if info["functions"]:
            lines.append("### Functions")
            for fn in info["functions"]:
                args_str = ", ".join(fn["args"])
                lines.append(f"- `{fn['name']}({args_str})`")
            lines.append("")

    return "\n".join(lines)


# ── CLAUDE.md update ──────────────────────────────────────────────────────────

def update_claude_md(proj_dir: Path) -> None:
    claude_md = proj_dir / "CLAUDE.md"
    if not claude_md.exists():
        print(f"[update_claude_md] {claude_md} not found — skipping")
        return

    content = claude_md.read_text()
    auto_block = f"{START_MARKER}\n{generate_auto_section(proj_dir)}\n{END_MARKER}"

    if START_MARKER in content and END_MARKER in content:
        s = content.index(START_MARKER)
        e = content.index(END_MARKER) + len(END_MARKER)
        new_content = content[:s] + auto_block + content[e:]
    else:
        new_content = content.rstrip() + "\n\n" + auto_block + "\n"

    claude_md.write_text(new_content)
    print(f"[update_claude_md] Updated {claude_md}")


# ── Project lookup ────────────────────────────────────────────────────────────

def get_project(filepath: Path) -> Path | None:
    for proj_dir in PROJECTS:
        try:
            filepath.relative_to(proj_dir)
            return proj_dir
        except ValueError:
            continue
    return None


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    # Resolve file path: CLI arg > CLAUDE_TOOL_INPUT env var
    file_path: str = ""

    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        raw = os.environ.get("CLAUDE_TOOL_INPUT", "")
        if raw:
            try:
                data = json.loads(raw)
                file_path = data.get("file_path", "")
            except json.JSONDecodeError:
                pass

    if not file_path:
        print("[update_claude_md] No file path — nothing to do")
        return

    filepath = Path(file_path).resolve()

    # Skip non-Python files and CLAUDE.md itself
    if filepath.suffix != ".py":
        return

    proj_dir = get_project(filepath)
    if proj_dir is None:
        return  # file not in a tracked project

    update_claude_md(proj_dir)


if __name__ == "__main__":
    main()
