#!/usr/bin/python3
import os
import sys
import asyncio
import functools
import signal
import yaml
import qasync
import argparse

try:
    import platformdirs as _platformdirs
except ModuleNotFoundError:
    platformdirs = None
else:
    platformdirs = _platformdirs

#from asyncqt import QEventLoop


from PyQt5.QtCore import QCommandLineParser
from PyQt5.QtWidgets import QApplication

import midibox.backends as mb_backends

from .window import GigPanelWindow
from .playlist import PlaylistClient

os.environ['QT_STYLE_OVERRIDE'] = 'Breeze'

def parse_args(self):
    if platformdirs is not None:
        defconfig = (platformdirs.user_config_path("gigpanel") / "config.yaml").resolve()
    else:
        defconfig = "gigpanel.yaml"

    parser = argparse.ArgumentParser(description='Gig Panel: Push Live performance to the next level')
    parser.add_argument("-c", "--config", help="Configuration file", default=defconfig)
    parser.add_argument("-m", "--midibox", help="Midibox configuration in config file")
    parser.add_argument("-f", "--fullscreen", help="Show in fullscreen mode", action='store_true')
    parser.add_argument("--edit_splitpoints", help="Edit splitpoints", action='store_true')
    parser.add_argument("--edit-bounding-box", help="Edit bounding box", action='store_true')
    parser.add_argument("qt", nargs='*')

    app = self
    app.parser = QCommandLineParser()
    app.parser.addHelpOption()
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
    args = app.args = parse_args(app)

    cfg = app.config = yaml.load(open(args.config).read(), yaml.Loader)

    # Midibox setup
    mb_cfg_node = cfg.get("midibox", {})
    mb_cfg_name = args.midibox or mb_cfg_node.get("default-configuration")
    app.mb_cfg = mb_cfg = mb_cfg_node.get("configurations", {}).get(mb_cfg_name, {})
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
    use_qasync_workaround = True
    try:
        if use_qasync_workaround:
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
