"""Look and feel shared by Kettle Studio and the Kettle Store."""
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QColor, QFont, QFontDatabase, QPalette

ACCENT = "#ffb347"

STYLE = """
QMainWindow, QDialog { background: #17142b; }
QToolBar { background: #1d1938; border: none; padding: 6px 8px; spacing: 4px; }
QToolBar QToolButton { color: #ece8ff; padding: 6px 12px; border-radius: 8px; font-weight: 600; }
QToolBar QToolButton:hover { background: #2e2858; }
QToolBar QToolButton:pressed { background: #3a3370; }
QToolBar QToolButton#accent { background: #ffb347; color: #1b1030; }
QToolBar QToolButton#accent:hover { background: #ffc46e; }
QPushButton { background: #2a2450; border: 1px solid #3a3370; border-radius: 8px;
              padding: 7px 14px; color: #ece8ff; }
QPushButton:hover { background: #352e63; }
QPushButton:disabled { color: #6b6688; background: #211c3d; }
QPushButton#accent { background: #ffb347; color: #1b1030; border: none; font-weight: 600; }
QPushButton#accent:hover { background: #ffc46e; }
QPushButton#accent:disabled { background: #4a3f2a; color: #8f8466; }
QPushButton#danger:hover { background: #5a2333; border-color: #a33b55; }
QListWidget { background: #141127; border: none; outline: 0; }
QListWidget::item { padding: 8px; border-radius: 8px; margin: 2px 6px; color: #d8d3f2; }
QListWidget::item:selected { background: #2e2858; color: #ffffff; }
QListWidget::item:hover:!selected { background: #221d40; }
QLineEdit, QSpinBox { background: #100e1e; border: 1px solid #3a3370; border-radius: 6px;
                      padding: 6px; color: #ece8ff; }
QLineEdit:focus, QSpinBox:focus { border-color: #ffb347; }
QPlainTextEdit#log { background: #100e1e; border: 1px solid #3a3370; border-radius: 6px;
                     color: #d8d3f2; font-family: "JetBrains Mono", monospace; }
QSplitter::handle { background: #0c0a18; }
QStatusBar { background: #1d1938; color: #a9a3c9; }
QStatusBar QLabel { color: #a9a3c9; padding: 0 8px; }
QLabel#h1 { font-size: 22px; font-weight: 700; color: #ffffff; }
QLabel#muted { color: #a9a3c9; }
QLabel#section { color: #8f88b8; font-size: 11px; font-weight: 700; padding: 12px 12px 4px; }
QLabel#error { background: #3a1626; color: #ffd0d8; border: 1px solid #7a2a40;
               border-radius: 8px; padding: 8px 10px; }
QLabel#ok { color: #8ee6a8; }
QFrame#panelHeader { background: #1d1938; }
QFrame#card { background: #1d1938; border: 1px solid #2c2656; border-radius: 12px; }
QTabWidget::pane { border: none; }
QTabBar::tab { background: transparent; color: #a9a3c9; padding: 8px 18px; font-weight: 600; }
QTabBar::tab:selected { color: #ffb347; border-bottom: 2px solid #ffb347; }
QScrollArea { border: none; background: transparent; }
QToolTip { background: #262144; color: #ffffff; border: 1px solid #3a3370; padding: 4px; }
"""


def set_quick_style():
    """Buttons inside Kettle apps: Plasma's own style on Kettle, Fusion elsewhere."""
    import os
    from PySide6.QtQuickControls2 import QQuickStyle
    if not os.environ.get("QT_QUICK_CONTROLS_STYLE"):
        QQuickStyle.setStyle("Fusion")


def apply_theme(app):
    """Kettle's own dark look, the same on Kettle Linux and anywhere else."""
    set_quick_style()
    app.setStyle("Fusion")
    pal = QPalette()
    colors = {
        QPalette.Window: "#17142b", QPalette.WindowText: "#ece8ff",
        QPalette.Base: "#100e1e", QPalette.AlternateBase: "#1d1938",
        QPalette.Text: "#ece8ff", QPalette.Button: "#262144",
        QPalette.ButtonText: "#ece8ff", QPalette.Highlight: ACCENT,
        QPalette.HighlightedText: "#1b1030", QPalette.ToolTipBase: "#262144",
        QPalette.ToolTipText: "#ffffff", QPalette.PlaceholderText: "#7a7499",
        QPalette.Link: ACCENT, QPalette.BrightText: "#ffffff",
    }
    for role, color in colors.items():
        pal.setColor(role, QColor(color))
    for role in (QPalette.Text, QPalette.WindowText, QPalette.ButtonText):
        pal.setColor(QPalette.Disabled, role, QColor("#6b6688"))
    app.setPalette(pal)
    if "Inter" in QFontDatabase.families():
        app.setFont(QFont("Inter", 10))
    app.setStyleSheet(STYLE)


def mono_font(size=11):
    for family in ("JetBrains Mono", "Cascadia Mono", "Consolas"):
        if family in QFontDatabase.families():
            font = QFont(family, size)
            break
    else:
        font = QFontDatabase.systemFont(QFontDatabase.FixedFont)
        font.setPointSize(size)
    font.setStyleHint(QFont.Monospace)
    return font


class Worker(QThread):
    """Runs slow work (internet, GitHub) without freezing the window."""
    log = Signal(str)
    done = Signal(object, object)  # (result, error message or None)

    def __init__(self, fn, *args, with_log=False, parent=None):
        super().__init__(parent)
        self.fn, self.args, self.with_log = fn, args, with_log

    def run(self):
        try:
            if self.with_log:
                result = self.fn(*self.args, self.log.emit)
            else:
                result = self.fn(*self.args)
            self.done.emit(result, None)
        except Exception as exc:  # shown to the user, never crashes the app
            self.done.emit(None, str(exc) or exc.__class__.__name__)
