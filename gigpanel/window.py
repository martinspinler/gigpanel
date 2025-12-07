from typing import Callable, Any

import mido

from .app import Application
from .widgets import DocumentWidget, DocumentWidgetScrollArea
from .widgets import PlaylistWidget
from .widgets import HidableTabPanel, TabTempoWidget, TempoWidget, TabBookmarksWidget

from PyQt5.QtWidgets import QWidget, QMainWindow, QVBoxLayout, QStackedLayout, QDockWidget
from PyQt5.QtCore import Qt, QFile, QPoint, QSize, QRect
from PyQt5.QtGui import QCloseEvent

from PyQt5.QtCore import QSettings

from midibox.widget import MidiboxQuickWidget

from .playlist import PlaylistEventListener
from .song import Song, Songlist, PlaylistItem


def set_style(app: Application, geometry: QRect) -> bool:
    style = []

    r = geometry
    ac = app.appconfig
    horizontal = r.width() > r.height()
    prev_horizontal = ac.horizontal if hasattr(ac, 'horizontal') else not horizontal
    ac.horizontal = horizontal

    font_size = "18pt"
    if ac.args.fullscreen:
        style.append(f"QPushButton {{font: {font_size};}}")
        style.append(f"QListWidget {{font: {font_size};}}")
        style.append("QScrollBar::vertical {min-width: 2em;}")
        style.append(f"QTabBar {{font: {font_size};}}")

    style.append(f".tempoButton{{background-color: yellow; font: {font_size};}}")
    style.append(".tempoButton:checked{background-color: blue;}")
    style.append("#tempoButton1:checked{background-color: red;}")
    app.qapp.setStyleSheet(" ".join(style))
    return prev_horizontal != horizontal


def try_song_file(song: Song, app: Application, store: Any, file: str) -> None:
    try:
        song.file = app.config['prefixes'][store['prefix']] + store['path'] + file + store['suffix']
    except Exception:
        song.file = None


def song_update_path(song: Song, app: Application) -> None:
    st = song.store if song.store is not None else app.config['defaultStore']
    store = app.config['stores'][st]
    override = app.config.get('override', {})

    file = song.filename
    if file:
        try_song_file(song, app, store, file)

    if (song.filename is None or not QFile(song.filename).exists()):
        pattern = song.pattern if song.pattern is not None else (store['pattern'] if 'pattern' in store else None)
        if pattern is not None:
            for fn in ([file] if file else []) + [song.name]:
                instrument_suffixes = ['-Piano', ' - Piano', '-Electric_Piano', ' Piano', '']
                if song.name in override:
                    if 'instrument' in override[song.name]:
                        instrument_suffixes = ["-" + override[song.name]['instrument']]

                if app.appconfig.horizontal:
                    instrument_suffixes = [x + "-L" for x in instrument_suffixes] + instrument_suffixes
                else:
                    instrument_suffixes = [x + "-P" for x in instrument_suffixes] + instrument_suffixes

                for instrument in instrument_suffixes:
                    fpattern = pattern.format(name=fn, instrument=instrument)
                    filename = app.config['prefixes'][store['prefix']] + fpattern
                    if QFile(filename).exists():
                        song.file = filename
                        break
                else:
                    continue
                break

    if song.file is None:
        try_song_file(song, app, store, song.name)


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

    def loadSong(self, pli: PlaylistItem) -> None:
        song = pli.song
        if song.file:
            self.document.loadSong(pli)
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
        QMainWindow.__init__(self)

        self.app = app
        s = self.screen()
        s.virtualGeometryChanged.connect(self.onGeometryChanged)
        set_style(self.app, s.geometry())

        self.setWindowTitle('Gig panel')

        self.tab_tempo = TabTempoWidget()
        self.gp = GigPanelWidget(self, app, self.tab_tempo.tempo)
        self.tab_bookmarks = TabBookmarksWidget(self.gp.document, app)
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
        if pcConfig.get('panel') == "bookmarks":
            hw.addTab("Bookmarks", self.tab_bookmarks)
        else:
            hw.addTab("Tempo", self.tab_tempo)
        hw.addTab("Playlist", self.gp.playlist)
        hw.addTab("Midibox", view)

        self.hw = hw

        self.dw = QDockWidget()
        self.dw.setFeatures(QDockWidget.DockWidgetVerticalTitleBar)
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

        self.tab_tempo.btn_next.clicked.connect(lambda x: app.pc.playlist_item_play(off=+1))
        self.tab_bookmarks.btn_next.clicked.connect(lambda x: app.pc.playlist_item_play(off=+1))

    def onGeometryChanged(self, geometry: QRect) -> None:
        orientation_changed = set_style(self.app, geometry)
        if orientation_changed:
            self.gp.loadSongs(self.gp.songs)

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
