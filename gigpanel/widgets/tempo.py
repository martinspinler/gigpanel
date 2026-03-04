from typing import Any, Optional
from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt, QTimer

import fluidsynth


class TempoWidget(QWidget):
    def __init__(self, btn_snd) -> None:
        QWidget.__init__(self)

        self._fs_started = False
        self.fs = None
        self.btn_snd = btn_snd

        self.note: Optional[int] = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.tempoTimeout)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)

        self.tempoBtns = []
        layout = QHBoxLayout()
        self.tempoText = QLabel()
        layout.addWidget(self.tempoText)
        layout.setStretchFactor(self.tempoText, 1)

        for i in range(4):
            btn = QPushButton(str(i + 1))
            layout.addWidget(btn)
            btn.setEnabled(False)
            self.tempoBtns.append(btn)
            btn.setObjectName("tempoButton" + ("" if i else "1"))
            btn.setProperty("class", 'tempoButton')
            btn.setAutoFillBackground(False)
            btn.setCheckable(True)
            layout.setStretchFactor(btn, 4)
        self.setLayout(layout)

    def fsStart(self):
        if not self._fs_started:
            if self.fs is None:
                self.fs = fluidsynth.Synth()
            self._fs_started = True
            self.fs.start(driver="pulseaudio")
            sfid = self.fs.sfload("/usr/share/soundfonts/FluidR3_GM.sf2")
            self.fs.program_select(9, sfid, 128, 0)

    def setTempo(self, bpm: float) -> None:
        if bpm:
            self.timer.start()
            self.timer.setInterval(int(60000 // bpm))
            self.tempoText.setText(str(bpm))
        else:
            self.timer.stop()
            self.tempoText.setText("")

    def tempoTimeout(self, *args: Any) -> None:
        st = len(self.tempoBtns) - 1
        for i in range(len(self.tempoBtns)):
            if self.tempoBtns[i].isChecked():
                st = i
        st_next = (st + 1) % len(self.tempoBtns)

        self.tempoBtns[st].setChecked(False)
        self.tempoBtns[st_next].setChecked(True)

        if self.btn_snd.isChecked():
            self.fsStart()

        if self.fs is not None:
            if self.note is not None:
                self.fs.noteoff(9, self.note)
            self.note = 34 if st_next == 0 else 33
            if self.btn_snd.isChecked():
                self.fs.noteon(9, self.note, 127)

class TabTempoWidget(QWidget):
    def __init__(self) -> None:
        QWidget.__init__(self)

        self.btn_next = QPushButton("Next")
        self.btn_preset = QPushButton("Preset")
        self.btn_preset.setEnabled(False)
        self.btn_snd = QPushButton("🕪")
        self.btn_snd.setCheckable(True)

        self.tempo = TempoWidget(self.btn_snd)

        layout = QHBoxLayout()
        layout.addWidget(self.tempo)
        layout.setStretch(0, 1)

        layout.addWidget(self.btn_snd)
        layout.addWidget(self.btn_next)
        layout.addWidget(self.btn_preset)

        self.setLayout(layout)
