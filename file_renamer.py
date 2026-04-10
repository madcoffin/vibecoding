import sys
import os

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

PREFIX_TO_REMOVE = "[전기기사] 단답암기신공_"


def get_creation_time(path):
    stat = os.stat(path)
    # macOS supports st_birthtime; fallback to st_mtime
    return getattr(stat, "st_birthtime", stat.st_mtime)


def rename_files(directory, log):
    if not os.path.isdir(directory):
        log(f"오류: '{directory}' 는 유효한 디렉토리가 아닙니다.")
        return

    entries = [
        e for e in os.scandir(directory) if e.is_file()
    ]

    if not entries:
        log("디렉토리에 파일이 없습니다.")
        return

    # Sort by creation date (oldest first)
    entries.sort(key=lambda e: get_creation_time(e.path))

    log(f"파일 {len(entries)}개 처리 시작...\n")
    renamed = 0
    skipped = 0

    for idx, entry in enumerate(entries, start=1):
        old_name = entry.name
        # Remove prefix if present
        new_name = old_name.replace(PREFIX_TO_REMOVE, "", 1)
        # Prepend sequential number
        new_name = f"{idx:02d}_{new_name}"

        if old_name == new_name:
            log(f"[건너뜀] {old_name}")
            skipped += 1
            continue

        old_path = entry.path
        new_path = os.path.join(directory, new_name)

        # Avoid overwriting existing file
        if os.path.exists(new_path):
            log(f"[충돌] {new_name} 이미 존재 — 건너뜀")
            skipped += 1
            continue

        os.rename(old_path, new_path)
        log(f"[완료] {old_name}\n      → {new_name}")
        renamed += 1

    log(f"\n완료: {renamed}개 변경, {skipped}개 건너뜀")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("파일명 일괄 변경기")
        self.setMinimumSize(700, 480)
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 20, 20, 20)
        root.setSpacing(12)

        # ── Directory row ────────────────────────────────────────────────────
        dir_row = QHBoxLayout()
        dir_row.setSpacing(8)

        lbl = QLabel("디렉토리:")
        lbl.setFont(QFont("Arial", 12))
        dir_row.addWidget(lbl)

        self.dir_input = QLineEdit()
        self.dir_input.setPlaceholderText("경로를 입력하거나 폴더를 선택하세요")
        self.dir_input.setFont(QFont("Arial", 12))
        dir_row.addWidget(self.dir_input)

        browse_btn = QPushButton("찾아보기")
        browse_btn.setFont(QFont("Arial", 12))
        browse_btn.setFixedWidth(90)
        browse_btn.clicked.connect(self._browse)
        dir_row.addWidget(browse_btn)

        root.addLayout(dir_row)

        # ── Info label ───────────────────────────────────────────────────────
        info = QLabel(f"제거할 문자열: \"{PREFIX_TO_REMOVE}\"  |  파일 생성일 기준 오름차순으로 번호 부여")
        info.setFont(QFont("Arial", 10))
        info.setStyleSheet("color: #666;")
        root.addWidget(info)

        # ── Run button ───────────────────────────────────────────────────────
        run_btn = QPushButton("파일명 변경 실행")
        run_btn.setFont(QFont("Arial", 13, QFont.Weight.Bold))
        run_btn.setFixedHeight(42)
        run_btn.clicked.connect(self._run)
        root.addWidget(run_btn)

        # ── Log area ─────────────────────────────────────────────────────────
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setFont(QFont("Menlo", 11))
        root.addWidget(self.log_area)

    def _browse(self):
        directory = QFileDialog.getExistingDirectory(self, "디렉토리 선택")
        if directory:
            self.dir_input.setText(directory)

    def _log(self, msg):
        self.log_area.append(msg)

    def _run(self):
        directory = self.dir_input.text().strip()
        if not directory:
            QMessageBox.warning(self, "입력 오류", "디렉토리 경로를 입력해주세요.")
            return

        self.log_area.clear()
        rename_files(directory, self._log)


def main():
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
