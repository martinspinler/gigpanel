#!/usr/bin/python3
import sys
import asyncio
import functools
import signal
import yaml
import qasync
import pathlib
#from asyncqt import QEventLoop

from PyQt5.QtCore import QCommandLineParser, QCommandLineOption
from PyQt5.QtWidgets import QApplication

from .window import GigPanelWindow
from .playlist import PlaylistClient
from .gposcclient import GigPanelOSCClient


def parse_args(self):
    app = self
    app.parser = QCommandLineParser()
    app.parser.setApplicationDescription("Gig Panel");
    app.parser.addHelpOption();
    app.option_use_simulator = QCommandLineOption("s", "Use emulator")
    app.option_fullscreen = QCommandLineOption("f", "Show fullscreen")
    app.option_edit_splitpoints = QCommandLineOption("e", "Edit splitpoints")
    app.option_edit_bounding_box = QCommandLineOption("b", "Edit bounding box")
    app.parser.addOption(app.option_use_simulator)
    app.parser.addOption(app.option_fullscreen)
    app.parser.addOption(app.option_edit_splitpoints)
    app.parser.addOption(app.option_edit_bounding_box)
    app.parser.process(app);


def init_loop(app):
    loop = asyncio.get_event_loop()
    future = asyncio.Future()

    def close_future(future, loop):
        app.pc.disconnect()
        app.midibox.disconnect()
        future.cancel()

    if hasattr(app, "aboutToQuit"):
        getattr(app, "aboutToQuit").connect(functools.partial(close_future, future, loop))

    return loop, future


async def _main():
    global app
    app = QApplication.instance()
    parse_args(app)

    app.config = yaml.load(open((pathlib.Path(__file__).parent / 'config.yaml').resolve(), 'r').read(), yaml.Loader)

    pcConfig = app.config['playlistClients'][app.config['defaultPlaylistClient']]
    window = GigPanelWindow(pcConfig, app)
    gigpanel = window.gp
    app.pc = PlaylistClient(gigpanel.playlist.livelist_client_cb, *(lambda c: (c['addr'], c['secure']))(pcConfig), currentBand=pcConfig['currentBand'])

    window.tab_tempo.btn_next.clicked.connect(lambda x: app.pc.playlist_item_set(off=+1))
    #app.oc = GigPanelOSCClient(gigpanel, (lambda c: (c['addr'], c['port']))(app.config['oscClient']))

    window.show()
    try:
        app.midibox.connect()
    except Exception as e:
        print(e)

    songs = {}
    pl = {'items': {}}

    loop, future = init_loop(app)
    try:
        await app.pc.connect()
        songs = await app.pc.get_db()
        pl = await app.pc.get_playlist()
    except Exception as e:
        print(e)

    gigpanel.loadSongs(songs)
    gigpanel.playlist.load(pl)

    try:
        #app.oc.start()
        asyncio.ensure_future(app.pc.get_messages())
        await future
    except:
        raise
    finally:
        #app.oc.stop()
        pass


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    try:
        if sys.version_info.major == 3 and sys.version_info.minor == 11:
            with qasync._set_event_loop_policy(qasync.DefaultQEventLoopPolicy()):
                runner = asyncio.runners.Runner()
                try:
                    runner.run(_main())
                finally:
                    runner.close()
        else:
            qasync.run(_main())
    except asyncio.exceptions.CancelledError:
        sys.exit(0)

if __name__ == "__main__":
    main()
