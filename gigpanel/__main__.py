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

from midibox.controller import BaseMidibox
import midibox.backends as mb_backends

from .window import GigPanelWindow
from .playlists import LivelistPlaylistClient, LocalPlaylistClient

from .app import Application
from .appconfig import AppConfig


os.environ['QT_STYLE_OVERRIDE'] = 'Breeze'


def parse_args() -> argparse.Namespace:
    if platformdirs is not None:
        defconfig = (platformdirs.user_config_path("gigpanel") / "config.yaml").resolve()
    else:
        defconfig = "gigpanel.yaml"

    parser = argparse.ArgumentParser(description='Gig Panel: Push Live performance to the next level')
    parser.add_argument("-c", "--config", help="Configuration file", default=defconfig)
    parser.add_argument("-m", "--midibox", help="Midibox configuration in config file")
    parser.add_argument("-f", "--fullscreen", help="Show in fullscreen mode", action='store_true')
    parser.add_argument("-p", "--playlist_client", help="Playlist client", default=None)
    parser.add_argument("--edit_splitpoints", help="Edit splitpoints", action='store_true')
    parser.add_argument("--edit-bounding-box", help="Edit bounding box", action='store_true')
    parser.add_argument("qt", nargs='*')

    qparser = QCommandLineParser()
    qparser.addHelpOption()
    args = parser.parse_args()
    qparser.process([sys.argv[0]] + args.qt)
    return args


def init_loop(app: Application):  # type: ignore
    loop = asyncio.get_event_loop()
    future = asyncio.Future()  # type: ignore

    def close_future(future, loop) -> None:  # type: ignore
        app.pc.disconnect()
        app.midibox.disconnect()
        future.cancel()

    if hasattr(app.qapp, "aboutToQuit"):
        getattr(app.qapp, "aboutToQuit").connect(functools.partial(close_future, future, loop))

    return loop, future


def create_midibox(app: Application) -> BaseMidibox:
    ac = app.appconfig
    mb_cfg_node = app.config.get("midibox", {})
    mb_cfg_name = ac.args.midibox or mb_cfg_node.get("default-configuration")
    app.mb_cfg = mb_cfg = mb_cfg_node.get("configurations", {}).get(mb_cfg_name, {})
    wcf = mb_cfg.get("widget-config-file")
    app.midibox_widget_cfg = yaml.load(open(wcf, 'r').read(), yaml.Loader) if wcf else {}

    mb_backend = mb_cfg.get('backend', mb_backends.default_backend)
    mb_backend_params = mb_cfg.get('backend-params', {})
    return mb_backends.create_midibox_from_config(mb_backend, **mb_backend_params)


async def amain() -> None:
    app = Application()
    app.appconfig = ac = AppConfig()
    app.qapp = QApplication.instance() # type: ignore
    ac.args = parse_args()

    cfg = app.config = yaml.load(open(ac.args.config).read(), yaml.Loader)

    app.midibox = create_midibox(app)

    # Playlist setup
    defaultPC = ac.args.playlist_client or cfg['defaultPlaylistClient']
    cfg_pc = cfg['playlistClients'][defaultPC]
    playlist_client_class = {
        "livelist": LivelistPlaylistClient,
        "local": LocalPlaylistClient,
    }.get(cfg_pc.get("pc_type"), LivelistPlaylistClient)

    app.pc = playlist_client_class(**cfg_pc)

    gpwindow = GigPanelWindow(cfg_pc, app)
    gpwindow.show()

    try:
        app.midibox.connect()
    except Exception:
        raise

    try:
        await app.pc.connect()
    except Exception:
        raise

    loop, future = init_loop(app)
    try:
        #app.oc.start()
        asyncio.ensure_future(app.pc.get_messages())
        await future
    except Exception:
        raise
    finally:
        #app.oc.stop()
        pass


def main() -> None:
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    use_qasync_workaround = True
    try:
        if use_qasync_workaround:
            with qasync._set_event_loop_policy(qasync.DefaultQEventLoopPolicy()):
                runner = asyncio.runners.Runner()
                try:
                    runner.run(amain())
                finally:
                    runner.close()
        else:
            qasync.run(amain())
    except asyncio.exceptions.CancelledError:
        sys.exit(0)


if __name__ == "__main__":
    main()
