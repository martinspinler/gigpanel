#!/usr/bin/python3
import sys
import os
import time
import socket
import threading
import json

import asyncio
import aiohttp
import ssl


#import warnings
from .docwidget import DocumentWidget, DocumentWidgetScrollArea

from PyQt5.QtWidgets import QFileDialog, QDialog, QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QToolButton, QPushButton, QInputDialog, QLineEdit, QLabel, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QTreeWidget, QTreeWidgetItem, QSizePolicy, QMenu, QAction, QFrame, QLabel, QAbstractItemView, QMessageBox, QStackedLayout, QListWidget, QListWidgetItem, QFileIconProvider, QGridLayout, QSizePolicy, QDockWidget, QScrollArea, QAbstractScrollArea, QLayout, QTabBar
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtGui import QFontMetrics, QFont, QImage, QPixmap, QIcon, QPaintEvent, QPainter, QPainterPath, QColor, QPalette, QBrush, QPen, QResizeEvent
from PyQt5.QtCore import Qt, QSize, QPoint, QUrl, QFile, QTimer, QItemSelectionModel, QRect, QRegExp, QIODevice, QCommandLineParser, QCommandLineOption

from PyQt5.QtCore import QPropertyAnimation, QParallelAnimationGroup, QPoint, QAbstractAnimation
from PyQt5.QtCore import QSettings

from midibox import MidiboxQuickWidget

def set_style(self):
    app = self
    style_fs = lambda w, h: (f"min-width:{w}px;max-width:{w}px;" if w != None else "") + (f"min-height:{h}px;max-height:{h}px;" if h != None else "")
    style_fs2 = lambda w, h: (f"max-width:{w}px;" if w != None else "") + (f"max-height:{h}px;" if h != None else "")
    style = ""

    r = app.screens()[0].geometry()
    app.horizontal = r.width() > r.height()

    if app.parser.isSet(app.option_fullscreen):
        font_size = 48
        #doc_w, doc_h = int(1080-240), int(1920)
        #doc_w, doc_h = int(1080), int(1920-240)
        if app.horizontal:
            doc_w, doc_h = r.width()-140, r.height()
        else:
            doc_w, doc_h = r.width(), r.height()
        style = f"""
            QPushButton {{font: {font_size}px;}}
            QListWidget {{font: {font_size}px;}}
            #DocumentWidget {{{style_fs(doc_w, doc_h)} border-color:red; border-width:0px; border-style:solid;}}
            QScrollBar::vertical {{min-width: 40px;}}
            """
    else:
        doc_w, doc_h = 80, 60
        doc_w, doc_h = int(1440), int(1080)
        doc_w, doc_h = int(1440), None
        doc_w, doc_h = int(1080/3), int(1920/3)
        #doc_w, doc_h = int(1080/3), int(1920/3)
        #win_w, win_h = int(1920/2), int(1080/2)

        style = f"""
            DocumentWidget {{{style_fs(doc_w, doc_h)} border-color:red; border-width:2px; border-style:solid;}}
            """

    style += " QPushButton#tempoButton{background-color: yellow; font: 64px;}"
    style += " QPushButton#tempoButton1{background-color: yellow; font: 64px;}"
    style += " QPushButton#tempoButton:checked{background-color: blue;}"
    style += " QPushButton#tempoButton1:checked{background-color: red;}"
    app.setStyleSheet(style);

def song_update_path(song):
    store = app.config['stores'][song['store']] if ('store' in song and song['store'] != None) else app.config['stores'][app.config['defaultStore']]

    if 'file' in song and song['file'] != None:
        song['filename'] = app.config['prefixes'][store['prefix']] + store['path'] + song['file'] + store['suffix']
    elif 'filename' not in song:
        song['filename'] = None

    if (song['filename'] is None or not QFile(song['filename']).exists()) and 'pattern' in store:
        for fn in ([song['file']] if 'file' in song else []) + [song['name']]:
            for instrument in ['-Piano', ' - Piano', '-Electric_Piano', '']:
                filename = app.config['prefixes'][store['prefix']] + store['pattern'].format(name=fn, instrument=instrument)
                if QFile(filename).exists():
                    song['filename'] = filename
                    break
            else:
                continue
            break


class PlaylistItem(QListWidgetItem):
    def __init__(self, song, pli):
        QListWidgetItem.__init__(self, song['name'])
        self.song = song
        [setattr(self, a, pli[a]) for a in ['id']]


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

