from PyQt5.QtWidgets import QFileDialog, QDialog, QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QToolButton, QPushButton, QInputDialog, QLineEdit, QLabel, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QTreeWidget, QTreeWidgetItem, QSizePolicy, QMenu, QAction, QFrame, QLabel, QAbstractItemView, QMessageBox, QStackedLayout, QListWidget, QListWidgetItem, QFileIconProvider, QGridLayout, QSizePolicy, QDockWidget, QScrollArea, QAbstractScrollArea, QLayout, QTabBar
from PyQt5.QtQuickWidgets import QQuickWidget
from PyQt5.QtGui import QFontMetrics, QFont, QImage, QPixmap, QIcon, QPaintEvent, QPainter, QPainterPath, QColor, QPalette, QBrush, QPen, QResizeEvent
from PyQt5.QtCore import Qt, QSize, QPoint, QUrl, QFile, QTimer, QItemSelectionModel, QRect, QRegExp, QIODevice, QCommandLineParser, QCommandLineOption


class TempoWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.timer = QTimer()
        self.timer.timeout.connect(self.tempoTimeout)
        self.timer.setTimerType(Qt.TimerType.PreciseTimer)

        self.tempoBtns = []
        l = QHBoxLayout()
        self.tempoText = QLabel()
        l.addWidget(self.tempoText)
        l.setStretchFactor(self.tempoText, 1)

        for i in range(4):
            btn = QPushButton(str(i+1))
            l.addWidget(btn)
            btn.setEnabled(False)
            self.tempoBtns.append(btn)
            btn.setObjectName("tempoButton" + ("" if i else "1"))
            btn.setAutoFillBackground(False)
            btn.setCheckable(True)
            l.setStretchFactor(btn, 4)
        self.setLayout(l)

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
            self.tempoBtns[((st+1) % len(self.tempoBtns))].setChecked(True)

class TabTempoWidget(QWidget):
    def __init__(self):
        QWidget.__init__(self)

        self.tempo = TempoWidget()

        l = QHBoxLayout()
        l.addWidget(self.tempo)
        l.setStretch(0, 1)

        self.btn_next = QPushButton("Next")
        l.addWidget(self.btn_next)

        self.setLayout(l)
