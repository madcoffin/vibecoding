# file_renamer

## 개요
PyQt6 기반의 GUI 파일 일괄 변경 앱. 지정 폴더 내 파일들의 이름을 생성일 기준 오름차순으로 정렬 후, 특정 접두사를 제거하고 순번(`01_`, `02_`, …)을 붙여 일괄 변경한다.

## 실행 방법
```bash
python file_renamer.py
```

## 의존성
- Python 3.x
- PyQt6

## 주요 설정
- `PREFIX_TO_REMOVE` : 제거할 접두사 문자열 (파일 상단에 하드코딩)
- macOS의 `st_birthtime`으로 생성일을 가져오며, 없을 경우 `st_mtime`으로 폴백

## 주의사항
- 이미 같은 이름의 파일이 존재하면 덮어쓰지 않고 건너뜀
- 실행 취소 기능 없음 — 변경 전 백업 권장

<!-- AUTO-GENERATED START -->
_Last auto-updated: 2026-04-13 10:07:52_

## `file_renamer.py` — Code Structure

### Dependencies
- `sys`
- `os`
- `PyQt6.QtWidgets (QApplication, QMainWindow, QWidget, QVBoxLayout...)`
- `PyQt6.QtCore (Qt)`
- `PyQt6.QtGui (QFont)`

### Constants
- `PREFIX_TO_REMOVE` = `'[전기기사] 단답암기신공_'`

### Classes
- **`MainWindow`**(QMainWindow)
  - `_build_ui()`
  - `_browse()`
  - `_log()`
  - `_run()`

### Functions
- `get_creation_time(path)`
- `rename_files(directory, log)`
- `main()`

<!-- AUTO-GENERATED END -->
