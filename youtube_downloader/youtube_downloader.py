import sys
import os
import shutil
import threading
import math
import yt_dlp

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog, QFrame,
)
from PyQt6.QtCore import Qt, QObject, pyqtSignal, pyqtSlot, QTimer, QRect, QRectF
from PyQt6.QtGui import QFont, QTextCursor, QPainter, QColor, QPen, QBrush, QPainterPath

FFMPEG_AVAILABLE = shutil.which("ffmpeg") is not None

# ── Pac-Man palette ─────────────────────────────────────────────────────────
BG          = "#000000"
MAZE        = "#2121DE"
YELLOW      = "#FFD700"
RED         = "#FF0000"
PINK        = "#FFB8DE"
CYAN        = "#00FFDE"
ORANGE      = "#FFB852"
WHITE       = "#FFFFFF"
DOT_COLOR   = "#DEDEBE"
DARK_PANEL  = "#0a0a1a"


# ── Pac-Man Progress Bar (custom widget) ────────────────────────────────────
class PacManBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0          # 0–100
        self.mouth_open = True
        self.setFixedHeight(32)
        self.setStyleSheet(f"background-color: {BG};")

        self._blink_timer = QTimer(self)
        self._blink_timer.timeout.connect(self._blink)
        self._blink_timer.start(200)

    def _blink(self):
        self.mouth_open = not self.mouth_open
        self.update()

    def set_value(self, v):
        self.value = max(0, min(100, v))
        self.update()

    def paintEvent(self, _event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        dot_r = 3
        dot_y = h // 2
        pad = 20          # left/right padding
        track_w = w - pad * 2
        pac_size = 22

        # ── dots ──────────────────────────────────────────────────────────
        n_dots = 28
        spacing = track_w / (n_dots + 1)
        eaten_x = pad + track_w * self.value / 100

        p.setPen(Qt.PenStyle.NoPen)
        for i in range(1, n_dots + 1):
            dx = pad + spacing * i
            if dx < eaten_x - pac_size // 2:
                continue  # eaten — skip
            p.setBrush(QColor(DOT_COLOR))
            if i % 7 == 0:                          # power pellet (bigger)
                p.drawEllipse(int(dx) - 5, dot_y - 5, 10, 10)
            else:
                p.drawEllipse(int(dx) - dot_r, dot_y - dot_r, dot_r * 2, dot_r * 2)

        # ── Pac-Man ───────────────────────────────────────────────────────
        px = int(pad + track_w * self.value / 100) - pac_size // 2
        py = dot_y - pac_size // 2
        rect = QRectF(px, py, pac_size, pac_size)

        p.setBrush(QColor(YELLOW))
        p.setPen(Qt.PenStyle.NoPen)
        if self.mouth_open:
            p.drawPie(rect, 30 * 16, 300 * 16)
        else:
            p.drawEllipse(rect)

        p.end()


# ── Maze border frame ────────────────────────────────────────────────────────
class MazeFrame(QFrame):
    """A panel styled with the classic Pac-Man maze blue border."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            MazeFrame {{
                background-color: {DARK_PANEL};
                border: 3px solid {MAZE};
                border-radius: 4px;
            }}
        """)


# ── Signal bridge ─────────────────────────────────────────────────────────────
class Signals(QObject):
    log      = pyqtSignal(str, str)
    status   = pyqtSignal(str)
    progress = pyqtSignal(int)
    done     = pyqtSignal()


