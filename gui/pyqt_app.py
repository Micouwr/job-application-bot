# gui/pyqt_app.py
"""
Minimal PyQt6 GUI that uses JobApplicationBot for interactions.

Run:
    python -m gui.py
or
    python gui/pyqt_app.py

Notes:
- Long-running operations are executed in a QThread to prevent blocking the UI.
- This is a starting point — we'll iterate on look & feel after the refactor.
"""
import sys
import logging
from typing import Optional, Dict
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTextEdit,
    QPushButton,
    QLabel,
    QListWidget,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

from app import JobApplicationBot

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WorkerThread(QThread):
    finished_signal = pyqtSignal(object, object, object)  # action, result, error (None if ok)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.func(*self.args, **self.kwargs)
            self.finished_signal.emit(self.func.__name__, result, None)
        except Exception as exc:
            logger.exception("Worker error")
            self.finished_signal.emit(self.func.__name__, None, exc)


class JobAppWindow(QWidget):
    """
    A simple GUI with:
    - Job description input
    - Resume input (text or load file)
    - Buttons to analyze / tailor / apply
    - Output area
    """

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Job Application Bot (PyQt6)")
        self.resize(1000, 700)

        self.bot = JobApplicationBot()  # uses default DB and APIClient placeholders

        # Layouts
        main_layout = QVBoxLayout()
        top_layout = QHBoxLayout()
        left_col = QVBoxLayout()
        right_col = QVBoxLayout()

        # Job description area
        self.job_label = QLabel("Job Description")
        self.job_text = QTextEdit()
        self.job_text.setPlaceholderText("Paste job description here...")

        left_col.addWidget(self.job_label)
        left_col.addWidget(self.job_text)

        # Resume area
        self.resume_label = QLabel("Resume (single)")
        self.resume_text = QTextEdit()
        self.resume_text.setPlaceholderText("Paste resume text here or load from file...")
        self.load_button = QPushButton("Load Resume From File")
        self.load_button.clicked.connect(self.load_resume)

        left_col.addWidget(self.resume_label)
        left_col.addWidget(self.resume_text)
        left_col.addWidget(self.load_button)

        # Controls
        self.analyze_button = QPushButton("Analyze (match)")
        self.tailor_button = QPushButton("Tailor Resume")
        self.apply_button = QPushButton("Apply (simulate)")
        self.history_button = QPushButton("Show History")

        self.analyze_button.clicked.connect(self.on_analyze)
        self.tailor_button.clicked.connect(self.on_tailor)
        self.apply_button.clicked.connect(self.on_apply)
        self.history_button.clicked.connect(self.on_show_history)

        right_col.addWidget(self.analyze_button)
        right_col.addWidget(self.tailor_button)
        right_col.addWidget(self.apply_button)
        right_col.addWidget(self.history_button)

        # Output area
        self.output_label = QLabel("Output")
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(False)

        right_col.addWidget(self.output_label)
        right_col.addWidget(self.output_text)

        top_layout.addLayout(left_col, 3)
        top_layout.addLayout(right_col, 2)

        main_layout.addLayout(top_layout)
        self.setLayout(main_layout)

        # keep a simple in-memory mapping for multiple resumes if you want to extend
        self.resumes: Dict[str, str] = {}

    def load_resume(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open Resume", "", "Text Files (*.txt);;All Files (*)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf8") as fh:
                txt = fh.read()
            self.resume_text.setPlainText(txt)
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to open file: {exc}")

    def _start_worker(self, func, *args, **kwargs):
        self.set_ui_enabled(False)
        worker = WorkerThread(func, *args, **kwargs)
        worker.finished_signal.connect(self._on_worker_done)
        worker.start()

    def _on_worker_done(self, action, result, error):
        self.set_ui_enabled(True)
        if error is not None:
            QMessageBox.critical(self, "Error", f"Operation {action} failed: {error}")
            return
        # dispatch on action name (func.__name__)
        if action == "top_matches" or action == "analyze_job":
            self.output_text.setPlainText(str(result))
        elif action == "tailor_resume":
            self.output_text.setPlainText(result)
        elif action == "apply_to_job":
            self.output_text.setPlainText(str(result))
        else:
            self.output_text.setPlainText(f"{action}: {result}")

    def set_ui_enabled(self, enabled: bool):
        for w in [self.analyze_button, self.tailor_button, self.apply_button, self.load_button, self.history_button]:
            w.setEnabled(enabled)

    def on_analyze(self):
        job = self.job_text.toPlainText().strip()
        resume = self.resume_text.toPlainText().strip()
        if not job:
            QMessageBox.warning(self, "Input needed", "Please paste a job description.")
            return
        if not resume:
            QMessageBox.warning(self, "Input needed", "Please paste or load a resume.")
            return
        resumes = {"resume1": resume}
        # call analyze_job in background
        self._start_worker(self.bot.analyze_job, job, resumes)

    def on_tailor(self):
        job = self.job_text.toPlainText().strip()
        resume = self.resume_text.toPlainText().strip()
        if not job or not resume:
            QMessageBox.warning(self, "Input needed", "Job description and resume are required.")
            return
        self._start_worker(self.bot.tailor_resume, resume, job)

    def on_apply(self):
        job = self.job_text.toPlainText().strip()
        resume = self.resume_text.toPlainText().strip()
        if not job or not resume:
            QMessageBox.warning(self, "Input needed", "Job description and resume are required.")
            return
        self._start_worker(self.bot.apply_to_job, resume, job, None)

    def on_show_history(self):
        history = self.bot.get_history(50)
        pretty = "\n\n".join([f"id={h['id']} action={h['action']} ts={h['timestamp']}\ninput={h['input_text']}\nresult={h['result_text']}" for h in history])
        self.output_text.setPlainText(pretty)


def main():
    app = QApplication(sys.argv)
    win = JobAppWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()