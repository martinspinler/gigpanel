import os

from PyQt5.QtWidgets import QWidget, QListWidget, QListWidgetItem, QHBoxLayout, QVBoxLayout, QPushButton
from . import SongListDialog

class QListWidgetWithId(QListWidget):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.items_by_id = {}

    def addItem(self, i):
        self.items_by_id[i.id] = i
        return super().addItem(i)

    def takeItem(self, i):
        x = super().takeItem(i)
        del self.items_by_id[x.id]
        return x


class PlaylistItem(QListWidgetItem):
    def __init__(self, song, pli):
        if song.get('user_id'):
            name = str(song.get('user_id')) + " - " + song['name']
        else:
            name = song['name']

        QListWidgetItem.__init__(self, name)
        self.song = song
        [setattr(self, a, pli[a]) for a in ['id']]


class PlaylistWidget(QWidget):
    def __init__(self, gp, app, window):
        QWidget.__init__(self)
        self.app = app
        self.gp = gp
        self.playlist = QListWidgetWithId()
        self.playlist.currentItemChanged.connect(self.current_item_changed)
        #self.playlist.itemActivated.connect(self.item_activated)

        h = QHBoxLayout()
        self.setLayout(h)
        #l.addSpacing(40)
        #l.setStretch(0, 1)

        layout = QVBoxLayout()
        if self.app.horizontal and False:
            #l = QVBoxLayout()
            layout.addWidget(self.playlist)
        else:
            h.addWidget(self.playlist)
        h.addLayout(layout)

        #l.setStretch(0, 1)
        #h.addLayout(l)
        #l = QVBoxLayout()

        def addButton(text, cb):
            btn = QPushButton(text)
            btn.clicked.connect(cb)
            layout.addWidget(btn)

        midibox_host = app.mb_cfg.get("backend-params", {}).get("addr", 'invalid')
        cmd = f'ssh -o ConnectTimeout=3 {midibox_host} -C sudo poweroff'
        addButton("Poweroff oscbox", lambda x: os.system(cmd))
        #addButton("Poweroff oscbox", lambda x: self.app.oc.send_message("/poweroff", None))
        addButton("Move up", lambda x: self.mv(-1))
        addButton("Move down", lambda x: self.mv(+1))
        addButton("Delete", lambda x: self.delete())
        addButton("Add", self.add)
        addButton("Prev", lambda x: self.app.pc.playlist_item_set(off=-1))
        addButton("Next", lambda x: self.app.pc.playlist_item_set(off=+1))
        layout.addSpacing(40)

        addButton("Next page", lambda x: self.gp.document.next_page())
        #addButton("Store db", self.gp.storeDb)
        addButton("Hide", lambda x: self.gp.wnd.dw.setVisible(False))

        addButton("Exit", lambda x: window.close())

    def load(self, playlist):
        self.playlist.clear()

        for songItem in playlist:
            playlistItem = playlist[songItem]
            songId = playlistItem['song_id']
            try:
                song = self.gp.songs[songId]
            except KeyError:
                print("Cant find playlist song:", songItem)
            else:
                self.playlist.addItem(PlaylistItem(song, playlistItem))

    def play(self, pli):
        item = self.playlist.items_by_id[pli['id']]
        self.playlist.setCurrentRow(self.playlist.row(item))

    def add(self, ch):
        d = SongListDialog(self.gp, self.app).get_songs()
        if d is not None:
            for si in d:
                self.app.pc.playlist_item_add(si)

    def delete(self):
        self.app.pc.playlist_item_del(self.playlist.currentItem().id)

    def client_add(self, pli):
        song = self.gp.songs[pli['song_id']]
        self.playlist.addItem(PlaylistItem(song, pli))

    def client_del(self, pli):
        item = self.playlist.items_by_id[pli['id']]
        x = self.playlist.takeItem(self.playlist.row(item))
        del x

    def mv(self, off):
        if self.playlist.currentItem():
            self.app.pc.playlist_item_move(self.playlist.currentItem().id, off)

    def current_item_changed(self, ci, pi):
        if ci:
            self.gp.loadSong(ci.song)
            self.app.tempo.setTempo(ci.song.get('bpm'))

    def livelist_client_cb(self, cmd, data):
        requests = {
            'add': self.client_add,
            'delete': self.client_del,
            'update': self.load,
            'play': self.play
        }
        if cmd in requests:
            requests[cmd](data)
        elif not cmd.startswith("_"):
            print("Playlist: unhandled cmd", cmd)