# ── Main Window ───────────────────────────────────────────────────────────────
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ᗧ···  PAC-MAN DOWNLOADER")
        self.setFixedSize(740, 660)
        self.output_dir = os.path.join(os.path.expanduser("~"), "Downloads")
        self.is_downloading = False
        self.cancel_flag = False

        self.signals = Signals()
        self.signals.log.connect(self._append_log)
        self.signals.status.connect(self._update_status)
        self.signals.progress.connect(self._update_progress)
        self.signals.done.connect(self._on_done)

        self._build_ui()

    # ── helpers ───────────────────────────────────────────────────────────────
    def _label(self, text, size=10, bold=False, color=WHITE):
        lbl = QLabel(text)
        weight = QFont.Weight.Bold if bold else QFont.Weight.Normal
        lbl.setFont(QFont("Courier", size, weight))
        lbl.setStyleSheet(f"color: {color}; background: transparent;")
        return lbl

    def _maze_section_title(self, text):
        row = QWidget()
        row.setStyleSheet("background: transparent;")
        rl = QHBoxLayout(row)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(6)
        lbl = self._label(f"── {text} ", 9, bold=True, color=MAZE)
        rl.addWidget(lbl)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {MAZE}; border: 1px solid {MAZE};")
        rl.addWidget(line, stretch=1)
        return row

    # ── UI Construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self.setStyleSheet(f"background-color: {BG}; color: {WHITE};")

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._header())

        body = QWidget()
        body.setStyleSheet(f"background-color: {BG};")
        bl = QVBoxLayout(body)
        bl.setContentsMargins(22, 16, 22, 16)
        bl.setSpacing(12)

        bl.addWidget(self._url_section())
        bl.addWidget(self._dir_section())
        bl.addWidget(self._button_section())
        bl.addWidget(self._progress_section())
        bl.addWidget(self._log_section(), stretch=1)

        root.addWidget(body)

    def _header(self):
        frame = QFrame()
        frame.setStyleSheet(f"background-color: {BG};")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(0, 18, 0, 14)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Pac-Man title row
        title_row = QWidget()
        title_row.setStyleSheet("background: transparent;")
        tr = QHBoxLayout(title_row)
        tr.setContentsMargins(0, 0, 0, 0)
        tr.setAlignment(Qt.AlignmentFlag.AlignCenter)
        tr.setSpacing(12)

        ghost_l = self._label("ᗣ", 22, color=CYAN)
        ghost_l.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title = self._label("PAC-MAN  DOWNLOADER", 20, bold=True, color=YELLOW)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        ghost_r = self._label("ᗣ", 22, color=PINK)
        ghost_r.setAlignment(Qt.AlignmentFlag.AlignCenter)

        tr.addWidget(ghost_l)
        tr.addWidget(title)
        tr.addWidget(ghost_r)

        # Subtitle
        sub = self._label("ᗧ· · · INSERT PLAYLIST URL · · ·ᗤ", 10, color=DOT_COLOR)
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # ffmpeg badge
        if FFMPEG_AVAILABLE:
            ff_text = "▶  FFMPEG DETECTED — MAX QUALITY MODE"
            ff_color = CYAN
        else:
            ff_text = "⚠  FFMPEG NOT FOUND — SINGLE STREAM MODE  |  brew install ffmpeg"
            ff_color = ORANGE
        ff_lbl = self._label(ff_text, 9, color=ff_color)
        ff_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(title_row)
        layout.addWidget(sub)
        layout.addSpacing(4)
        layout.addWidget(ff_lbl)
        return frame

    def _url_section(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(6)
        l.addWidget(self._maze_section_title("STAGE  ·  PLAYLIST URL"))

        panel = MazeFrame()
        pl = QVBoxLayout(panel)
        pl.setContentsMargins(12, 10, 12, 10)

        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.youtube.com/playlist?list=...")
        self.url_input.setFont(QFont("Courier", 11))
        self.url_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {BG};
                color: {YELLOW};
                border: none;
                padding: 6px 4px;
            }}
            QLineEdit::placeholder {{ color: #555; }}
        """)
        pl.addWidget(self.url_input)
        l.addWidget(panel)
        return w

    def _dir_section(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(6)
        l.addWidget(self._maze_section_title("SAVE TO"))

        panel = MazeFrame()
        pl = QHBoxLayout(panel)
        pl.setContentsMargins(12, 8, 12, 8)
        pl.setSpacing(10)

        self.dir_label = QLabel(self.output_dir)
        self.dir_label.setFont(QFont("Courier", 10))
        self.dir_label.setStyleSheet(f"color: {DOT_COLOR}; background: transparent;")

        change_btn = QPushButton("CHANGE")
        change_btn.setFont(QFont("Courier", 10, QFont.Weight.Bold))
        change_btn.setFixedWidth(90)
        change_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        change_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {MAZE};
                color: {WHITE};
                border: 2px solid {CYAN};
                border-radius: 2px;
                padding: 6px;
            }}
            QPushButton:hover {{ background-color: #3535ff; border-color: {WHITE}; }}
        """)
        change_btn.clicked.connect(self._choose_dir)

        pl.addWidget(self.dir_label, stretch=1)
        pl.addWidget(change_btn)
        l.addWidget(panel)
        return w

    def _button_section(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        l = QHBoxLayout(w)
        l.setContentsMargins(0, 4, 0, 4)
        l.setSpacing(14)

        self.download_btn = QPushButton("  ᗧ  START DOWNLOAD  ")
        self.download_btn.setFont(QFont("Courier", 13, QFont.Weight.Bold))
        self.download_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.download_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {YELLOW};
                color: {BG};
                border: 3px solid {YELLOW};
                border-radius: 2px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: #ffe84d;
                border-color: {WHITE};
            }}
            QPushButton:disabled {{
                background-color: #444;
                color: #777;
                border-color: #555;
            }}
        """)
        self.download_btn.clicked.connect(self._start_download)

        self.cancel_btn = QPushButton("  ᗣ  CANCEL  ")
        self.cancel_btn.setFont(QFont("Courier", 13, QFont.Weight.Bold))
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {BG};
                color: {RED};
                border: 3px solid {RED};
                border-radius: 2px;
                padding: 10px 20px;
            }}
            QPushButton:hover {{
                background-color: #1a0000;
                border-color: #ff5555;
            }}
            QPushButton:disabled {{
                background-color: {BG};
                color: #444;
                border-color: #333;
            }}
        """)
        self.cancel_btn.clicked.connect(self._cancel_download)

        l.addWidget(self.download_btn)
        l.addWidget(self.cancel_btn)
        l.addStretch()
        return w

    def _progress_section(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(6)
        l.addWidget(self._maze_section_title("SCORE"))

        self.status_label = self._label("READY!", 10, color=YELLOW)
        l.addWidget(self.status_label)

        self.pac_bar = PacManBar()
        l.addWidget(self.pac_bar)

        self.pct_label = self._label("0%", 9, color=DOT_COLOR)
        self.pct_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        l.addWidget(self.pct_label)
        return w

    def _log_section(self):
        w = QWidget()
        w.setStyleSheet("background: transparent;")
        l = QVBoxLayout(w)
        l.setContentsMargins(0, 0, 0, 0)
        l.setSpacing(6)
        l.addWidget(self._maze_section_title("ARCADE LOG"))

        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setFont(QFont("Courier", 10))
        self.log_view.setStyleSheet(f"""
            QTextEdit {{
                background-color: {DARK_PANEL};
                color: {DOT_COLOR};
                border: 3px solid {MAZE};
                border-radius: 4px;
                padding: 8px;
            }}
            QScrollBar:vertical {{
                background: {BG};
                width: 10px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {MAZE};
                border-radius: 2px;
                min-height: 20px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        """)
        l.addWidget(self.log_view, stretch=1)
        return w

    # ── Slots ──────────────────────────────────────────────────────────────────
    def _choose_dir(self):
        path = QFileDialog.getExistingDirectory(self, "저장 폴더 선택", self.output_dir)
        if path:
            self.output_dir = path
            self.dir_label.setText(path)

    def _start_download(self):
        url = self.url_input.text().strip()
        if not url:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(self, "INPUT ERROR", "재생목록 URL을 입력해주세요.")
            return
        if self.is_downloading:
            return
        self.is_downloading = True
        self.cancel_flag = False
        self.download_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.pac_bar.set_value(0)
        self.pct_label.setText("0%")
        self.log_view.clear()
        threading.Thread(target=self._download_worker, args=(url,), daemon=True).start()

    def _cancel_download(self):
        self.cancel_flag = True
        self.signals.log.emit("ᗣ  GAME OVER — 취소 요청됨", "error")

    @pyqtSlot(str, str)
    def _append_log(self, msg, tag):
        colors = {
            "info":    DOT_COLOR,
            "success": CYAN,
            "error":   RED,
            "title":   YELLOW,
        }
        color = colors.get(tag, WHITE)
        # escape HTML special chars
        safe = msg.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        self.log_view.append(f'<span style="color:{color}; font-family:Courier;">{safe}</span>')
        self.log_view.moveCursor(QTextCursor.MoveOperation.End)

    @pyqtSlot(str)
    def _update_status(self, msg):
        self.status_label.setText(msg)

    @pyqtSlot(int)
    def _update_progress(self, value):
        self.pac_bar.set_value(value)
        self.pct_label.setText(f"{value}%")

    @pyqtSlot()
    def _on_done(self):
        self.is_downloading = False
        self.download_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)

    # ── Download Worker ────────────────────────────────────────────────────────
    def _download_worker(self, url):
        try:
            self.signals.status.emit("ᗧ···  재생목록 정보 로딩 중...")
            self.signals.log.emit("ᗧ  재생목록 정보를 가져오는 중입니다...", "info")

            with yt_dlp.YoutubeDL({"quiet": True, "extract_flat": True}) as ydl:
                info = ydl.extract_info(url, download=False)

            if info is None:
                self.signals.log.emit("ᗣ  URL에서 정보를 가져올 수 없습니다.", "error")
                return

            entries = info.get("entries") or [info]
            total = len(entries)
            self.signals.log.emit(f"· · ·  총 {total}개의 영상 발견  · · ·", "success")

            for idx, entry in enumerate(entries, start=1):
                if self.cancel_flag:
                    self.signals.log.emit("ᗣ  GAME OVER — 다운로드가 취소되었습니다.", "error")
                    break

                title = entry.get("title", f"영상 {idx}")
                video_url = entry.get("url") or entry.get("webpage_url") or url

                self.signals.log.emit(f"ᗧ  [{idx}/{total}]  {title}", "title")
                self.signals.status.emit(f"ᗧ···  LEVEL {idx}/{total}  —  {title}")
                self.signals.progress.emit(int((idx - 1) / total * 100))

                if FFMPEG_AVAILABLE:
                    fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
                    postprocessors = [{"key": "FFmpegVideoConvertor", "preferedformat": "mp4"}]
                    merge_fmt = "mp4"
                else:
                    fmt = "best[ext=mp4]/best"
                    postprocessors = []
                    merge_fmt = None

                ydl_opts = {
                    "format": fmt,
                    "outtmpl": os.path.join(self.output_dir, "%(title)s.%(ext)s"),
                    "quiet": True,
                    "no_warnings": True,
                    "progress_hooks": [self._make_hook(idx, total)],
                    "postprocessors": postprocessors,
                }
                if merge_fmt:
                    ydl_opts["merge_output_format"] = merge_fmt

                try:
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        ydl.download([video_url])
                    self.signals.log.emit(f"   ★ CLEAR!  {title}", "success")
                except Exception as e:
                    self.signals.log.emit(f"   ᗣ ERROR: {e}", "error")

            self.signals.progress.emit(100)
            if not self.cancel_flag:
                self.signals.log.emit(f"", "info")
                self.signals.log.emit(f"ᗧ· · · · · · · · · · ·  ALL STAGES CLEAR!  · · · · · · · · · · ·ᗤ", "success")
                self.signals.log.emit(f"저장 위치: {self.output_dir}", "info")
                self.signals.status.emit("ᗧ  ALL CLEAR!  — 다운로드 완료")
            else:
                self.signals.status.emit("ᗣ  GAME OVER")
        except Exception as e:
            self.signals.log.emit(f"ᗣ  오류 발생: {e}", "error")
            self.signals.status.emit("ᗣ  ERROR")
        finally:
            self.signals.done.emit()

    def _make_hook(self, idx, total):
        def hook(d):
            if self.cancel_flag:
                raise Exception("사용자가 취소했습니다.")
            if d["status"] == "downloading":
                downloaded = d.get("downloaded_bytes", 0)
                total_bytes = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
                if total_bytes:
                    pct = ((idx - 1) + downloaded / total_bytes) / total * 100
                    self.signals.progress.emit(int(pct))
        return hook


# ── Entry Point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
