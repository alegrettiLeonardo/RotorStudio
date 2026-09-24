from __future__ import annotations

APP_STYLESHEET = r"""
* {
    font-family: "Segoe UI", "Noto Sans", sans-serif;
    font-size: 10pt;
    color: #203245;
}
QMainWindow, QDialog, QWidget {
    background: #eef4f9;
}
QMenuBar {
    background: #f8fbfe;
    border-bottom: 1px solid #b8c9d8;
    padding: 1px 3px;
}
QMenuBar::item {
    padding: 4px 9px;
    background: transparent;
}
QMenuBar::item:selected {
    background: #dcecff;
    color: #0a4f98;
}
QMenu {
    background: #ffffff;
    border: 1px solid #aebfce;
}
QMenu::item { padding: 5px 24px 5px 24px; }
QMenu::item:selected { background: #dcecff; color: #0a4f98; }

QToolBar#MainToolbar {
    background: #f9fbfd;
    border: 0;
    border-bottom: 1px solid #aebfce;
    spacing: 2px;
    padding: 3px 5px;
}
QToolBar#MainToolbar QToolButton {
    min-width: 52px;
    min-height: 46px;
    padding: 2px 6px;
    border: 1px solid transparent;
    border-radius: 2px;
}
QToolBar#MainToolbar QToolButton:hover {
    background: #e6f1fb;
    border-color: #b2cbe1;
}
QToolBar#MainToolbar QToolButton:pressed,
QToolBar#MainToolbar QToolButton:checked {
    background: #d1e7fa;
    border-color: #77a8d3;
}
QToolBar#MainToolbar QComboBox {
    min-width: 150px;
    min-height: 26px;
    background: white;
    border: 1px solid #aebfce;
    padding: 2px 6px;
}

QDockWidget {
    background: #f4f8fc;
    border: 1px solid #9eb6cb;
}
QDockWidget::title {
    background: #d8eafd;
    color: #0b417a;
    border-bottom: 1px solid #9eb6cb;
    padding: 5px 7px;
    font-weight: 700;
    text-align: left;
}

QTreeView, QTableView, QTableWidget, QPlainTextEdit, QListView, QListWidget {
    background: white;
    alternate-background-color: #f4f8fc;
    border: 1px solid #b3c5d5;
    selection-background-color: #cde6ff;
    selection-color: #123a61;
}
QTreeView::item {
    min-height: 21px;
}
QTreeView::item:selected {
    background: #cde6ff;
    color: #123a61;
}
QHeaderView::section {
    background: #e8f2fb;
    color: #173b61;
    border: 0;
    border-right: 1px solid #c5d4e2;
    border-bottom: 1px solid #afc3d5;
    padding: 4px 5px;
    font-weight: 700;
}

QTabWidget::pane {
    border: 1px solid #aabfd1;
    background: white;
    top: -1px;
}
QTabBar::tab {
    background: #e5eff8;
    border: 1px solid #afc3d5;
    border-bottom: none;
    padding: 6px 15px;
    min-width: 78px;
}
QTabBar::tab:selected {
    background: white;
    color: #0a4f98;
    font-weight: 700;
}
QTabBar::tab:hover:!selected {
    background: #d9eaf8;
}

QGroupBox {
    background: #f9fbfd;
    border: 1px solid #b3c7d9;
    margin-top: 11px;
    padding-top: 6px;
    font-weight: 700;
    color: #0b4a86;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}

QPushButton, QToolButton {
    background: #f9fbfd;
    border: 1px solid #aebfce;
    border-radius: 2px;
    padding: 4px 8px;
}
QPushButton:hover, QToolButton:hover {
    background: #e6f2fc;
    border-color: #7fa9cf;
}
QPushButton:pressed, QToolButton:pressed {
    background: #cfe7fa;
}
QPushButton:disabled, QToolButton:disabled {
    color: #8493a0;
    background: #eef2f5;
    border-color: #c8d2da;
}
QPushButton:default {
    background: #d8ebfb;
    border: 1px solid #6e9fc9;
}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background: white;
    border: 1px solid #aebfce;
    padding: 2px 4px;
    min-height: 23px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #4f92cc;
}
QCheckBox { spacing: 5px; }

QSplitter::handle {
    background: #c8d6e2;
}
QSplitter::handle:horizontal { width: 2px; }
QSplitter::handle:vertical { height: 2px; }

QStatusBar {
    background: #edf4fa;
    border-top: 1px solid #b3c6d6;
    min-height: 20px;
}
QStatusBar::item { border: 0; }

QFrame#SectionHeader {
    background: #dceeff;
    border-bottom: 1px solid #abc1d5;
}
QLabel#SectionHeaderTitle {
    color: #0a4f98;
    font-weight: 700;
}
QToolButton[analysisCard="true"] {
    background: #f8fbfe;
    border: 1px solid #b5c9db;
    border-radius: 3px;
    padding: 5px;
    min-width: 92px;
    min-height: 74px;
    font-weight: 600;
}
QToolButton[analysisCard="true"]:hover {
    background: #e2f0fc;
    border-color: #6fa2d0;
}
QLabel[resultStatus="current"] { color: #13743b; font-weight: 700; }
QLabel[resultStatus="stale"] { color: #a45b00; font-weight: 700; }
"""
