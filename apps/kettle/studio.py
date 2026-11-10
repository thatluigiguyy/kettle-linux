#!/usr/bin/env python3
"""Kettle Studio: write Kettle apps and watch them come to life as you type."""
import argparse
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QRect, QRegularExpression, QSize, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import (QAction, QColor, QFont, QIcon, QKeySequence, QPainter,
                           QSyntaxHighlighter, QTextCharFormat, QTextCursor, QTextFormat)
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import (QApplication, QDialog, QDialogButtonBox, QFormLayout, QFrame,
                               QHBoxLayout, QLabel, QLineEdit, QListWidget, QListWidgetItem,
                               QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QSizePolicy,
                               QSpinBox, QSplitter, QTextEdit, QToolBar, QVBoxLayout, QWidget)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import ui  # noqa: E402
from templates import TEMPLATES  # noqa: E402


# ----------------------------------------------------------- editor --

class QmlHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)

        def fmt(color, bold=False, italic=False):
            f = QTextCharFormat()
            f.setForeground(QColor(color))
            if bold:
                f.setFontWeight(QFont.Bold)
            f.setFontItalic(italic)
            return f

        keywords = (r"\b(import|property|readonly|required|default|alias|signal|function|var|let|"
                    r"const|if|else|for|while|do|return|break|continue|new|typeof|in|of|switch|"
                    r"case|true|false|null|undefined|this|parent|on|as|component|enum|pragma)\b")
        self.rules = [
            (QRegularExpression(r"\b[A-Z][A-Za-z0-9_]*\b"), fmt("#7fd4ff")),
            (QRegularExpression(r"\b[a-z_][A-Za-z0-9_.]*(?=\s*:)"), fmt("#c9a7ff")),
            (QRegularExpression(keywords), fmt("#ff8fa3", bold=True)),
            (QRegularExpression(r"\b\d+(\.\d+)?\b"), fmt("#ffd27f")),
            (QRegularExpression(r'"(?:[^"\\]|\\.)*"|\'(?:[^\'\\]|\\.)*\''), fmt("#a6e3a1")),
            (QRegularExpression(r"(^|\s)//[^\n]*"), fmt("#7a7f99", italic=True)),
        ]
        self.comment = fmt("#7a7f99", italic=True)
        self.start = QRegularExpression(r"/\*")
        self.end = QRegularExpression(r"\*/")

    def highlightBlock(self, text):
        for rx, f in self.rules:
            it = rx.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), f)
        self.setCurrentBlockState(0)
        if self.previousBlockState() == 1:
            start = 0
        else:
            m = self.start.match(text)
            start = m.capturedStart() if m.hasMatch() else -1
        while start >= 0:
            m = self.end.match(text, start)
            if m.hasMatch():
                length = m.capturedEnd() - start
                self.setFormat(start, length, self.comment)
                nxt = self.start.match(text, start + length)
                start = nxt.capturedStart() if nxt.hasMatch() else -1
            else:
                self.setCurrentBlockState(1)
                self.setFormat(start, len(text) - start, self.comment)
                break


class LineNumbers(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.gutter_width(), 0)

    def paintEvent(self, event):
        self.editor.paint_gutter(event)