class HidableTabWidget(QScrollArea):
    def __init__(self, widget):
        super().__init__()

        contentArea = self
        contentArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        #contentArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        contentArea.setMaximumHeight(0)
        contentArea.setMinimumHeight(0)
        contentArea.setWidget(widget)

        contentArea.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        contentArea.setWidgetResizable(True)

        toggleAnimation = QParallelAnimationGroup()
        toggleAnimation.addAnimation(QPropertyAnimation(contentArea, b"maximumHeight"))

        self.contentArea = contentArea
        self.toggleAnimation = toggleAnimation


class HidableTabPanel(QWidget):
    def __init__(self, title=""):
        QWidget.__init__(self)

        tabBar = QTabBar()

        mainLayout = QGridLayout()
        mainLayout.setVerticalSpacing(0)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.addWidget(tabBar, 0, 0, 1, 2)

        self.setLayout(mainLayout)
        self.tb = tabBar

        self.ci = 0
        self.content = []

        tabBar.currentChanged.connect(self.on_tab_changed)

    def addTab(self, name, widget):
        self.tb.addTab(name)
        w = HidableTabWidget(widget)

        self.content.append(w)
        self.layout().addWidget(w, len(self.content), 0, 1, 2)

        if len(self.content) == 1:
            self.on_tab_changed(0)

    def _animate(self, animation, startHeight, endHeight):
        animationDuration = 100
        for i in range(animation.animationCount() - 1):
            SectionAnimation = animation.animationAt(i)
            SectionAnimation.setDuration(animationDuration)
            SectionAnimation.setStartValue(startHeight)
            SectionAnimation.setEndValue(endHeight);

        contentAnimation = animation.animationAt(animation.animationCount() - 1)
        contentAnimation.setDuration(animationDuration)
        contentAnimation.setStartValue(startHeight)
        contentAnimation.setEndValue(endHeight)
        animation.start()

    def on_tab_changed(self, index):
        if not self.content:
            return

        wstart = self.content[self.ci]
        wend = self.content[index]

        self.ci = index

        h = wend.sizeHint().height()
        self._animate(wstart.toggleAnimation, wstart.maximumHeight(), 0)
        self._animate(wend.toggleAnimation, 0, h)


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

class SongListWidget(QListWidget):
    def __init__(self, songs):
        QListWidget.__init__(self)
        #self.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.setSelectionMode(QAbstractItemView.MultiSelection)
        self.loadSongs(songs)

    def loadSongs(self, songs):
        #for song in db['Songs'].values():
        for song in songs.values():
            #if 'Flags' in song and not QFile(song['filename']).exists():
            #if not 'Hidden' in song and not QFile(song['filename']).exists():
                sli = SonglistItem(song)
                self.addItem(sli)
                #if sli.file_exists:
                #    self.addItem(sli)
                #else:
                #    del sli

    def findSong(self, filter_string = ""):
        re = QRegExp(filter_string)
        re.setCaseSensitivity(Qt.CaseInsensitive)
        for i in self.findItems("", Qt.MatchContains):
            i.setHidden(True)
            x = re.indexIn(i.text())
            if x >= 0:
                i.setHidden(False)

class SongListDialog(QDialog):
    nummap = {'1': ".1", '2': "2aábcč", '3': "3dďeéf", '4': "4ghií", '5': "5jkl", '6': "6mnňoó", '7': "7pqrřsš", '8': "8tťuúův", '9': "9wxyýzž", '0': "0 "}
    def __init__(self, gp):
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

        self.songlist = SongListWidget(app.songs)
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

        for text, data, x, y in [
                ("1 *",   1, 0, 0),
                ("2 ABC", 2, 0, 1),
                ("3 DEF", 3, 0, 2),
                ("4 GHI", 4, 1, 0),
                ("5 JKL", 5, 1, 1),
                ("6 MNO", 6, 1, 2),
                ("7 PQRS",7, 2, 0),
                ("8 TUV", 8, 2, 1),
                ("9 WXYZ",9, 2, 2),
                ("0 WXYZ",9, 3, 1),
                ("CLEAR", 0, 3, 0),
                ("SEL", 0xD, 3, 2),
                ("UP",  0xA, 1, 3),
                ("DOWN",0xB, 2, 3),
                ]:
            btn = QPushButton(text)
            btn.clicked.connect(lambda ch,d=data: self.btnpress(d))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding);
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


