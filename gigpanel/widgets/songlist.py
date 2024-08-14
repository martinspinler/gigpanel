from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QAbstractItemView, QListWidget, QListWidgetItem, QFileIconProvider, QGridLayout, QSizePolicy
from PyQt5.QtCore import Qt, QFile, QItemSelectionModel, QRegExp


class SonglistItem(QListWidgetItem):
    def __init__(self, song):
        QListWidgetItem.__init__(self, song['name'])
        self.song = song
        self.file_exists = False

        if song['filename']:
            if QFile(song['filename']).exists():
                self.file_exists = True
                self.setIcon(QFileIconProvider().icon(QFileIconProvider.File))
            else:
                self.setIcon(QFileIconProvider().icon(QFileIconProvider.Trashcan))
        if 'Flags' in song:
            self.setIcon(QFileIconProvider().icon(QFileIconProvider.Desktop))


class SongListWidget(QListWidget):
    def __init__(self, songs):
        QListWidget.__init__(self)
        #self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionMode(QAbstractItemView.MultiSelection)
        self.loadSongs(songs)

    def loadSongs(self, songs):
        #for song in db['Songs'].values():
        for song in songs.values():
            sli = SonglistItem(song)
            self.addItem(sli)

    def findSong(self, filter_string=""):
        re = QRegExp(filter_string)
        re.setCaseSensitivity(Qt.CaseInsensitive)
        for i in self.findItems("", Qt.MatchContains):
            i.setHidden(True)
            x = re.indexIn(i.text())
            if x >= 0:
                i.setHidden(False)


class SongListDialog(QDialog):
    nummap = {'1': ".1", '2': "2aábcč", '3': "3dďeéf", '4': "4ghií", '5': "5jkl", '6': "6mnňoó", '7': "7pqrřsš", '8': "8tťuúův", '9': "9wxyýzž", '0': "0 "}

    def __init__(self, gp, app):
        QDialog.__init__(self)
        self.gp = gp

        self.setModal(True)
        self.setGeometry(gp.parent().geometry())

        self.setWindowState(gp.parent().windowState())

        h = QHBoxLayout()
        self.setLayout(h)

        v = QVBoxLayout()
        h.addLayout(v)
        #self.setLayout(v)

        self.songlist = SongListWidget(gp.songs)
        #self.songlist = SongListWidget(None)
        v.addWidget(self.songlist)
        g = QGridLayout()
        if app.horizontal:
            h.addLayout(g)
        else:
            v.addLayout(g)
        btn = QPushButton("OK")
        btn.clicked.connect(lambda ch: self.accept())
        v.addWidget(btn)

        btn = QPushButton("Cancel")
        btn.clicked.connect(lambda ch: self.reject())
        v.addWidget(btn)

        keypad = [
            ("1 *",    1, 0, 0),
            ("2 ABC",  2, 0, 1),
            ("3 DEF",  3, 0, 2),
            ("4 GHI",  4, 1, 0),
            ("5 JKL",  5, 1, 1),
            ("6 MNO",  6, 1, 2),
            ("7 PQRS", 7, 2, 0),
            ("8 TUV",  8, 2, 1),
            ("9 WXYZ", 9, 2, 2),
            ("0 WXYZ", 9, 3, 1),
            ("CLEAR",  0, 3, 0),
            ("SEL",  0xD, 3, 2),
            ("UP",   0xA, 1, 3),
            ("DOWN", 0xB, 2, 3),
        ]
        for text, data, x, y in keypad:
            btn = QPushButton(text)
            btn.clicked.connect(lambda ch, d=data: self.btnpress(d))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            g.addWidget(btn, x, y)
            g.setRowStretch(x, 1)

        self.filter_string = ""
        self.filter_btns = []

    def btnpress(self, btn):
        self.ext_input(btn)

    def get_songs(self):
        self.gp.ext_input_cb.append(self.ext_input)
        self.exec_()
        del self.gp.ext_input_cb[-1]

        if self.result() == QDialog.Accepted:
            return self.songlist.selectedItems()
        else:
            return None

    def ext_input(self, btn):
        filter_btns = self.filter_btns.copy()
        if btn >= 1 and btn <= 9:
            filter_btns.append(chr(ord('0') + btn))
        elif btn == 0:
            filter_btns = filter_btns[:-1]
            filter_btns = []
        elif btn == 0x0A or btn == 0x0B:
            self.songlist.setCurrentRow(self.songlist.currentRow() + (1 if btn == 0x0B else -1), QItemSelectionModel.Current)
            self.songlist.setFocus()
        elif btn == 0x0D:
            sm = self.songlist.selectionModel()
            sm.select(sm.currentIndex(), QItemSelectionModel.Toggle)
            #self.songlist.setFocus()
            filter_btns = []
        elif btn == 0x0E:
            self.reject()
        elif btn == 0x0F:
            self.accept()

        if filter_btns != self.filter_btns:
            self.filter_string = "".join(["[" + SongListDialog.nummap[num] + "]" for num in filter_btns])
            self.songlist.findSong(self.filter_string)
            self.filter_btns = filter_btns
            self.songlist.setFocus()