class CodeEditor(QPlainTextEdit):
    def __init__(self):
        super().__init__()
        self.setFont(ui.mono_font(11))
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setStyleSheet("QPlainTextEdit { background: #100e1e; color: #ece8ff; border: none;"
                           " selection-background-color: #4b3b8f; padding-left: 4px; }")
        self.error_line = None
        self.gutter = LineNumbers(self)
        self.blockCountChanged.connect(self._update_margin)
        self.updateRequest.connect(self._update_gutter)
        self.cursorPositionChanged.connect(self._highlight)
        self._update_margin()
        self._highlight()

    def gutter_width(self):
        digits = max(3, len(str(self.blockCount())))
        return 18 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_margin(self, *_):
        self.setViewportMargins(self.gutter_width(), 0, 0, 0)

    def _update_gutter(self, rect, dy):
        if dy:
            self.gutter.scroll(0, dy)
        else:
            self.gutter.update(0, rect.y(), self.gutter.width(), rect.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.gutter.setGeometry(QRect(cr.left(), cr.top(), self.gutter_width(), cr.height()))

    def paint_gutter(self, event):
        p = QPainter(self.gutter)
        p.fillRect(event.rect(), QColor("#141127"))
        block = self.firstVisibleBlock()
        n = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())
        current = self.textCursor().blockNumber()
        height = self.fontMetrics().height()
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                if self.error_line == n + 1:
                    p.setPen(QColor("#ff6b81"))
                elif n == current:
                    p.setPen(QColor(ui.ACCENT))
                else:
                    p.setPen(QColor("#57527a"))
                p.drawText(0, top, self.gutter.width() - 10, height, Qt.AlignRight, str(n + 1))
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            n += 1

    def _highlight(self):
        selections = []
        cur = QTextEdit.ExtraSelection()
        cur.format.setBackground(QColor("#1c1934"))
        cur.format.setProperty(QTextFormat.FullWidthSelection, True)
        cur.cursor = self.textCursor()
        cur.cursor.clearSelection()
        selections.append(cur)
        if self.error_line:
            block = self.document().findBlockByNumber(self.error_line - 1)
            if block.isValid():
                err = QTextEdit.ExtraSelection()
                err.format.setBackground(QColor("#3a1626"))
                err.format.setProperty(QTextFormat.FullWidthSelection, True)
                err.cursor = QTextCursor(block)
                selections.append(err)
        self.setExtraSelections(selections)
        self.gutter.update()

    def set_error_line(self, line):
        self.error_line = line
        self._highlight()

    def go_to_line(self, line):
        block = self.document().findBlockByNumber(max(0, line - 1))
        if block.isValid():
            self.setTextCursor(QTextCursor(block))
            self.centerCursor()
            self.setFocus()

    def keyPressEvent(self, event):
        cursor = self.textCursor()
        if event.key() == Qt.Key_Tab and not event.modifiers():
            self.insertPlainText("    ")
            return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            line = cursor.block().text()[:cursor.positionInBlock()]
            indent = line[:len(line) - len(line.lstrip())]
            if line.rstrip().endswith(("{", "[")):
                indent += "    "
            super().keyPressEvent(event)
            self.insertPlainText(indent)
            return
        if event.text() in ("}", "]"):
            line = cursor.block().text()[:cursor.positionInBlock()]
            if line.strip() == "" and line.endswith("    "):
                for _ in range(4):
                    cursor.deletePreviousChar()
        super().keyPressEvent(event)


# ---------------------------------------------------------- preview --

class Preview(QWidget):
    error_line = Signal(object)

    def __init__(self):
        super().__init__()
        self.path = None

        header = QFrame(objectName="panelHeader")
        title = QLabel("LIVE PREVIEW", objectName="section")
        self.state = QLabel("", objectName="muted")
        reload_btn = QPushButton("Reload")
        reload_btn.setToolTip("Restart the app in the preview")
        reload_btn.clicked.connect(self.reload)
        h = QHBoxLayout(header)
        h.setContentsMargins(4, 0, 8, 0)
        h.addWidget(title)
        h.addWidget(self.state)
        h.addStretch()
        h.addWidget(reload_btn)

        self.view = QQuickWidget()
        self.view.setResizeMode(QQuickWidget.SizeRootObjectToView)
        self.view.setClearColor(QColor("#0c0a18"))
        self.view.engine().warnings.connect(self._warnings)

        self.error = QLabel(objectName="error")
        self.error.setWordWrap(True)
        self.error.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.error.hide()
        self.error.linkActivated.connect(lambda link: self.error_line.emit(int(link)))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(header)
        layout.addWidget(self.view, 1)
        err_box = QVBoxLayout()
        err_box.setContentsMargins(8, 8, 8, 8)
        err_box.addWidget(self.error)
        layout.addLayout(err_box)

    def load(self, path):
        self.path = Path(path)
        self.reload()

    def reload(self):
        if not self.path:
            return
        self.view.setSource(QUrl())
        self.view.engine().clearComponentCache()
        self.view.setSource(QUrl.fromLocalFile(str(self.path)))
        if self.view.status() == QQuickWidget.Error:
            self._show_errors(self.view.errors())
        else:
            self.error.hide()
            self.state.setText("running")
            self.state.setObjectName("ok")
            self.state.setStyleSheet("color: #8ee6a8;")
            self.error_line.emit(None)

    def _warnings(self, warnings):
        relevant = [w for w in warnings if self.path and w.url().toLocalFile() == str(self.path)]
        if relevant and self.view.status() != QQuickWidget.Error:
            self._show_errors(relevant, warning=True)

    def _show_errors(self, errors, warning=False):
        lines = []
        first = None
        for e in errors[:4]:
            desc = e.description().replace("<", "&lt;")
            if "root objects" in desc and "QQuickItem" in desc:
                desc = "The outside of your app must be an Item or Rectangle, not a Window."
            if e.line() > 0:
                first = first or e.line()
                lines.append(f'<a href="{e.line()}" style="color:#ffb347">Line {e.line()}</a>: {desc}')
            else:
                lines.append(desc)
        kind = "Heads up" if warning else "Oops, something's not right"
        self.error.setText(f"<b>{kind}</b><br>" + "<br>".join(lines))
        self.error.show()
        self.state.setText("has a warning" if warning else "stopped")
        self.state.setStyleSheet("color: #ffd27f;" if warning else "color: #ff6b81;")
        self.error_line.emit(first)


