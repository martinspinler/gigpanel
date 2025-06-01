from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton

from ..app import Application
from ..song import PlaylistItem
from ..playlist import PlaylistEventListener
from . import DocumentWidget


class BookmarksWidget(PlaylistEventListener, QWidget):
    def __init__(self, doc: DocumentWidget, app: Application) -> None:
        QWidget.__init__(self)

        layout = QHBoxLayout()
        self.doc = doc
        self.pc = app.pc
        self.bookmarks = app.pc.bookmarks
        self.btn_bookmarks: dict[str, QPushButton] = {}
        self.is_setting = False
        self.current_item: PlaylistItem | None = None
        app.pc.add_callback(self)

        for bookmark in app.pc.bookmarks:
            btn = QPushButton(bookmark)
            layout.addWidget(btn)
            btn.setCheckable(True)
            btn.setEnabled(False)
            layout.setStretchFactor(btn, 4)

            btn.clicked.connect(lambda x, bookmark=bookmark: self.on_bookmark(bookmark, x))
            self.btn_bookmarks[bookmark] = btn

        btn = QPushButton("Set")
        btn.setCheckable(True)
        btn.clicked.connect(lambda x: self.on_set(x))
        layout.addWidget(btn)
        self.btn_set = btn

        self.setLayout(layout)

        self.on_set(False)

    def on_set(self, checked: bool) -> None:
        for text, btn in self.btn_bookmarks.items():
            btn.setEnabled(checked or self.bookmarks[text] is not None)

    def switch_buttons(self, target: str | None) -> None:
        for bookmark, btn_bookmark in self.btn_bookmarks.items():
            btn_bookmark.setChecked(bookmark == target)

    def update_bookmark(self, name: str, btn: QPushButton) -> None:
        if self.current_item:
            self.bookmarks.update({name: self.current_item})
            btn.setEnabled(True)
        self.btn_set.setChecked(False)

    def on_bookmark(self, name: str, checked: bool) -> None:
        btn = self.btn_bookmarks[name]
        if self.btn_set.isChecked():
            self.update_bookmark(name, btn)
        else:
            bookmark = self.bookmarks[name]
            if btn.isChecked():
                if bookmark is not None:
                    self.pc.playlist_item_play(bookmark.id)
            else:
                self.switch_buttons(name)

    def pe_play(self, pi: PlaylistItem) -> None:
        self.current_item = pi

        name = pi.song.name
        keys = [k for k, v in self.bookmarks.items() if v is not None and v.song.name == name]
        target = keys[0] if keys else None
        self.switch_buttons(target)


class TabBookmarksWidget(QWidget):
    def __init__(self, doc: DocumentWidget, app: Application) -> None:
        QWidget.__init__(self)

        self.bookmarks = BookmarksWidget(doc, app)

        layout = QHBoxLayout()
        layout.addWidget(self.bookmarks)
        layout.setStretch(0, 1)

        self.btn_next = QPushButton("Next")

        layout.addWidget(self.btn_next)

        self.setLayout(layout)
