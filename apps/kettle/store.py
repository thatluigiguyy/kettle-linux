#!/usr/bin/env python3
"""Kettle Store: find, install, open and remix apps made with Kettle Studio."""
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (QApplication, QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QMessageBox, QPushButton, QScrollArea, QTabWidget,
                               QVBoxLayout, QWidget)

sys.path.insert(0, str(Path(__file__).resolve().parent))
import common  # noqa: E402
import ui  # noqa: E402


def load_store():
    """Search GitHub for Kettle apps, then read each one's kettle.json."""
    entries = common.search_store()
    with ThreadPoolExecutor(max_workers=8) as pool:
        metas = list(pool.map(common.fetch_meta, entries))
    for entry, meta in zip(entries, metas):
        entry["meta"] = meta
    return entries


class AppCard(QFrame):
    def __init__(self, store, icon, name, author, description, extra="", entry=None, app=None):
        super().__init__(objectName="card")
        self.store, self.entry, self.app = store, entry, app
        self.search_text = f"{name} {author} {description}".lower()

        emoji = QLabel(icon)
        emoji.setFixedWidth(64)
        emoji.setAlignment(Qt.AlignCenter)
        emoji.setStyleSheet("font-size: 38px; background: #262144; border-radius: 14px;")
        emoji.setFixedHeight(64)

        title = QLabel(f"<b style='font-size:15px'>{_esc(name)}</b>"
                       f"  <span style='color:#8f88b8'>by {_esc(author)}</span>")
        desc = QLabel(_esc(description) or "<i>No description</i>")
        desc.setWordWrap(True)
        desc.setObjectName("muted")
        meta = QLabel(extra)
        meta.setStyleSheet("color: #8f88b8; font-size: 11px;")

        text = QVBoxLayout()
        text.setSpacing(3)
        text.addWidget(title)
        text.addWidget(desc)
        text.addWidget(meta)

        self.buttons = QHBoxLayout()
        self.buttons.setSpacing(6)

        row = QHBoxLayout(self)
        row.setContentsMargins(12, 12, 12, 12)
        row.setSpacing(14)
        row.addWidget(emoji, 0, Qt.AlignTop)
        row.addLayout(text, 1)
        row.addLayout(self.buttons)
        self.refresh_buttons()

    def _button(self, text, slot, kind=None):
        b = QPushButton(text)
        if kind:
            b.setObjectName(kind)
        b.clicked.connect(slot)
        self.buttons.addWidget(b)
        return b

    def refresh_buttons(self):
        while self.buttons.count():
            w = self.buttons.takeAt(0).widget()
            if w:
                w.deleteLater()
        installed = self.app or (self.entry and common.installed_folder(self.entry).is_dir()
                                 and common.KettleApp(common.installed_folder(self.entry)))
        if installed:
            self._button("Open", lambda: common.run_app(installed.folder), "accent")
            self._button("Remix", lambda: self.store.remix(installed))
            self._button("Remove", lambda: self.store.remove(self), "danger")
        else:
            self.install_btn = self._button("Install", lambda: self.store.install(self), "accent")
        if self.entry and self.entry.get("url"):
            self._button("Code", lambda: QDesktopServices.openUrl(QUrl(self.entry["url"])))