# ---------------------------------------------------------- dialogs --

class NewAppDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Kettle App")
        self.resize(460, 480)
        self.name = QLineEdit(placeholderText="My Awesome App")
        self.list = QListWidget()
        self.list.setIconSize(QSize(28, 28))
        for key, tpl in TEMPLATES.items():
            item = QListWidgetItem(f"{tpl['icon']}   {tpl['title']}\n      {tpl['description']}")
            item.setData(Qt.UserRole, key)
            item.setSizeHint(QSize(0, 54))
            self.list.addItem(item)
        self.list.setCurrentRow(0)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Ok).setText("Create app")
        buttons.button(QDialogButtonBox.Ok).setObjectName("accent")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        self.list.itemDoubleClicked.connect(lambda *_: self.accept())

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Make a new app", objectName="h1"))
        layout.addWidget(QLabel("Name", objectName="muted"))
        layout.addWidget(self.name)
        layout.addWidget(QLabel("Start from", objectName="muted"))
        layout.addWidget(self.list, 1)
        layout.addWidget(buttons)

    def result_values(self):
        key = self.list.currentItem().data(Qt.UserRole)
        name = self.name.text().strip() or TEMPLATES[key]["title"]
        return name, key


class AppInfoDialog(QDialog):
    def __init__(self, app, parent=None):
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("App info")
        m = app.meta
        self.name = QLineEdit(m.get("name", ""))
        self.icon = QLineEdit(m.get("icon", ""))
        self.icon.setMaxLength(4)
        self.icon.setToolTip("One emoji, like \U0001FAD6 \U0001F3AE \U0001F680 \U0001F431. Press Win + . to pick one.")
        self.desc = QLineEdit(m.get("description", ""))
        self.version = QLineEdit(str(m.get("version", "1.0")))
        self.author = QLineEdit(m.get("author", ""))
        self.width_ = QSpinBox(minimum=160, maximum=3840, value=int(m.get("width", 480)))
        self.height_ = QSpinBox(minimum=120, maximum=2160, value=int(m.get("height", 360)))
        size = QHBoxLayout()
        size.addWidget(self.width_)
        size.addWidget(QLabel("x"))
        size.addWidget(self.height_)
        form = QFormLayout()
        form.addRow("Name", self.name)
        form.addRow("Icon (emoji)", self.icon)
        form.addRow("Description", self.desc)
        form.addRow("Version", self.version)
        form.addRow("Made by", self.author)
        form.addRow("Window size", size)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.button(QDialogButtonBox.Save).setObjectName("accent")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"{app.icon}  {app.name}", objectName="h1"))
        layout.addLayout(form)
        layout.addWidget(buttons)

    def apply(self):
        self.app.meta.update(
            name=self.name.text().strip() or self.app.name,
            icon=self.icon.text().strip() or common.DEFAULT_META["icon"],
            description=self.desc.text().strip(),
            version=self.version.text().strip() or "1.0",
            author=self.author.text().strip(),
            width=self.width_.value(), height=self.height_.value(),
        )
        self.app.save_meta()


