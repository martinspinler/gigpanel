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

import functools

#import warnings
from docwidget import DocumentWidget

from PyQt5.QtWidgets import QFileDialog, QDialog, QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QPushButton, QInputDialog, QLineEdit, QLabel, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QTreeWidget, QTreeWidgetItem, QSizePolicy, QMenu, QAction, QFrame, QLabel, QAbstractItemView, QMessageBox, QStackedLayout, QListWidget, QListWidgetItem, QFileIconProvider, QGridLayout, QSizePolicy, QDockWidget, QScrollArea, QAbstractScrollArea
from PyQt5.QtGui import QFontMetrics, QFont, QImage, QPixmap, QIcon, QPaintEvent, QPainter, QPainterPath, QColor, QPalette, QBrush, QPen, QResizeEvent
from PyQt5.QtCore import Qt, QSize, QPoint, QUrl, QFile, QTimer, QItemSelectionModel, QRect, QRegExp, QIODevice, QCommandLineParser, QCommandLineOption

from asyncqt import QEventLoop

import popplerqt5
import yaml

import numpy as np
from linetimer import CodeTimer

from typing import List, Tuple, Union, Any, Iterable
from pythonosc import osc_packet
from pythonosc.osc_message_builder import OscMessageBuilder

def song_update_path(song):
    if 'file' in song and song['file'] != None:
        store = app.config['stores'][song['store']] if ('store' in song and song['store'] != None) else app.config['stores'][app.config['defaultStore']]
        song['filename'] = app.config['prefixes'][store['prefix']] + store['path'] + song['file'] + store['suffix']
    elif 'filename' not in song:
        song['filename'] = None

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
        if app.horizontal:
            #l = QVBoxLayout()
            l.addWidget(self.playlist)
        else:
            h.addWidget(self.playlist)
        h.addLayout(l)

        #l.setStretch(0, 1)
        #h.addLayout(l)
        #l = QVBoxLayout()

        btn = QPushButton("Poweroff oscbox")
        btn.clicked.connect(lambda x: oc.send_message("/poweroff", None))
        l.addWidget(btn)

        btn = QPushButton("Move up")
        btn.clicked.connect(lambda x: self.mv(-1))
        l.addWidget(btn)

        btn = QPushButton("Move down")
        btn.clicked.connect(lambda x: self.mv(+1))
        l.addWidget(btn)

        btn = QPushButton("Delete")
        btn.clicked.connect(lambda x: self.delete())
        l.addWidget(btn)

        btn = QPushButton("Insert")
        btn.clicked.connect(self.insert)
        l.addWidget(btn)

        btn = QPushButton("Add")
        btn.clicked.connect(self.add)
        l.addWidget(btn)

        btn = QPushButton("Prev")
        btn.clicked.connect(lambda x: app.pc.playlist_item_set(off=-1))
        l.addWidget(btn)
        btn = QPushButton("Next")
        btn.clicked.connect(lambda x: app.pc.playlist_item_set(off=1))
        l.addWidget(btn)

        l.addWidget(btn)
        l.addSpacing(40)

        btn = QPushButton("Next page")
        btn.clicked.connect(lambda x: self.gp.document.next_page())
        l.addWidget(btn)

        btn = QPushButton("Store db")
        #btn.clicked.connect(self.gp.storeDb)
        l.addWidget(btn)

        btn = QPushButton("Hide")
        btn.clicked.connect(lambda x: self.gp.wnd.dw.setVisible(False))
        l.addWidget(btn)

        btn = QPushButton("Exit")
        btn.clicked.connect(lambda ch: app.w.close())
        l.addWidget(btn)

    def load(self, playlist):
        self.playlist.clear()
        #x = self.playlist.takeItem(self.playlist.row(item))
        #del x

        for songItem in playlist["items"]:
            songId = songItem['songId']
            try:
                #song = [x for x in self.gp.db['Songs'] if x['name'] == name][0]
                song = app.songs[songId]
            except:
                #print("Cant find playlist song:", name)
                print("Cant find playlist song:", songItem)
            else:
                self.playlist.addItem(PlaylistItem(song, songItem))

    def play(self, pli):
        item = self.playlist.items_by_id[pli['id']]
        x = self.playlist.setCurrentRow(self.playlist.row(item))

        #self.playlist.setCurrentRow(self.playlist.currentRow() + 1)
        pass
    def next(self, ch):
        app.pc.playlist_item_set(1, True)
    def prev(self, ch):
        app.pc.playlist_item_set(-1, True)

        #self.playlist.setCurrentRow(self.playlist.currentRow() + 1)

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
        #self.stacked_layout.addWidget(w)

        l.setSpacing(0)
        l.setContentsMargins(0, 0, 0, 0)

        self.document = DocumentWidget(self, app)
        #l.addWidget(self.document)
        sa = QScrollArea()
        sa.setWidget(self.document)
        sa.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sa.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sa.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        sa.setWidgetResizable(True)
        #self.stacked_layout.addWidget(self.document)
        self.stacked_layout.addWidget(sa)

        v = QVBoxLayout()
        l.addLayout(v)

        #self.loadDb()

        #self.song_list = SongListWidget(self.db)
        #self.stacked_layout.addWidget(self.song_list)
        self.stacked_layout.setCurrentIndex(1)
        self.playlist = PlaylistWidget(self)
        #self.playlist.setFixedSize(800, 800)
        #self.stacked_layout.addWidget(self.playlist)

        #self.playlist.setAlignment(Qt.AlignBottom | Qt.AlignLeft);
        self.stacked_layout.setCurrentIndex(0)

        #self.db = {}
        self.songs = {}

        #v.addWidget(self.playlist)

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

class GigPanelWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.setWindowTitle('Gig panel')
        self.gp = GigPanelWidget(self)
        self.setCentralWidget(self.gp)
        self.dw = QDockWidget()
        self.dw.setWidget(self.gp.playlist)
        self.addDockWidget(Qt.RightDockWidgetArea if app.horizontal else Qt.BottomDockWidgetArea, self.dw)
        if app.parser.isSet(app.option_fullscreen):
            self.setWindowState(Qt.WindowFullScreen)

class GigPanelOSCClient(threading.Thread):
    def __init__(self, gp, addr):
        threading.Thread.__init__(self)
        self.addr = addr
        self.gp = gp
        self.s = None

    def start(self):
        self.alive = threading.Event()
        self.alive.set()

        threading.Thread.start(self)

#    def start_listen(self):
        #t = threading.Thread(target = self.listen)
        #t.start()

    def stop(self):
        self.alive.clear()
        if self.s:
            self.s.shutdown(socket.SHUT_RDWR)
            self.s.close()
        self.join()

    def handle_msg(self, m):
        print(m.message.address, m.message.params)
        if m.message.address == "/next":
            self.gp.playlist.gp.document.next_page()
        if m.message.address == "/prev":
            self.gp.playlist.gp.document.prev_page()

    def send_message(self, address: str, value: Union[int, float, bytes, str, bool, tuple, list]) -> None:
        builder = OscMessageBuilder(address=address)
        if value is None:
            values = []
        elif not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
            values = [value]
        else:
            values = value
        for val in values: builder.add_arg(val)
        msg = builder.build()
        try:
            self.s.sendall(msg.size.to_bytes(length=4, byteorder='little') + msg._dgram)
        except:
            pass

    def run(self):
        while self.s == None and self.alive.is_set():
            try:
                self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.s.connect(self.addr)
            except OSError:
                self.s = None
                time.sleep(1)

        if self.s:
            print("OSC client connected")

        while self.alive.is_set():
            try:
                sz = self.s.recv(4)
                if not sz:
                    break
                data = self.s.recv(int.from_bytes(sz, byteorder='little'))
                for m in osc_packet.OscPacket(data).messages:
                    self.handle_msg(m)
            except socket.timeout:
                pass

