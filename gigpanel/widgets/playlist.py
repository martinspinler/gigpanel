import os
from typing import Callable, Any, Optional


from PyQt5.QtWidgets import QWidget, QListWidget, QListWidgetItem, QHBoxLayout, QVBoxLayout, QPushButton

from . import SongListDialog


from ..playlist import PlaylistEventListener
from ..song import Playlist, PlaylistItem
from ..app import Application

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from ..window import GigPanelWidget, GigPanelWindow


class QPlaylistItem(QListWidgetItem):
    def __init__(self, pli: PlaylistItem):
        self.song = song = pli.song
        name = f"{song.user_id} - {song.name}" if song.user_id else song.name

        QListWidgetItem.__init__(self, name)
        self.id = pli.id
        self.pli = pli


class QListWidgetWithId(QListWidget):
    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self.items_by_id: dict[int, QPlaylistItem] = {}

    def add_item(self, i: QPlaylistItem) -> None:
        self.items_by_id[i.id] = i
        super().addItem(i)

    def takeItem(self, row: int) -> QListWidgetItem | None:
        i = super().takeItem(row)
        if isinstance(i, QPlaylistItem):
            del self.items_by_id[i.id]
        return i


class PlaylistWidget(PlaylistEventListener, QWidget):
    def __init__(self, window: "GigPanelWindow", gp: "GigPanelWidget", app: Application):
        QWidget.__init__(self)
        self.app = app
        self.gp = gp
        self.gpwindow = window
        self.playlist = QListWidgetWithId()
        self.playlist.currentItemChanged.connect(self.current_item_changed)
        self.playlist.itemActivated.connect(self.item_activated)

        h = QHBoxLayout()
        self.setLayout(h)
        #l.addSpacing(40)
        #l.setStretch(0, 1)

        layout = QVBoxLayout()
        if self.app.appconfig.horizontal and False:
            #l = QVBoxLayout()
            layout.addWidget(self.playlist)
        else:
            h.addWidget(self.playlist)
        h.addLayout(layout)

        #l.setStretch(0, 1)
        #h.addLayout(l)
        #l = QVBoxLayout()

        def addButton(text: str, cb: Callable[[QPushButton], Any]) -> None:
            btn = QPushButton(text)
            btn.clicked.connect(cb)
            layout.addWidget(btn)

        midibox_host = app.mb_cfg.get("backend-params", {}).get("addr", 'invalid')
        cmd = f'ssh -o ConnectTimeout=3 {midibox_host} -C sudo poweroff'
        addButton("Playlist config", lambda x: self.app.pc.show_config())
        #addButton("Poweroff oscbox", lambda x: self.app.oc.send_message("/poweroff", None))
        addButton("Move up", lambda x: self.mv(-1))
        addButton("Move down", lambda x: self.mv(+1))
        addButton("Delete", lambda x: self.delete())
        addButton("Add", self.add)
        addButton("Prev", lambda x: self.app.pc.playlist_item_play(off=-1))
        addButton("Next", lambda x: self.app.pc.playlist_item_play(off=+1))
        addButton("Poweroff oscbox", lambda x: os.system(cmd))
        layout.addSpacing(40)

        addButton("Next page", lambda x: self.gp.document.next_page())
        #addButton("Store db", self.gp.storeDb)
        #addButton("Hide", lambda x: self.gpwindow.dw.setVisible(False))

        addButton("Exit", lambda x: window.close())

    def load(self, playlist: Playlist) -> None:
        ci = self.playlist.currentItem()
        ciid = ci.id if isinstance(ci, QPlaylistItem) else None
        self.playlist.clear()

        for playlistItem in playlist:
            pi = QPlaylistItem(playlistItem)
            self.playlist.add_item(pi)

            if ciid == pi.id:
                self.playlist.setCurrentItem(pi)

    def pe_play(self, pli: PlaylistItem) -> None:
        item = self.playlist.items_by_id[pli.id]
        self.playlist.setCurrentRow(self.playlist.row(item))

    def add(self, ch: QPushButton) -> None:
        d = SongListDialog(self.gpwindow, self.app).get_songs()
        if d is not None:
            for si in d:
                self.app.pc.playlist_item_add(si.song)

    def delete(self) -> None:
        ci: Optional[QListWidgetItem] = self.playlist.currentItem()
        if isinstance(ci, QPlaylistItem):
            self.app.pc.playlist_item_del(ci.id)

    def pe_add(self, pli: PlaylistItem) -> None:
        self.playlist.add_item(QPlaylistItem(pli))

    def client_del(self, pli: PlaylistItem) -> None:
        item = self.playlist.items_by_id[pli.id]
        x = self.playlist.takeItem(self.playlist.row(item))
        del x

    def mv(self, off: int) -> None:
        ci = self.playlist.currentItem()
        if isinstance(ci, QPlaylistItem):
            self.app.pc.playlist_item_move(ci.id, off)

    def current_item_changed(self, ci: QPlaylistItem | None, pi: QPlaylistItem | None) -> None:
        if ci:
            self.app.pc.playlist_item_set(ci.id)
            self.gp.loadSong(ci.pli)

    def item_activated(self, ci: QPlaylistItem) -> None:
        self.app.pc.playlist_item_set(ci.id, 0)

    def pe_update_playlist(self, data: Playlist) -> None:
        self.load(data)
