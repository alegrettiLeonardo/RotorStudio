from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QPushButton, QGroupBox


class AnalysisModulesBar(QGroupBox):
    modalRequested = Signal()
    campbellRequested = Signal()
    criticalRequested = Signal()

    def __init__(self, parent=None):
        super().__init__("Analysis Modules", parent)
        layout = QHBoxLayout(self)
        labels = [
            ("Modal /\nChar. Roots", True),
            ("Campbell\nDiagram", True),
            ("Critical\nSpeeds", True),
            ("Synchronous\nResponse", False),
            ("Frequency\nResponse", False),
            ("Foundation\nExcitation", False),
            ("Run-up /\nRun-down", False),
            ("Coaxial\nRotor", False),
            ("Bearing\nPerformance", False),
        ]
        self.buttons = {}
        for text, enabled in labels:
            button = QPushButton(text)
            button.setMinimumHeight(62)
            button.setEnabled(enabled)
            if not enabled:
                button.setToolTip(
                    "This Stage 2 view is not integrated yet. No unavailable physics is simulated."
                )
            layout.addWidget(button, 1)
            self.buttons[text] = button
        self.buttons["Modal /\nChar. Roots"].clicked.connect(self.modalRequested)
        self.buttons["Campbell\nDiagram"].clicked.connect(self.campbellRequested)
        self.buttons["Critical\nSpeeds"].clicked.connect(self.criticalRequested)