class PublishDialog(QDialog):
    def __init__(self, app, user, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Publishing to the Kettle Store")
        self.resize(560, 380)
        self.title = QLabel(f"Publishing {app.icon} {app.name}...", objectName="h1")
        self.log = QPlainTextEdit(objectName="log", readOnly=True)
        self.result = QLabel(objectName="muted")
        self.result.setOpenExternalLinks(True)
        self.result.setWordWrap(True)
        self.close_btn = QPushButton("Close", enabled=False)
        self.close_btn.clicked.connect(self.accept)
        layout = QVBoxLayout(self)
        layout.addWidget(self.title)
        layout.addWidget(self.log, 1)
        layout.addWidget(self.result)
        layout.addWidget(self.close_btn, 0, Qt.AlignRight)
        self.worker = ui.Worker(common.publish, app, user, with_log=True, parent=self)
        self.worker.log.connect(self.log.appendPlainText)
        self.worker.done.connect(self._done)
        self.worker.start()

    def _done(self, url, error):
        self.close_btn.setEnabled(True)
        if error:
            self.title.setText("Publishing didn't work")
            self.result.setText(f"<span style='color:#ff8fa3'>{error}</span>")
        else:
            self.title.setText("Published! \U0001F389")
            self.result.setText(f"Your app is live at <a style='color:#ffb347' href='{url}'>{url}</a>"
                                "<br>It shows up in the Kettle Store within a few minutes.")


# ------------------------------------------------------------- main --

class Studio(QMainWindow):
    def __init__(self, open_folder=None):
        super().__init__()
        self.app = None
        self.loading = False
        self.setWindowTitle("Kettle Studio")
        self.setWindowIcon(QIcon.fromTheme("kettle-studio"))
        self.resize(1360, 820)

        self._build_toolbar()

        # left: my apps
        side = QWidget()
        side.setStyleSheet("background: #141127;")
        self.apps = QListWidget()
        self.apps.currentItemChanged.connect(self._app_selected)
        new_btn = QPushButton("+  New app", objectName="accent")
        new_btn.clicked.connect(self.new_app)
        sl = QVBoxLayout(side)
        sl.setContentsMargins(0, 0, 0, 10)
        sl.addWidget(QLabel("MY APPS", objectName="section"))
        sl.addWidget(self.apps, 1)
        nb = QHBoxLayout()
        nb.setContentsMargins(10, 0, 10, 0)
        nb.addWidget(new_btn)
        sl.addLayout(nb)

        # middle: code
        self.editor = CodeEditor()
        self.highlighter = QmlHighlighter(self.editor.document())
        self.editor.textChanged.connect(self._changed)
        self.editor.cursorPositionChanged.connect(self._cursor_moved)
        code = QWidget()
        cl = QVBoxLayout(code)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        code_header = QFrame(objectName="panelHeader")
        ch = QHBoxLayout(code_header)
        ch.setContentsMargins(4, 0, 8, 0)
        self.file_label = QLabel("MAIN.QML", objectName="section")
        ch.addWidget(self.file_label)
        ch.addStretch()
        cl.addWidget(code_header)
        cl.addWidget(self.editor, 1)

        # right: live preview
        self.preview = Preview()
        self.preview.error_line.connect(self._error_line)

        split = QSplitter()
        split.addWidget(side)
        split.addWidget(code)
        split.addWidget(self.preview)
        split.setSizes([230, 620, 510])
        split.setChildrenCollapsible(False)
        self.setCentralWidget(split)

        self.saved = QLabel("")
        self.position = QLabel("")
        self.statusBar().addWidget(self.saved)
        self.statusBar().addPermanentWidget(self.position)

        self.save_timer = QTimer(self, singleShot=True, interval=600)
        self.save_timer.timeout.connect(self.save_and_preview)

        self.refresh_apps()
        if open_folder:
            self.open_app(common.KettleApp(open_folder))
        elif self.apps.count() == 0:
            self.open_app(common.KettleApp.create("Hello Kettle", "hello"))
        else:
            self.apps.setCurrentRow(0)

    def _build_toolbar(self):
        bar = QToolBar(movable=False)
        bar.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.addToolBar(bar)

        def action(text, slot, shortcut=None, tip=None, accent=False):
            act = QAction(text, self)
            act.triggered.connect(slot)
            if shortcut:
                act.setShortcut(QKeySequence(shortcut))
            act.setToolTip(tip or text)
            bar.addAction(act)
            if accent:
                bar.widgetForAction(act).setObjectName("accent")
            return act

        brand = QLabel("  \U0001FAD6  Kettle Studio  ")
        brand.setStyleSheet("font-size: 15px; font-weight: 700; color: #ffb347;")
        bar.addWidget(brand)
        action("New App", self.new_app, "Ctrl+N", "Start a new app (Ctrl+N)")
        action("App Info", self.edit_info, "Ctrl+I", "Name, icon and description (Ctrl+I)")
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        bar.addWidget(spacer)
        action("Add to App Menu", self.add_to_menu, None, "Put this app in the Kettle app menu")
        action("Kettle Store", self.open_store, None, "Browse apps other people made")
        action("Publish", self.publish, None, "Share this app on the Kettle Store")
        action("▶  Run", self.run_app, "F5", "Open the app in its own window (F5)", accent=True)

    # ---- apps list
    def refresh_apps(self, select=None):
        self.apps.blockSignals(True)
        self.apps.clear()
        for app in common.list_projects():
            item = QListWidgetItem(f"{app.icon}  {app.name}")
            item.setData(Qt.UserRole, str(app.folder))
            item.setToolTip(app.meta.get("description") or app.name)
            self.apps.addItem(item)
            if select and Path(select) == app.folder:
                self.apps.setCurrentItem(item)
        self.apps.blockSignals(False)

    def _app_selected(self, item, _prev=None):
        if item:
            self.open_app(common.KettleApp(item.data(Qt.UserRole)))

    def open_app(self, app):
        if self.app and self.save_timer.isActive():
            self.save_and_preview()
        self.app = app
        self.loading = True
        self.editor.setPlainText(app.read_code())
        self.loading = False
        self.editor.set_error_line(None)
        self.setWindowTitle(f"{app.name} - Kettle Studio")
        self.file_label.setText(f"{app.name.upper()}  /  MAIN.QML")
        self.saved.setText("All changes saved")
        self.refresh_apps(select=app.folder)
        self.preview.load(app.main)

    # ---- editing
    def _changed(self):
        if self.loading or not self.app:
            return
        self.saved.setText("Typing...")
        self.save_timer.start()

    def save_and_preview(self):
        self.save_timer.stop()
        if not self.app:
            return
        self.app.write_code(self.editor.toPlainText())
        self.saved.setText("All changes saved")
        self.preview.reload()

    def _cursor_moved(self):
        c = self.editor.textCursor()
        self.position.setText(f"Line {c.blockNumber() + 1}, Column {c.positionInBlock() + 1}")

    def _error_line(self, line):
        self.editor.set_error_line(line)
        if line and self.sender() is self.preview and not self.editor.hasFocus():
            self.editor.go_to_line(line)

    # ---- toolbar actions
    def new_app(self):
        dlg = NewAppDialog(self)
        if dlg.exec() == QDialog.Accepted:
            name, key = dlg.result_values()
            self.open_app(common.KettleApp.create(name, key))

    def edit_info(self):
        if not self.app:
            return
        dlg = AppInfoDialog(self.app, self)
        if dlg.exec() == QDialog.Accepted:
            dlg.apply()
            self.open_app(common.KettleApp(self.app.folder))

    def run_app(self):
        if self.app:
            self.save_and_preview()
            common.run_app(self.app.folder)

    def add_to_menu(self):
        if not self.app:
            return
        self.save_and_preview()
        common.install_launcher(self.app)
        QMessageBox.information(self, "Added",
                                f"{self.app.icon} {self.app.name} is now in your app menu.")

    def open_store(self):
        subprocess.Popen([sys.executable, str(common.HERE / "store.py")])

    def publish(self):
        if not self.app:
            return
        self.save_and_preview()
        if self.preview.view.status() == QQuickWidget.Error:
            QMessageBox.warning(self, "Fix it first",
                                "Your app has a mistake in it. Fix the red error, then publish.")
            return
        if not common.gh_available():
            QMessageBox.warning(self, "GitHub tools missing",
                                "Publishing needs the 'gh' and 'git' commands.")
            return
        user = common.gh_user()
        if not user:
            box = QMessageBox(self)
            box.setWindowTitle("Sign in to GitHub")
            box.setText("Kettle apps are shared through GitHub.\n\n"
                        "Sign in once: a terminal opens with a short code. Press Enter, "
                        "type the code on the GitHub page and click Authorize. "
                        "Then press Publish again.")
            sign_in = box.addButton("Sign in", QMessageBox.AcceptRole)
            box.addButton(QMessageBox.Cancel)
            box.exec()
            if box.clickedButton() is sign_in:
                if not common.open_terminal(["gh", "auth", "login", "--web", "--hostname",
                                             "github.com", "--git-protocol", "https"]):
                    QMessageBox.warning(self, "No terminal",
                                        "Run this in a terminal:\n gh auth login --web")
            return
        repo = common.repo_name(self.app)
        answer = QMessageBox.question(
            self, "Publish to the Kettle Store?",
            f"{self.app.icon} {self.app.name} will be uploaded to\n\n"
            f"    github.com/{user}/{repo}\n\n"
            "Anyone will be able to see its code, download it and remix it.\n"
            "Publish it?")
        if answer == QMessageBox.Yes:
            PublishDialog(self.app, user, self).exec()

    def closeEvent(self, event):
        if self.save_timer.isActive():
            self.save_and_preview()
        super().closeEvent(event)


def main():
    parser = argparse.ArgumentParser(prog="kettle-studio")
    parser.add_argument("--open", help="app folder to open")
    args, _ = parser.parse_known_args()
    qt = QApplication(sys.argv)
    qt.setApplicationName("Kettle Studio")
    qt.setDesktopFileName("org.kettle.studio")
    ui.apply_theme(qt)
    win = Studio(args.open)
    win.show()
    return qt.exec()


if __name__ == "__main__":
    sys.exit(main())
