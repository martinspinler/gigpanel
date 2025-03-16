from typing import Callable, Any

import mido

from .song import Song
from .app import Application
from .widgets import DocumentWidget, DocumentWidgetScrollArea
from .widgets import PlaylistWidget
from .widgets import HidableTabPanel, TabTempoWidget, TempoWidget

from PyQt5.QtWidgets import QWidget, QMainWindow, QVBoxLayout, QStackedLayout, QDockWidget
from PyQt5.QtCore import Qt, QFile, QPoint, QSize
from PyQt5.QtGui import QCloseEvent

from PyQt5.QtCore import QSettings

from midibox.widget import MidiboxQuickWidget

from .playlist import PlaylistEventListener
from .song import Songlist


def set_style(app: Application) -> None:
    def style_fs(w: int, h: int) -> str:
        ws = f"min-width:{w}px;max-width:{w}px;" if w is not None else ""
        hs = f"min-height:{h}px;max-height:{h}px;" if h is not None else ""
        return ws + hs

    def style_fs2(w: int, h: int) -> str:
        ws = f"max-width:{w}px;" if w is not None else ""
        hs = f"max-height:{h}px;" if h is not None else ""
        return ws + hs

    style = ""

    ac = app.appconfig
    r = app.qapp.screens()[0].geometry()
    ac.horizontal = r.width() > r.height()

    if ac.args.fullscreen:
        font_size = 48
        #doc_w, doc_h = int(1080-240), int(1920)
        #doc_w, doc_h = int(1080), int(1920-240)
        if ac.horizontal:
            doc_w, doc_h = r.width() - 140, r.height()
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
        doc_w, doc_h = int(1080 / 3), int(1920 / 3)
        #doc_w, doc_h = int(1080/3), int(1920/3)
        #win_w, win_h = int(1920/2), int(1080/2)

        style = f"""
            DocumentWidget {{{style_fs(doc_w, doc_h)} border-color:red; border-width:2px; border-style:solid;}}
            """

    style += " QPushButton#tempoButton{background-color: yellow; font: 64px;}"
    style += " QPushButton#tempoButton1{background-color: yellow; font: 64px;}"
    style += " QPushButton#tempoButton:checked{background-color: blue;}"
    style += " QPushButton#tempoButton1:checked{background-color: red;}"
    app.qapp.setStyleSheet(style)


def song_update_path(song: Song, app: Application) -> None:
    st = song.store if song.store is not None else app.config['defaultStore']
    store = app.config['stores'][st]

    file = song.filename

    if file:
        song.filename = app.config['prefixes'][store['prefix']] + store['path'] + file + store['suffix']

    if (song.filename is None or not QFile(song.filename).exists()) and 'pattern' in store:
        for fn in ([file] if file else []) + [song.name]:
            for instrument in ['-Piano', ' - Piano', '-Electric_Piano', ' Piano', '']:
                pattern = store['pattern'].format(name=fn, instrument=instrument)
                filename = app.config['prefixes'][store['prefix']] + pattern
                if QFile(filename).exists():
                    song.filename = filename
                    break
            else:
                continue
            break


