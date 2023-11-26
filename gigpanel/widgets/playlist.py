from PyQt5.QtWidgets import QFileDialog, QDialog, QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QToolButton, QPushButton, QInputDialog, QLineEdit, QLabel, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QTreeWidget, QTreeWidgetItem, QSizePolicy, QMenu, QAction, QFrame, QLabel, QAbstractItemView, QMessageBox, QStackedLayout, QListWidget, QListWidgetItem, QFileIconProvider, QGridLayout, QSizePolicy, QDockWidget, QScrollArea, QAbstractScrollArea, QLayout, QTabBar
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtGui import QFontMetrics, QFont, QImage, QPixmap, QIcon, QPaintEvent, QPainter, QPainterPath, QColor, QPalette, QBrush, QPen, QResizeEvent
from PyQt5.QtCore import Qt, QSize, QPoint, QUrl, QFile, QTimer, QItemSelectionModel, QRect, QRegExp, QIODevice, QCommandLineParser, QCommandLineOption

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

        l = QVBoxLayout()
        if self.app.horizontal and False:
            #l = QVBoxLayout()
            l.addWidget(self.playlist)
        else:
            h.addWidget(self.playlist)
        h.addLayout(l)

        #l.setStretch(0, 1)
        #h.addLayout(l)
        #l = QVBoxLayout()

        def addButton(text, cb):
            btn = QPushButton(text)
            btn.clicked.connect(cb)
            l.addWidget(btn)

        addButton("Poweroff oscbox", lambda x: self.app.oc.send_message("/poweroff", None))
        addButton("Move up", lambda x: self.mv(-1))
        addButton("Move down", lambda x: self.mv(+1))
        addButton("Delete", lambda x: self.delete())
        addButton("Insert", self.insert)
        addButton("Add", self.add)
        addButton("Prev",lambda x: self.app.pc.playlist_item_set(off=-1))
        addButton("Next",lambda x: self.app.pc.playlist_item_set(off=+1))
        l.addSpacing(40)

        addButton("Next page", lambda x: self.gp.document.next_page())
        #addButton("Store db", self.gp.storeDb)
        addButton("Hide", lambda x: self.gp.wnd.dw.setVisible(False))

        addButton("Exit", lambda x: window.close())

    def load(self, playlist):
        self.playlist.clear()

        for songItem in playlist["items"]:
            songId = songItem['songId']
            try:
                song = self.gp.songs[songId]
            except:
                print("Cant find playlist song:", songItem)
            else:
                self.playlist.addItem(PlaylistItem(song, songItem))

    def play(self, pli):
        item = self.playlist.items_by_id[pli['id']]
        x = self.playlist.setCurrentRow(self.playlist.row(item))

    def insert(self, ch):
        d = SongListDialog(self.gp, self.app).get_songs()
        if d != None:
            r = self.playlist.currentRow() + 1
            for si in reversed(d):
                pass
                # TODO
#                app.pc.playlist_item_add(si)
#####                self.playlist.insertItem(r, PlaylistItem(si.song))


    def add(self, ch):
        d = SongListDialog(self.gp, self.app).get_songs()
        if d != None:
            for si in d:
                self.app.pc.playlist_item_add(si)

    def delete(self):
        self.app.pc.playlist_item_del(self.playlist.currentItem().id)

    def client_add(self, pli):
        song = self.gp.songs[pli['songId']]
        self.playlist.addItem(PlaylistItem(song, pli))

    def client_del(self, pli):
        item = self.playlist.items_by_id[pli['id']]
        x = self.playlist.takeItem(self.playlist.row(item))
        del x

    def mv(self, off):
        self.app.pc.playlist_item_move(self.playlist.currentItem().id, off)
        return
        r = self.playlist.currentRow()
        x = self.playlist.takeItem(r)
        if off:
            self.playlist.insertItem(r + off, x)
            r = self.playlist.setCurrentRow(r + off)
        else:
            del x

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
        else:
            print("Playlist: unhandled cmd", cmd)
