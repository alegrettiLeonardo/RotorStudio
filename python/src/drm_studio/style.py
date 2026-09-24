from __future__ import annotations

APP_STYLESHEET = r"""
QMainWindow, QDialog { background: #f4f8fc; }
QMenuBar { background: #f5f8fb; border-bottom: 1px solid #b6c7d8; }
QToolBar {
    background: #f8fbfe;
    border-bottom: 1px solid #afc3d7;
    spacing: 4px;
    padding: 3px;
}
QToolButton { padding: 4px 7px; }
QDockWidget::title {
    background: #dceeff;
    color: #0b3f78;
    border: 1px solid #9ebbd6;
    padding: 4px;
    font-weight: 600;
}
QTreeView, QTableView, QPlainTextEdit, QListView, QListWidget {
    background: white;
    alternate-background-color: #f5f9fd;
    border: 1px solid #b9c9d8;
}
QHeaderView::section {
    background: #eaf3fb;
    color: #173b61;
    border: 0;
    border-right: 1px solid #c7d5e2;
    border-bottom: 1px solid #b6c8d9;
    padding: 4px;
    font-weight: 600;
}
QTabWidget::pane { border: 1px solid #afc4d8; background: white; }
QTabBar::tab {
    background: #e7f1fa;
    border: 1px solid #b5c8da;
    border-bottom: none;
    padding: 5px 14px;
}
QTabBar::tab:selected { background: white; color: #0a4f98; font-weight: 600; }
QPushButton { padding: 5px 10px; }
QPushButton:default { background: #dbeeff; border: 1px solid #7fa9d2; }
QStatusBar { background: #eef5fb; border-top: 1px solid #b5c7d7; }
"""