class GigPanelWidget(PlaylistEventListener, QWidget):
    def __init__(self, wnd: "GigPanelWindow", app: Application, tempo: TempoWidget) -> None:
        QWidget.__init__(self)
        self.app = app
        self.wnd = wnd
        self.tempo = tempo

        self.ext_input_cb: list[Callable[[int], None]] = []
        self.stacked_layout = QStackedLayout()
        self.setLayout(self.stacked_layout)
        self.stacked_layout.setStackingMode(QStackedLayout.StackAll)

        self.stacked_layout.setAlignment(Qt.AlignBottom | Qt.AlignLeft)

        layout = QVBoxLayout()
        w = QWidget()
        w.setLayout(layout)
        self.stacked_layout.setCurrentIndex(0)

        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)

        self.document = DocumentWidget(app.appconfig)
        sa = DocumentWidgetScrollArea(self.document)

        self.stacked_layout.addWidget(sa)

        v = QVBoxLayout()
        layout.addLayout(v)

        self.stacked_layout.setCurrentIndex(1)
        self.playlist = PlaylistWidget(self.wnd, self, app)
        app.pc.add_callback(self.playlist)

        self.stacked_layout.setCurrentIndex(0)

        self.songs: dict[int, Song] = {} # TODO: Is key really int?

    def loadSong(self, song: Song) -> None:
        if song.filename:
            self.document.loadSong(song)
        if song.bpm:
            self.tempo.setTempo(song.bpm)

        bp = self.wnd.tab_tempo.btn_preset
        qbox = self.wnd.mbview.qmidibox
        mpresets = [k for k, v in qbox._presets.items() if v.label == song.name]
        dplabel = self.app.config.get('midibox', {}).get('default-preset', None)
        dpresets = [k for k, v in qbox._presets.items() if v.label == dplabel]

        if mpresets:
            bp.setEnabled(True)
            bp.setText("Preset (S)")
            bp.clicked.connect(lambda x: self.setPreset(mpresets[0]))
        elif dpresets:
            bp.setEnabled(True)
            bp.setText("Preset (D)")
            bp.clicked.connect(lambda x: self.setPreset(dpresets[0]))
        else:
            bp.setEnabled(False)
            bp.setText("Preset (-)")
            bp.clicked.connect(lambda x: None)

    def setPreset(self, p: int) -> None:
        qbox = self.wnd.mbview.qmidibox
        qbox.loadPreset(p)

    def loadSongs(self, songs: Songlist) -> None:
        self.songs = songs
        for song in songs.values():
            song_update_path(song, self.app)

    def pe_update_songlist(self, songlist: Songlist) -> None:
        self.loadSongs(songlist)

    def storeDb(self) -> None:
        pass
#        for song in self.db["Songs"]:
#            if 'filename' in song:
#                del song['filename']
#
#        p = []
# #        for i in self.playlist.playlist.findItems("*", Qt.MatchWildcard):
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
    def __init__(self, pcConfig: dict[str, Any], app: Application) -> None:
        set_style(app)

        QMainWindow.__init__(self)
        self.setWindowTitle('Gig panel')
        self.app = app

        self.tab_tempo = TabTempoWidget()
        self.gp = GigPanelWidget(self, app, self.tab_tempo.tempo)
        self.setCentralWidget(self.gp)

        self.gp.document.setClickCallback(self.onDocumentClick)

        self.midibox = app.midibox
        view = MidiboxQuickWidget(
            app.qapp, self.midibox,
            **dict({'playlist_url': pcConfig['url']} if pcConfig.get('url') else {}),
            **dict({'config': app.midibox_widget_cfg} if app.midibox_widget_cfg else {}),
        )
        app.pc.add_callback(self.gp)

        #app.qapp.aboutToQuit.connect(e.deleteLater)

        self.midibox._callbacks.append(self.midicb)
        app.mbview = view
        self.mbview = view

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

        ac = app.appconfig
        if ac.args.fullscreen:
            self.setWindowState(Qt.WindowFullScreen)

        self.tab_tempo.btn_next.clicked.connect(lambda x: app.pc.playlist_item_set(off=+1))

    def onDocumentClick(self, pos: QPoint, size: QSize) -> bool:
        visible = self.dwIsVisible()
        if visible or pos.y() > int(size.height() * 0.9):
            self.dwSetVisible(not visible, 2 if pos.x() > self.width() // 2 else 1)
            return True
        else:
            return False

    def midicb(self, msg: mido.Message) -> None:
        if msg.type == 'control_change':
            if msg.is_cc(16) and msg.value > 64:
                self.gp.playlist.gp.document.prev_page()
            if msg.is_cc(17) and msg.value > 64:
                self.gp.playlist.gp.document.next_page()
            if msg.is_cc(18) and msg.value > 64:
                self.mbview.qmidibox.transpositionExtra = not self.mbview.qmidibox.transpositionExtra

    def closeEvent(self, event: QCloseEvent) -> None:
        settings = QSettings("cz.spinler", "gigpanel")
        if not self.app.appconfig.args.fullscreen:
            settings.setValue("geometry", self.saveGeometry())
        #settings.setValue("windowState", self.saveState())
        super().closeEvent(event)

    def dwSetVisible(self, v: bool, index: int = 1) -> None:
        self.hw.tb.setCurrentIndex(index if v else 0)

    def dwIsVisible(self) -> bool:
        return self.hw.tb.currentIndex() > 0
