# Created: 2026-04-17 16:41:03
#!/usr/bin/env python3
"""
Auto-update the AUTO-GENERATED section of each project's CLAUDE.md
whenever a Python source file is edited.

Usage (called by Claude Code PostToolUse hook):
    python3 update_claude_md.py          # reads CLAUDE_TOOL_INPUT env var
    python3 update_claude_md.py <path>   # explicit file path (for testing)

Projects are auto-discovered: any directory under vibecoding/ that contains
both a CLAUDE.md and at least one .py file is tracked automatically.
"""

import ast
import json
import os
import sys
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent  # /Users/coffin/vibecoding
SKIP_DIRS = {"scripts", ".git", ".claude", "__pycache__"}

START_MARKER = "<!-- AUTO-GENERATED START -->"
END_MARKER   = "<!-- AUTO-GENERATED END -->"


# ── Project discovery ─────────────────────────────────────────────────────────

def find_projects() -> dict[Path, list[str]]:
    """Return {proj_dir: [py_filenames]} for every dir with CLAUDE.md + .py files."""
    projects: dict[Path, list[str]] = {}
    for claude_md in sorted(BASE_DIR.rglob("CLAUDE.md")):
        proj_dir = claude_md.parent
        if any(part in SKIP_DIRS for part in proj_dir.parts):
            continue
        py_files = sorted(p.name for p in proj_dir.glob("*.py"))
        if py_files:
            projects[proj_dir] = py_files
    return projects


# ── AST analysis ──────────────────────────────────────────────────────────────

def _unparse(node) -> str:
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
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)

        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            names = [a.name for a in node.names]
            preview = ", ".join(names[:4])
            suffix = "..." if len(names) > 4 else ""
            imports.append(f"{mod} ({preview}{suffix})")

        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.isupper():
                    val = _unparse(node.value)
                    if len(val) > 60:
                        val = val[:57] + "..."
                    constants.append((target.id, val))

        elif isinstance(node, ast.ClassDef):
            bases = [_unparse(b) for b in node.bases]
            methods = [
                n.name
                for n in node.body
                if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
                and not n.name.startswith("__")
            ]
            classes.append({"name": node.name, "bases": bases, "methods": methods})

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

def generate_auto_section(proj_dir: Path, py_files: list[str]) -> str:
    lines: list[str] = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines.append(f"_Last auto-updated: {now}_\n")

    for fname in py_files:
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

def update_claude_md(proj_dir: Path, py_files: list[str]) -> None:
    claude_md = proj_dir / "CLAUDE.md"
    if not claude_md.exists():
        return

    content = claude_md.read_text()
    auto_block = f"{START_MARKER}\n{generate_auto_section(proj_dir, py_files)}\n{END_MARKER}"

    if START_MARKER in content and END_MARKER in content:
        s = content.index(START_MARKER)
        e = content.index(END_MARKER) + len(END_MARKER)
        new_content = content[:s] + auto_block + content[e:]
    else:
        new_content = content.rstrip() + "\n\n" + auto_block + "\n"

    claude_md.write_text(new_content)
    print(f"[update_claude_md] Updated {claude_md}")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
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

    if filepath.suffix != ".py":
        return

    projects = find_projects()

    for proj_dir, py_files in projects.items():
        try:
            filepath.relative_to(proj_dir)
            update_claude_md(proj_dir, py_files)
            return
        except ValueError:
            continue

    print(f"[update_claude_md] {filepath} not in any tracked project — skipping")


if __name__ == "__main__":
    main()