class PlaylistClient():
    def __init__(self):
        self.queue = asyncio.Queue()

    async def _receive_msg(self, msgid):
        i = 0
        while True:
            i += 1
            if i > 100:
                #print("Keep-alive", time.time())
                await self.ws.send_str("client:keep-alive-hotfix:")
                i = 0

            try:
                msg = self.queue.get_nowait()
                if msg == "close":
                    await self._disconnect()
                    return None, None
            except asyncio.QueueEmpty:
                pass
            else:
                await self.ws.send_str("client:" + msg)

            try:
                msg = await self.ws.receive(timeout=0.1)
            except asyncio.TimeoutError as e:
                continue

            if msg.type == aiohttp.WSMsgType.TEXT:
                text = msg.data
                if text.startswith("client:"):
                    _,req, data = text.split(":", 2)
                    if msgid == None:
                        return req, data
                    if req == msgid:
                        return req, data
                elif text.startswith("lona:"):
                    pass
                else:
                    print(msg)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print("Err")
                break
            elif msg.type == aiohttp.WSMsgType.CLOSE:
                print("Close")
                #self._reconnect()
                #await self.ws.close()
                break
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                print("Closed")
                #await self._reconnect()
                await self.session.close()
                await self.connect(self.w, self.addr, self.s == "s")

                await self.get_playlist()
            else:
                print(msg.type)
        return None, None

    async def connect(self, widget, addr = 'pcspinler-emil.fit.vutbr.cz/playlist', secure = False):
        self.w = widget
        self.session = aiohttp.ClientSession()
        ssl._create_default_https_context = ssl._create_unverified_context
        self.context = ssl._create_unverified_context()
        self.addr = addr

        self.s = "s" if secure else ""
        self.headers = {}
        resp = await self.session.get(f'http{self.s}://{addr}/client/', ssl=self.context, headers=self.headers)
        t1 = await resp.text()
        if 'refresh' in t1:
            resp = await self.session.get(f'http{self.s}://{addr}/client/', ssl=self.context, headers=self.headers)
            t1 = await resp.text()
        await self._reconnect()

    async def _reconnect(self):
        self.ws = await self.session.ws_connect(f'ws{self.s}://{self.addr}/client/', ssl=self.context, headers=self.headers)
        msg = """lona:[1,null,101,["/playlist/client/",null]]"""

        await self.ws.send_str(msg)

    async def _disconnect(self):
        await self.ws.close()
        await self.session.close()

    def disconnect(self):
        self.queue.put_nowait('close')

    def playlist_item_add(self, si):
        self.queue.put_nowait('add:' + json.JSONEncoder().encode({'songId': si.song['id'], 'playlistId': 1}))

    def playlist_item_del(self, si):
        self.queue.put_nowait('delete:' + json.JSONEncoder().encode({'id': si, 'playlistId': 1}))

    def playlist_item_move(self, si, pos):
        self.queue.put_nowait('move:' + json.JSONEncoder().encode({'id': si, 'playlistId': 1, 'pos': pos}))

    def playlist_item_set(self, id = None, off = None):
        self.queue.put_nowait('play:' + json.JSONEncoder().encode({'id': id, 'playlistId': 1, 'off': off}))

    async def get_messages(self):
        while True:
            req, data = await self._receive_msg(None)
            if req == 'add':
                self.w.playlist.client_add(json.JSONDecoder().decode(data))
            elif req == 'delete':
                self.w.playlist.client_del(json.JSONDecoder().decode(data))
            elif req == 'update':
                self.w.playlist.load(json.JSONDecoder().decode(data))
            elif req == 'play':
                self.w.playlist.play(json.JSONDecoder().decode(data))

            if req == None:
                break

    async def get_playlist(self):
        await self.ws.send_str("client:get-playlist:" + json.JSONEncoder().encode({'playlistId': 1}))
        _, data = await self._receive_msg('playlist')
        j = json.JSONDecoder().decode(data)
        return j

    async def get_db(self):
        await self.ws.send_str("client:get-songlist:")
        _, data = await self._receive_msg('songlist')
        j = json.JSONDecoder().decode(data)
        j = {int(k):v for k,v in j.items()}
        [j[k].update({'id':k}) for k in j.keys()]
        return j


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
        #win_w, win_h = int(1920/2), int(1080/2)

        style = f"""
            DocumentWidget {{{style_fs(doc_w, doc_h)} border-color:red; border-width:2px; border-style:solid;}}
            """

    app.setStyleSheet(style);


def init_parser(self):
    app = self
    app.parser = QCommandLineParser()
    app.parser.setApplicationDescription("Gig Panel");
    app.parser.addHelpOption();
    app.option_fullscreen = QCommandLineOption("f", "Show fullscreen")
    app.option_edit_splitpoints = QCommandLineOption("s", "Edit splitpoints")
    app.option_edit_bounding_box = QCommandLineOption("b", "Edit bounding box")
    app.parser.addOption(app.option_fullscreen)
    app.parser.addOption(app.option_edit_splitpoints)
    app.parser.addOption(app.option_edit_bounding_box)
    app.parser.process(app);


def init_loop(app):
    loop = asyncio.get_event_loop()
    future = asyncio.Future()

    def close_future(future, loop):
        app.pc.disconnect()
        loop.call_later(10, future.cancel)
        future.cancel()
    if hasattr(app, "aboutToQuit"):
        getattr(app, "aboutToQuit").connect(functools.partial(close_future, future, loop))
    return loop, future


async def main():
    global app
    app = QApplication.instance()
    init_parser(app)
    set_style(app)
    loop, future = init_loop(app)

    app.config = yaml.load(open('config.yaml', 'r').read(), yaml.Loader)
    app.pc = PlaylistClient()

    app.w = GigPanelWindow()
    app.w.show()
    gp = app.w.centralWidget()

    oc = GigPanelOSCClient(gp, (lambda c: (c['addr'], c['port']))(app.config['oscClient']))
    await app.pc.connect(gp, *(lambda c: (c['addr'], c['secure']))(app.config['webClient']))
    app.songs = await app.pc.get_db()
    pl = await app.pc.get_playlist()

    gp.loadSongs(app.songs)
    gp.playlist.load(pl)

    try:
        oc.start()
        asyncio.ensure_future(app.pc.get_messages())
        await future
    except:
        raise
    finally:
        oc.stop()

import signal
import qasync
#from qasync import QApplication

if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    try:
        qasync.run(main())
    except asyncio.exceptions.CancelledError:
        sys.exit(0)