def _esc(text):
    return (text or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Store(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Kettle Store")
        self.setWindowIcon(QIcon.fromTheme("kettle-store"))
        self.resize(980, 720)
        self.workers = []

        header = QFrame(objectName="panelHeader")
        hl = QVBoxLayout(header)
        hl.setContentsMargins(24, 18, 24, 14)
        top = QHBoxLayout()
        title = QLabel("\U0001FAD6  Kettle Store", objectName="h1")
        title.setStyleSheet("font-size: 24px; font-weight: 800; color: #ffb347;")
        self.search = QLineEdit(placeholderText="Search apps...")
        self.search.setFixedWidth(280)
        self.search.textChanged.connect(self.filter)
        refresh = QPushButton("Refresh")
        refresh.clicked.connect(self.load)
        studio = QPushButton("Make your own", objectName="accent")
        studio.clicked.connect(lambda: subprocess.Popen(
            [sys.executable, str(common.HERE / "studio.py")]))
        top.addWidget(title)
        top.addStretch()
        top.addWidget(self.search)
        top.addWidget(refresh)
        top.addWidget(studio)
        sub = QLabel("Apps made with Kettle Studio by people like you. "
                     "They're made by other people, so only install apps you trust.",
                     objectName="muted")
        sub.setWordWrap(True)
        hl.addLayout(top)
        hl.addWidget(sub)

        self.tabs = QTabWidget()
        self.discover, self.discover_list = self._page()
        self.installed, self.installed_list = self._page()
        self.tabs.addTab(self.discover, "Discover")
        self.tabs.addTab(self.installed, "Installed")
        self.tabs.currentChanged.connect(lambda i: i == 1 and self.show_installed())

        central = QWidget()
        cl = QVBoxLayout(central)
        cl.setContentsMargins(0, 0, 0, 0)
        cl.setSpacing(0)
        cl.addWidget(header)
        cl.addWidget(self.tabs, 1)
        self.setCentralWidget(central)

        self.load()
        self.show_installed()

    def _page(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.setContentsMargins(24, 16, 24, 16)
        layout.setSpacing(10)
        layout.addStretch()
        scroll.setWidget(inner)
        return scroll, layout

    def _clear(self, layout):
        while layout.count() > 1:
            w = layout.takeAt(0).widget()
            if w:
                w.deleteLater()

    def _message(self, layout, text):
        self._clear(layout)
        label = QLabel(text, objectName="muted")
        label.setAlignment(Qt.AlignCenter)
        label.setWordWrap(True)
        label.setStyleSheet("font-size: 15px; padding: 60px;")
        layout.insertWidget(0, label)

    def _run(self, fn, *args, done):
        worker = ui.Worker(fn, *args, parent=self)
        self.workers.append(worker)

        def finished(result, error):
            self.workers.remove(worker)
            done(result, error)
        worker.done.connect(finished)
        worker.start()

    # ---- discover
    def load(self):
        self._message(self.discover_list, "Finding apps...")
        self._run(load_store, done=self._loaded)

    def _loaded(self, entries, error):
        if error:
            self._message(self.discover_list, "Couldn't reach the Kettle Store. Are you online?"
                          f"\n\n({error})")
            return
        if not entries:
            self._message(self.discover_list, "No apps yet. Be the first!\n\n"
                          "Make an app in Kettle Studio and press Publish.")
            return
        self._clear(self.discover_list)
        for i, e in enumerate(entries):
            m = e.get("meta") or {}
            card = AppCard(self, m.get("icon") or common.DEFAULT_META["icon"],
                           m.get("name") or e["repo"].removeprefix(common.REPO_PREFIX),
                           m.get("author") or e["owner"],
                           m.get("description") or e["description"],
                           f"★ {e['stars']}   ·   version {m.get('version', '?')}"
                           f"   ·   github.com/{e['owner']}/{e['repo']}",
                           entry=e)
            self.discover_list.insertWidget(i, card)
        self.filter(self.search.text())

    def filter(self, text):
        text = text.lower().strip()
        for layout in (self.discover_list, self.installed_list):
            for i in range(layout.count()):
                w = layout.itemAt(i).widget()
                if isinstance(w, AppCard):
                    w.setVisible(not text or text in w.search_text)

    # ---- installed
    def show_installed(self):
        apps = common.list_installed()
        if not apps:
            self._message(self.installed_list, "You haven't installed any Kettle apps yet.")
            return
        self._clear(self.installed_list)
        for i, app in enumerate(apps):
            src = common.source_of(app) or {}
            card = AppCard(self, app.icon, app.name, app.meta.get("author") or src.get("owner", "?"),
                           app.meta.get("description", ""), f"version {app.meta.get('version', '?')}",
                           entry=src or None, app=app)
            self.installed_list.insertWidget(i, card)

    # ---- actions
    def install(self, card):
        card.install_btn.setEnabled(False)
        card.install_btn.setText("Installing...")

        def done(app, error):
            if error:
                QMessageBox.warning(self, "Couldn't install", str(error))
            card.refresh_buttons()
            self.show_installed()
        self._run(common.download_app, card.entry, done=done)

    def remove(self, card):
        app = card.app or common.KettleApp(common.installed_folder(card.entry))
        if QMessageBox.question(self, "Remove app?", f"Remove {app.icon} {app.name}?") \
                != QMessageBox.Yes:
            return
        entry = card.entry or common.source_of(app)
        if entry:
            common.uninstall_app(entry)
        card.app = None
        self.load_cards_again()

    def remix(self, app):
        copy = common.remix(app)
        subprocess.Popen([sys.executable, str(common.HERE / "studio.py"), "--open", str(copy.folder)])

    def load_cards_again(self):
        self.show_installed()
        for i in range(self.discover_list.count()):
            w = self.discover_list.itemAt(i).widget()
            if isinstance(w, AppCard):
                w.refresh_buttons()


def main():
    qt = QApplication(sys.argv)
    qt.setApplicationName("Kettle Store")
    qt.setDesktopFileName("org.kettle.store")
    ui.apply_theme(qt)
    win = Store()
    win.show()
    return qt.exec()


if __name__ == "__main__":
    sys.exit(main())
