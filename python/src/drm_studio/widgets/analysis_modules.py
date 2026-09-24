from __future__ import annotations

from PySide6.QtCore import QSize, Signal, Qt
from PySide6.QtWidgets import QHBoxLayout, QGroupBox, QToolButton

from drm_studio.resources import studio_icon


class AnalysisModulesBar(QGroupBox):
    modalRequested = Signal()
    campbellRequested = Signal()
    criticalRequested = Signal()
    synchronousRequested = Signal()
    frequencyRequested = Signal()
    foundationRequested = Signal()
    runupRequested = Signal()
    coaxialRequested = Signal()
    asymmetricRequested = Signal()
    bearingRequested = Signal()

    def __init__(self, parent=None):
        super().__init__("Analysis Modules", parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 10, 8, 7)
        layout.setSpacing(8)

        specs = [
            ("Modal /\nChar. Roots", "modal", True, self.modalRequested),
            ("Campbell\nDiagram", "campbell", True, self.campbellRequested),
            ("Critical\nSpeeds", "critical", True, self.criticalRequested),
            ("Synchronous\nResponse", "synchronous", True, self.synchronousRequested),
            ("Frequency\nResponse", "frequency", True, self.frequencyRequested),
            ("Foundation\nExcitation", "foundation", True, self.foundationRequested),
            ("Run-up /\nRun-down", "runup", True, self.runupRequested),
            ("Coaxial\nRotor", "coaxial", True, self.coaxialRequested),
            ("Asymmetric\nRotor", "asymmetric", True, self.asymmetricRequested),
            ("Bearing /\nSeal", "bearing", True, self.bearingRequested),
        ]

        self.buttons = {}
        for text, icon_name, enabled, signal in specs:
            button = QToolButton()
            button.setProperty("analysisCard", True)
            button.setText(text)
            button.setIcon(studio_icon(icon_name))
            button.setIconSize(QSize(30, 30))
            button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
            button.setEnabled(enabled)
            button.clicked.connect(signal)
            layout.addWidget(button, 1)
            self.buttons[text] = button
