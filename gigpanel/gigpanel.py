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

import window
from window import GigPanelWindow
from playlist import PlaylistClient
from gposcclient import GigPanelOSCClient

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
        #loop.call_later(0.1, future.cancel)
        future.cancel()

    if hasattr(app, "aboutToQuit"):
        getattr(app, "aboutToQuit").connect(functools.partial(close_future, future, loop))

    return loop, future


async def main():
    global app
    app = QApplication.instance()
    window.app = app

    parse_args(app)
    window.set_style(app)

    app.config = yaml.load(open((pathlib.Path(__file__).parent / 'config.yaml').resolve(), 'r').read(), yaml.Loader)
    app.w = GigPanelWindow()
    app.gp = app.w.centralWidget()
    app.pc = PlaylistClient(app.gp.playlist.livelist_client_cb, *(lambda c: (c['addr'], c['secure']))(app.config['webClient']))
    #app.oc = GigPanelOSCClient(app.gp, (lambda c: (c['addr'], c['port']))(app.config['oscClient']))

    app.w.show()
    try:
        app.midibox.connect()
    except:
        pass


    loop, future = init_loop(app)
    try:
        await app.pc.connect()
        app.songs = await app.pc.get_db()
        pl = await app.pc.get_playlist()
    except Exception as e:
        print(e)
        app.songs = {}
        pl = {}
        pl['items'] = {}
        pass

    app.gp.loadSongs(app.songs)
    app.gp.playlist.load(pl)

    try:
        #app.oc.start()
        asyncio.ensure_future(app.pc.get_messages())
        await future
    except:
        raise
    finally:
        #app.oc.stop()
        pass


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    try:
        if sys.version_info.major == 3 and sys.version_info.minor == 11:
            with qasync._set_event_loop_policy(qasync.DefaultQEventLoopPolicy()):
                runner = asyncio.runners.Runner()
                try:
                    runner.run(main())
                finally:
                    runner.close()
        else:
            qasync.run(main())
    except asyncio.exceptions.CancelledError:
        sys.exit(0)