class PlaylistWidget(QWidget):
    def __init__(self, gp):
        QWidget.__init__(self)
        self.gp = gp
        self.playlist = QListWidgetWithId()
        self.playlist.currentItemChanged.connect(self.current_item_changed)
        #self.playlist.itemActivated.connect(self.item_activated)

        h = QHBoxLayout()
        self.setLayout(h)
        #l.addSpacing(40)
        #l.setStretch(0, 1)

        l = QVBoxLayout()
        if app.horizontal and False:
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

        addButton("Poweroff oscbox", lambda x: app.oc.send_message("/poweroff", None))
        addButton("Move up", lambda x: self.mv(-1))
        addButton("Move down", lambda x: self.mv(+1))
        addButton("Delete", lambda x: self.delete())
        addButton("Insert", self.insert)
        addButton("Add", self.add)
        addButton("Prev",lambda x: app.pc.playlist_item_set(off=-1))
        addButton("Next",lambda x: app.pc.playlist_item_set(off=+1))
        l.addSpacing(40)

        addButton("Next page", lambda x: self.gp.document.next_page())
        #addButton("Store db", self.gp.storeDb)
        addButton("Hide", lambda x: self.gp.wnd.dw.setVisible(False))

        addButton("Exit", lambda x: app.w.close())

    def load(self, playlist):
        self.playlist.clear()

        for songItem in playlist["items"]:
            songId = songItem['songId']
            try:
                song = app.songs[songId]
            except:
                print("Cant find playlist song:", songItem)
            else:
                self.playlist.addItem(PlaylistItem(song, songItem))

    def play(self, pli):
        item = self.playlist.items_by_id[pli['id']]
        x = self.playlist.setCurrentRow(self.playlist.row(item))

    def next(self, ch):
        app.pc.playlist_item_set(1, True)

    def prev(self, ch):
        app.pc.playlist_item_set(-1, True)

    def insert(self, ch):
        d = SongListDialog(self.gp).get_songs()
        if d != None:
            r = self.playlist.currentRow() + 1
            for si in reversed(d):
                pass
                # TODO
#                app.pc.playlist_item_add(si)
#####                self.playlist.insertItem(r, PlaylistItem(si.song))


    def add(self, ch):
        d = SongListDialog(self.gp).get_songs()
        if d != None:
            for si in d:
                app.pc.playlist_item_add(si)

    def delete(self):
        app.pc.playlist_item_del(self.playlist.currentItem().id)

    def client_add(self, pli):
        song = self.gp.songs[pli['songId']]
        self.playlist.addItem(PlaylistItem(song, pli))

    def client_del(self, pli):
        item = self.playlist.items_by_id[pli['id']]
        x = self.playlist.takeItem(self.playlist.row(item))
        del x

    def mv(self, off):
        app.pc.playlist_item_move(self.playlist.currentItem().id, off)
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
            app.tempo.setTempo(ci.song.get('bpm'))

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


class GigPanelWidget(QWidget):
    def __init__(self, wnd):
        QWidget.__init__(self)
        self.wnd = wnd

        self.ext_input_cb = []
        self.stacked_layout = QStackedLayout()
        self.setLayout(self.stacked_layout)
        self.stacked_layout.setStackingMode(QStackedLayout.StackAll)

        self.stacked_layout.setAlignment(Qt.AlignBottom | Qt.AlignLeft);

        l = QVBoxLayout()
        w = QWidget()
        w.setLayout(l)
        self.stacked_layout.setCurrentIndex(0)

        l.setSpacing(0)
        l.setContentsMargins(0, 0, 0, 0)

        self.document = DocumentWidget(self, app)
        sa = DocumentWidgetScrollArea()
        sa.document = self.document
        sa.setWidget(self.document)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sa.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sa.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        sa.setWidgetResizable(True)

        self.stacked_layout.addWidget(sa)

        v = QVBoxLayout()
        l.addLayout(v)

        self.stacked_layout.setCurrentIndex(1)
        self.playlist = PlaylistWidget(self)

        self.stacked_layout.setCurrentIndex(0)

        self.songs = {}

    def loadSong(self, song):
        if 'filename' in song and song['filename']:
            self.document.loadSong(song)

    def loadSongs(self, songs):
        self.songs = songs
        for song in songs.values():
            song_update_path(song)

    def storeDb(self):
        pass
