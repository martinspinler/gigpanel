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
from .widgets import DocumentWidget, DocumentWidgetScrollArea
from .widgets import SongListDialog, PlaylistWidget
from .widgets import HidableTabPanel

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
        for fn in ([song['file']] if 'file' in song and song['file'] else []) + [song['name']]:
            for instrument in ['-Piano', ' - Piano', '-Electric_Piano', ' Piano', '']:
                filename = app.config['prefixes'][store['prefix']] + store['pattern'].format(name=fn, instrument=instrument)
                if QFile(filename).exists():
                    song['filename'] = filename
                    break
            else:
                continue
            break




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
        self.playlist = PlaylistWidget(self, app)

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
        #hw.addTab("Hide", HidableTabWidget(QWidget()))
        hw.addTab("Tempo", w)
        hw.addTab("Playlist", self.gp.playlist)
        hw.addTab("Midibox", view)

        self.hw = hw
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

        self.gp.document.setClickCallback(self.onDocumentClick)

    def onDocumentClick(self, pos, size):
        visible = self.dwIsVisible()
        if visible or pos.y() > int(size.height() * 0.9):
            self.dwSetVisible(not visible, 2 if pos.x() > self.width() // 2 else 1)
            return True
        else:
            return False

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

    def dwSetVisible(self, v: bool, index = 1):
        self.hw.tb.setCurrentIndex(index if v else 0)

    def dwIsVisible(self):
        return self.hw.tb.currentIndex() > 0
