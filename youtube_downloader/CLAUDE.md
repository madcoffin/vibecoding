# youtube_downloader

## 개요
PyQt6 기반의 YouTube 재생목록 다운로더. Pac-Man 테마 UI를 갖추고 있으며 `yt_dlp`로 영상을 다운받는다. ffmpeg가 설치된 경우 최고 화질 MP4로 병합하고, 없으면 단일 스트림 모드로 동작한다.

## 실행 방법
```bash
python youtube_downloader.py
```

## 의존성
- Python 3.x
- PyQt6
- yt_dlp  (`pip install yt-dlp`)
- ffmpeg (선택, 최고화질 다운로드 시 필요) — `brew install ffmpeg`

## 주요 동작
1. URL 입력 → 재생목록 정보 추출 (`yt_dlp` flat extract)
2. 영상별 순차 다운로드 (별도 데몬 스레드)
3. Pac-Man 프로그레스 바로 진행률 표시
4. 취소 버튼으로 중단 가능

## 저장 위치
기본값: `~/Downloads` — UI에서 변경 가능

## 주의사항
- 단일 영상 URL도 지원 (`entries`가 없으면 `[info]`로 처리)
- 취소 시 `cancel_flag`를 통해 다음 영상 시작 전 중단 (현재 다운로드 중인 파일은 잔류할 수 있음)

<!-- AUTO-GENERATED START -->
_Last auto-updated: 2026-04-13 10:07:52_

## `youtube_downloader.py` — Code Structure

### Dependencies
- `sys`
- `os`
- `shutil`
- `threading`
- `math`
- `yt_dlp`
- `PyQt6.QtWidgets (QApplication, QMainWindow, QWidget, QVBoxLayout...)`
- `PyQt6.QtCore (Qt, QObject, pyqtSignal, pyqtSlot...)`
- `PyQt6.QtGui (QFont, QTextCursor, QPainter, QColor...)`

### Constants
- `FFMPEG_AVAILABLE` = `shutil.which('ffmpeg') is not None`
- `BG` = `'#000000'`
- `MAZE` = `'#2121DE'`
- `YELLOW` = `'#FFD700'`
- `RED` = `'#FF0000'`
- `PINK` = `'#FFB8DE'`
- `CYAN` = `'#00FFDE'`
- `ORANGE` = `'#FFB852'`
- `WHITE` = `'#FFFFFF'`
- `DOT_COLOR` = `'#DEDEBE'`
- `DARK_PANEL` = `'#0a0a1a'`

### Classes
- **`PacManBar`**(QWidget)
  - `_blink()`
  - `set_value()`
  - `paintEvent()`
- **`MazeFrame`**(QFrame)
- **`Signals`**(QObject)
- **`MainWindow`**(QMainWindow)
  - `_label()`
  - `_maze_section_title()`
  - `_build_ui()`
  - `_header()`
  - `_url_section()`
  - `_dir_section()`
  - `_button_section()`
  - `_progress_section()`
  - `_log_section()`
  - `_choose_dir()`
  - `_start_download()`
  - `_cancel_download()`
  - `_append_log()`
  - `_update_status()`
  - `_update_progress()`
  - `_on_done()`
  - `_download_worker()`
  - `_make_hook()`

<!-- AUTO-GENERATED END -->
