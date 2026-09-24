from __future__ import annotations

from datetime import datetime

from PySide6.QtWidgets import (
    QDockWidget, QTabWidget, QWidget, QVBoxLayout, QPlainTextEdit, QListWidget
)


class MessagesDock(QDockWidget):
    def __init__(self, session, parent=None):
        super().__init__("Messages & Results", parent)
        self.setObjectName("MessagesResultsDock")
        tabs = QTabWidget(self)
        self.console = QPlainTextEdit()
        self.console.setReadOnly(True)
        self.checks = QListWidget()
        self.results = QListWidget()
        self.notes = QPlainTextEdit()
        tabs.addTab(self.console, "Console")
        tabs.addTab(self.checks, "Checks (0)")
        tabs.addTab(self.results, "Results")
        tabs.addTab(self.notes, "Notes")
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(tabs)
        self.setWidget(host)
        self.tabs = tabs
        session.logMessage.connect(self.append_log)
        session.resultsChanged.connect(lambda: self.refresh_results(session))
        self.append_log("INFO", "Rotor Dynamics Studio — Stage 2")

    def append_log(self, level: str, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.console.appendPlainText(f"[{stamp}] [{level}] {message}")

    def set_checks(self, entries: list[str]) -> None:
        self.checks.clear()
        self.checks.addItems(entries)
        self.tabs.setTabText(1, f"Checks ({len(entries)})")

    def refresh_results(self, session) -> None:
        self.results.clear()
        for record in session.results.values():
            self.results.addItem(record.display_name)
