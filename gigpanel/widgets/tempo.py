from PyQt5.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLabel
from PyQt5.QtCore import Qt, QTimer


class TempoWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

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
            btn.setAutoFillBackground(False)
            btn.setCheckable(True)
            layout.setStretchFactor(btn, 4)
        self.setLayout(layout)

    def setTempo(self, bpm):
        if bpm:
            self.timer.start()
            self.timer.setInterval(60000 // bpm)
            self.tempoText.setText(str(bpm))
        else:
            self.timer.stop()
            self.tempoText.setText("")

    def tempoTimeout(self, *args):
        st = None
        for i in range(len(self.tempoBtns)):
            if self.tempoBtns[i].isChecked():
                st = i

        if st is None:
            self.tempoBtns[0].setChecked(True)
        else:
            self.tempoBtns[st].setChecked(False)
            self.tempoBtns[((st + 1) % len(self.tempoBtns))].setChecked(True)

class TabTempoWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.tempo = TempoWidget()

        layout = QHBoxLayout()
        layout.addWidget(self.tempo)
        layout.setStretch(0, 1)

        self.btn_next = QPushButton("Next")
        layout.addWidget(self.btn_next)

        self.setLayout(layout)
