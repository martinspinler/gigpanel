#!/usr/bin/python3
import os
import sys
import asyncio
import functools
import signal
import yaml
import qasync
import pathlib
import argparse

#from asyncqt import QEventLoop

os.environ['QT_STYLE_OVERRIDE'] = 'Breeze'

from PyQt5.QtCore import QCommandLineParser, QCommandLineOption
from PyQt5.QtWidgets import QApplication

import midibox.backends as mb_backends

from .window import GigPanelWindow
from .playlist import PlaylistClient


def parse_args(self):
    parser = argparse.ArgumentParser(description='Gig Panel: Push Live performance to the next level')
    parser.add_argument("-m", "--midibox", help="Midibox configuration in config file")
    parser.add_argument("-s", "--simulator", help="Use emulator", action='store_true')
    parser.add_argument("-f", "--fullscreen", help="Show in fullscreen mode", action='store_true')
    parser.add_argument("--edit_splitpoints", help="Edit splitpoints", action='store_true')
    parser.add_argument("--edit-bounding-box", help="Edit bounding box", action='store_true')
    parser.add_argument("qt", nargs='*')

    app = self
    app.parser = QCommandLineParser()
    app.parser.addHelpOption();
    args = parser.parse_args()
    app.parser.process([sys.argv[0]] + args.qt)
    return args


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
    app.args = parse_args(app)

    cfg = app.config = yaml.load(open((pathlib.Path(__file__).parent / 'config.yaml').resolve(), 'r').read(), yaml.Loader)

    # Midibox setup
    mb_cfg_node = cfg.get("midibox", {})
    mb_cfg_name = mb_cfg_node.get(app.args.midibox or "default-configuration")
    mb_cfg = mb_cfg_node.get("configurations", {}).get(mb_cfg_name, {})
    if (wcf := mb_cfg.get("widget-config-file")):
        app.midibox_widget_cfg = yaml.load(open(wcf, 'r').read(), yaml.Loader)
    else:
        app.midibox_widget_cfg = {}

    app.midibox = mb_backends.create_midibox_from_config(mb_cfg.get('backend', mb_backends.default_backend), **mb_cfg.get('backend-params', {}))

    # Playlist setup
    cfg_pc = cfg['playlistClients'][cfg['defaultPlaylistClient']]
    gpwindow = GigPanelWindow(cfg_pc, app)
    gpwidget = gpwindow.gp

    app.pc = PlaylistClient(cfg_pc.get("url"), currentBand=cfg_pc['currentBand'])
    app.pc.add_callback(gpwidget.playlist.livelist_client_cb)

    gpwindow.tab_tempo.btn_next.clicked.connect(lambda x: app.pc.playlist_item_set(off=+1))
    #app.oc = GigPanelOSCClient(gpwidget, (lambda c: (c['addr'], c['port']))(app.config['oscClient']))

    gpwindow.show()

    try:
        app.midibox.connect()
    except Exception as e:
        print(e)

    songs = {}
    pl = {}

    loop, future = init_loop(app)
    try:
        await app.pc.connect()
        songs = await app.pc.get_db()
        pl = await app.pc.get_playlist()
    except Exception as e:
        print(e)

    gpwidget.loadSongs(songs)
    gpwidget.playlist.load(pl)

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
