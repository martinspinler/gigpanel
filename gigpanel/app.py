from typing import Any

from PyQt5.QtWidgets import QApplication

from midibox.controller import BaseMidibox
from midibox.widget import MidiboxQuickWidget

#from .window import GigPanelWindow
from .playlist import PlaylistClient
#from .widgets.tempo import TempoWidget

from .appconfig import AppConfig


class Application():
    qapp: QApplication
    pc: PlaylistClient
    midibox: BaseMidibox
    midibox_widget_cfg: Any
    config: Any
    mb_cfg: Any
    #tempo: TempoWidget
    mbview: MidiboxQuickWidget

    appconfig: AppConfig
