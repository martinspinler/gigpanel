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
from .widgets import HidableTabPanel, TabTempoWidget

from PyQt5.QtWidgets import QFileDialog, QDialog, QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QToolButton, QPushButton, QInputDialog, QLineEdit, QLabel, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QTreeWidget, QTreeWidgetItem, QSizePolicy, QMenu, QAction, QFrame, QLabel, QAbstractItemView, QMessageBox, QStackedLayout, QListWidget, QListWidgetItem, QFileIconProvider, QGridLayout, QSizePolicy, QDockWidget, QScrollArea, QAbstractScrollArea, QLayout, QTabBar
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtGui import QFontMetrics, QFont, QImage, QPixmap, QIcon, QPaintEvent, QPainter, QPainterPath, QColor, QPalette, QBrush, QPen, QResizeEvent
from PyQt5.QtCore import Qt, QSize, QPoint, QUrl, QFile, QTimer, QItemSelectionModel, QRect, QRegExp, QIODevice, QCommandLineParser, QCommandLineOption

from PyQt5.QtCore import QPropertyAnimation, QParallelAnimationGroup, QPoint, QAbstractAnimation
from PyQt5.QtCore import QSettings

from midibox.widget import MidiboxQuickWidget


def set_style(app):
    style_fs = lambda w, h: (f"min-width:{w}px;max-width:{w}px;" if w != None else "") + (f"min-height:{h}px;max-height:{h}px;" if h != None else "")
    style_fs2 = lambda w, h: (f"max-width:{w}px;" if w != None else "") + (f"max-height:{h}px;" if h != None else "")
    style = ""

    r = app.screens()[0].geometry()
    app.horizontal = r.width() > r.height()

    if app.args.fullscreen:
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


def song_update_path(song, app):
    store = app.config['stores'][song['store']] if ('store' in song and song['store'] != None) else app.config['stores'][app.config['defaultStore']]

    file = song.get('filename')

    if file:
        song['filename'] = app.config['prefixes'][store['prefix']] + store['path'] + file + store['suffix']
    elif 'filename' not in song:
        song['filename'] = None

    if (song['filename'] is None or not QFile(song['filename']).exists()) and 'pattern' in store:
        for fn in ([file] if file else []) + [song['name']]:
            for instrument in ['-Piano', ' - Piano', '-Electric_Piano', ' Piano', '']:
                filename = app.config['prefixes'][store['prefix']] + store['pattern'].format(name=fn, instrument=instrument)
                if QFile(filename).exists():
                    song['filename'] = filename
                    break
            else:
                continue
            break


class GigPanelWidget(QWidget):
    def __init__(self, wnd, app):
        QWidget.__init__(self)
        self.app = app
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
        self.playlist = PlaylistWidget(self, app, self.wnd)

        self.stacked_layout.setCurrentIndex(0)

        self.songs = {}

    def loadSong(self, song):
        if 'filename' in song and song['filename']:
            self.document.loadSong(song)

    def loadSongs(self, songs):
        self.songs = songs
        for song in songs.values():
            song_update_path(song, self.app)

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


class GigPanelWindow(QMainWindow):
    def __init__(self, pcConfig, app):
        set_style(app)

        QMainWindow.__init__(self)
        self.setWindowTitle('Gig panel')
        self.app = app

        self.gp = GigPanelWidget(self, app)
        self.setCentralWidget(self.gp)

        self.gp.document.setClickCallback(self.onDocumentClick)

        self.midibox = app.midibox
        view = MidiboxQuickWidget(app, self.midibox,
            **dict({'playlist_url': pcConfig['url']} if pcConfig.get('url') else {}),
            **dict({'config': app.midibox_widget_cfg} if app.midibox_widget_cfg else {}),
        )

        self.midibox._callbacks.append(self.midicb)
        app.mbview = view
        self.mbview = view

        self.tab_tempo = TabTempoWidget()
        app.tempo = self.tab_tempo.tempo
        hw = HidableTabPanel()
        #hw.addTab("Hide", HidableTabWidget(QWidget()))
        hw.addTab("Tempo", self.tab_tempo)
        hw.addTab("Playlist", self.gp.playlist)
        hw.addTab("Midibox", view)

        self.hw = hw

        self.dw = QDockWidget()
        self.dw.setFeatures(QDockWidget.NoDockWidgetFeatures)
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

        if app.args.fullscreen:
            self.setWindowState(Qt.WindowFullScreen)

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
        if not self.app.args.fullscreen:
            settings.setValue("geometry", self.saveGeometry())
        #settings.setValue("windowState", self.saveState())
        super().closeEvent(event)

    def dwSetVisible(self, v: bool, index = 1):
        self.hw.tb.setCurrentIndex(index if v else 0)

    def dwIsVisible(self):
        return self.hw.tb.currentIndex() > 0