#        for song in self.db["Songs"]:
#            if 'filename' in song:
#                del song['filename']
#
#        p = []
##        for i in self.playlist.playlist.findItems("*", Qt.MatchWildcard):
#        for i in self.playlist.playlist.findItems("", Qt.MatchContains):
#            p.append(i.song['name'])
#
#        #self.db["Playlists"] = [{"Songs": p}]
#
#        with open('pt.yaml', 'w') as file:
#            documents = yaml.dump(self.db, file, allow_unicode=True)
#
#        #self.loadSongs()

class TempoWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.timer = QTimer()
        self.timer.timeout.connect(self.tempoTimeout)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)

        self.tempoBtns = []
        l = QHBoxLayout()
        self.tempoText = QLabel()
        l.addWidget(self.tempoText)
        l.setStretchFactor(self.tempoText, 1)

        for i in range(4):
            btn = QPushButton(str(i+1))
            l.addWidget(btn)
            btn.setEnabled(False)
            self.tempoBtns.append(btn)
            btn.setObjectName("tempoButton" + ("" if i else "1"))
            btn.setAutoFillBackground(False)
            btn.setCheckable(True)
            l.setStretchFactor(btn, 4)
        self.setLayout(l)

    def setTempo(self, bpm):
        if bpm:
            self.timer.start()
            self.timer.setInterval(60000 // bpm)
            self.tempoText.setText(str(bpm))
        else:
            self.timer.stop()
            self.tempoText.setText("")

    def tempoTimeout(self, *args):
        st = None
        for i in range(len(self.tempoBtns)):
            if self.tempoBtns[i].isChecked():
                st = i

        if st is None:
            self.tempoBtns[0].setChecked(True)
        else:
            self.tempoBtns[st].setChecked(False)
            self.tempoBtns[((st+1) % len(self.tempoBtns))].setChecked(True)


class GigPanelWindow(QMainWindow):
    def __init__(self, pcConfig):
        QMainWindow.__init__(self)
        self.setWindowTitle('Gig panel')
        self.gp = GigPanelWidget(self)
        self.setCentralWidget(self.gp)
        self.dw = QDockWidget()
        self.dw.setFeatures(QDockWidget.NoDockWidgetFeatures)


        midibox_params = {'port_name': 'Midibox XIAO BLE'}
        if app.parser.isSet(app.option_use_simulator):
            midibox_params = {'port_name': 'MidiboxSim', 'virtual': True, 'find': True, 'debug': True}
        view = MidiboxQuickWidget(app, midibox_params=midibox_params,
                **({'playlist_url': pcConfig['playlist']} if pcConfig.get('playlist') else {})
            )

        app.midibox = view.midibox
        app.midibox._callbacks.append(self.midicb)
        app.mbview = view
        self.mbview = view

        app.tempo = TempoWidget()

        l = QHBoxLayout()
        l.addWidget(app.tempo)
        l.setStretch(0, 1)

        btn = QPushButton("Next")
        btn.clicked.connect(lambda x: app.pc.playlist_item_set(off=+1))
        l.addWidget(btn)

        w = QWidget()
        w.setLayout(l)

        hw = HidableTabPanel()
        hw.addTab("Hide", HidableTabWidget(QWidget()))
        hw.addTab("Tempo", w)
        hw.addTab("Playlist", self.gp.playlist)
        hw.addTab("Midibox", view)

        self.dw.setWidget(hw)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.dw)

        self.setObjectName("gigpanel window")

        settings = QSettings("cz.spinler", "gigpanel")
        g = settings.value("geometry")
        if g:
            self.restoreGeometry(g)
        ws = settings.value("windowState")
        if ws:
            self.restoreState(ws.toByteArray())

        if app.parser.isSet(app.option_fullscreen):
            self.setWindowState(Qt.WindowFullScreen)

        self.midibox = app.midibox

    def midicb(self, msg):
        if msg.type == 'control_change':
            if msg.is_cc(16) and msg.value > 64:
                self.gp.playlist.gp.document.prev_page()
            if msg.is_cc(17) and msg.value > 64:
                self.gp.playlist.gp.document.next_page()
            if msg.is_cc(18) and msg.value > 64:
                self.mbview.qmidibox.transpositionExtra = not self.mbview.qmidibox.transpositionExtra

    def closeEvent(self, event):
        settings = QSettings("cz.spinler", "gigpanel")
        if not app.parser.isSet(app.option_fullscreen):
            settings.setValue("geometry", self.saveGeometry())
        #settings.setValue("windowState", self.saveState())
        super().closeEvent(event)
