#!/usr/bin/env python3
"""kettle-run: open a Kettle app (a folder with main.qml) in its own window."""
import sys
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QIcon
from PySide6.QtQuick import QQuickView
from PySide6.QtWidgets import QApplication, QMessageBox

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ui  # noqa: E402
from common import KettleApp  # noqa: E402


def main():
    if len(sys.argv) < 2:
        print("usage: kettle-run <app folder>", file=sys.stderr)
        return 2
    folder = Path(sys.argv[1]).expanduser().resolve()
    app_info = KettleApp(folder)

    ui.set_quick_style()
    qt = QApplication(sys.argv)
    qt.setApplicationName(app_info.name)
    qt.setWindowIcon(QIcon.fromTheme("kettle-app"))

    if not app_info.main.is_file():
        QMessageBox.critical(None, "Kettle", f"There is no main.qml in\n{folder}")
        return 1

    view = QQuickView()
    view.setTitle(app_info.name)
    view.setResizeMode(QQuickView.SizeRootObjectToView)
    view.setSource(QUrl.fromLocalFile(str(app_info.main)))
    if view.status() == QQuickView.Error:
        errors = "\n".join(e.toString() for e in view.errors())
        QMessageBox.critical(None, app_info.name,
                             f"{app_info.name} has a mistake in its code:\n\n{errors}")
        return 1

    view.resize(int(app_info.meta.get("width", 480)), int(app_info.meta.get("height", 360)))
    view.show()
    return qt.exec()


if __name__ == "__main__":
    sys.exit(main())
