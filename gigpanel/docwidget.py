#!/usr/bin/python3
from PyQt5.QtWidgets import QFileDialog, QDialog, QApplication, QWidget, QMainWindow, QVBoxLayout, QHBoxLayout, QFormLayout, QComboBox, QPushButton, QInputDialog, QLineEdit, QLabel, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QTreeWidget, QTreeWidgetItem, QSizePolicy, QMenu, QAction, QFrame, QLabel, QAbstractItemView, QMessageBox, QStackedLayout, QListWidget, QListWidgetItem, QFileIconProvider, QGridLayout, QSizePolicy, QDockWidget, QScrollArea, QAbstractScrollArea
from PyQt5.QtGui import QFontMetrics, QFont, QImage, QPixmap, QIcon, QPaintEvent, QPainter, QPainterPath, QColor, QPalette, QBrush, QPen, QResizeEvent
from PyQt5.QtCore import Qt, QSize, QPoint, QUrl, QFile, QTimer, QItemSelectionModel, QRect, QRegExp, QIODevice, QCommandLineParser, QCommandLineOption

import popplerqt5
import numpy as np

class DocumentWidget(QLabel):
    MODE_NORMAL = 0
    MODE_SET_SPLITPOINTS = 1
    MODE_SET_BOUNDING_BOX = 2

    def __init__(self, gp, app):
        QLabel.__init__(self, gp)
        self.setObjectName("DocumentWidget")
        self.gp = gp
        
        self.setAlignment(Qt.AlignTop | Qt.AlignLeft);
        self.document = None
        self.page = None
        self.page_index = 0
        self.page_splitpoints = []
        self.page_splitindex = 0
        self.bb = []

        self.mode = self.MODE_NORMAL
        self.horizontal = app.horizontal
        if app.parser.isSet(app.option_edit_splitpoints):
            self.mode = self.MODE_SET_SPLITPOINTS
        elif app.parser.isSet(app.option_edit_bounding_box):
            self.mode = self.MODE_SET_BOUNDING_BOX

        #self.resizeEvent.connect(self.on_resize)

    def loadSong(self, song):
        doc = popplerqt5.Poppler.Document
        self.sect = 0
        self.song = song

        self.page = None
        self.page_splitindex = 0
        self.document = doc.load(song['filename'])
        if not self.document:
            return

        self.document.setRenderHint(doc.Antialiasing |
                doc.TextAntialiasing | doc.ThinLineShape | doc.TextSlightHinting )
        #self.document.setRenderBackend(doc.SplashBackend)
        #self.document.setRenderBackend(doc.ArthurBackend)
        self.loadPage(0)

        if 'Scenes' in song and song['Scenes']:
            if 'Registration' in song['Scenes'][0]:
                pass
                #midibox.setRegistration(song['Scenes'][0]['Registration'])

    def mouseMoveEvent(self, e):
        x = int(e.localPos().x())
        y = int(e.localPos().y())
        if self.mode == self.MODE_SET_BOUNDING_BOX and len(self.bb) == 2:
            self.bb += [x, y]
            self.loadPage(self.page_index)
            self.bb = self.bb[0:2]
            #self.update()
            pass

    def mouseReleaseEvent(self, e):
        x = int(e.localPos().x())
        y = int(e.localPos().y())
        if self.mode == self.MODE_SET_BOUNDING_BOX:
            self.bb += [x, y]

            if 'Pages' not in self.song:
                self.song['Pages'] = []

            #if self.page_index >= len(self.song['Pages']):
            #print(len(self.song['Pages']))
            #print(max(0,  self.page_index + 1 - len(self.song['Pages'])))
            self.song['Pages'] += [{} for i in range(max(0, self.page_index + 1 - len(self.song['Pages'])))]

            ps = self.page.pageSize()
            s = [int(x * (ps.width() / self.width())) for x in self.bb]
            sp = self.song['Pages'][self.page_index]['BoundingBox'] = s
            self.bb = []

    def mousePressEvent(self, e):
        x = int(e.localPos().x())
        y = int(e.localPos().y())
        if self.mode == self.MODE_SET_SPLITPOINTS:
            if 'Pages' not in self.song:
                self.song['Pages'] = []
            self.song['Pages'] += [{} for i in range(max(0, self.page_index + 1 - len(self.song['Pages'])))]
            if 'Splitpoints' not in self.song['Pages'][self.page_index]:
                self.song['Pages'][self.page_index]['Splitpoints'] = []
            sp = self.song['Pages'][self.page_index]['Splitpoints'].append(y)
            self.loadPage(self.page_index)
            #self.update()
        elif self.mode == self.MODE_SET_BOUNDING_BOX:
            self.bb = [x, y]
            self.loadPage(self.page_index)
        elif self.mode == self.MODE_NORMAL:
            if e.localPos().y() > int(self.height() * 0.9):
                self.gp.wnd.dw.setVisible(not self.gp.wnd.dw.isVisible())
            else:
                if e.localPos().x() > self.width() // 2:
                    self.next_page()
                else:
                    self.prev_page()

    def loadPage(self, index):
      #with CodeTimer():
        if not self.document:
            return

        page = self.document.page(index)
        if not page:
            return

        self.page_splitpoints = []
        self.page_boundingbox = None
        if self.horizontal and 'Pages' in self.song and len(self.song['Pages']) > index:
            if 'Splitpoints' in self.song['Pages'][index]:
                self.page_splitpoints = self.song['Pages'][index]['Splitpoints']
                print(self.page_splitpoints)

        if 'Pages' in self.song and len(self.song['Pages']) > index:
            if 'BoundingBox' in self.song['Pages'][index]:
                self.page_boundingbox = self.song['Pages'][index]['BoundingBox']
                #print(self.page_boundingbox)

        self.page = page
        self.page_index = index

        mult = 2.1
        ps = self.page.pageSize()

        yfrom = self.page_splitpoints[self.page_splitindex - 1] if len(self.page_splitpoints) > 0 and self.page_splitindex > 0 else 0
        yto   = self.page_splitpoints[self.page_splitindex]     if len(self.page_splitpoints) > self.page_splitindex else ps.height() - yfrom

        if self.mode == self.MODE_SET_SPLITPOINTS:
            yfrom, yto = 0, ps.height()

        ps *= mult
        yfrom = int(yfrom * mult)
        yto = int(yto * mult)

        dpi = int(72 * mult)
        img = self.page.renderToImage(dpi, dpi, 0, yfrom, ps.width(), yto)

        if False:
            rect = self.get_bounding_box(img).adjusted(*(lambda x: [-x, -x, x, x])(20))
            img = img.copy(rect)
        elif self.page_boundingbox and self.mode == self.MODE_NORMAL:
            p1 = QPoint(*self.page_boundingbox[0:2])
            p2 = QPoint(*self.page_boundingbox[2:4])
            rect = QRect(p1 * mult, p2 * mult)
            img = img.copy(rect)

        img2 = img.scaled(self.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pixmap = QPixmap.fromImage(img2)

        if self.mode == self.MODE_SET_SPLITPOINTS:
            p = QPainter(pixmap)
            for i in self.page_splitpoints:
                p.drawLine(0, i, ps.width(), i)
            p.end()
        elif self.mode == self.MODE_SET_BOUNDING_BOX:
            p = QPainter(pixmap)
            if self.bb:
                bb = self.bb
            elif self.page_boundingbox:
                bb = [int(x) for x in self.page_boundingbox]
            else:
                bb = []

            if len(bb) == 2:
                p.drawLine(bb[0], bb[1], ps.width() - bb[0], bb[1])
                p.drawLine(bb[0], bb[1], bb[0], ps.height() - bb[1])
            elif len(bb) == 4:
                p.drawLine(bb[0], bb[1], bb[2], bb[1]) #T
                p.drawLine(bb[0], bb[1], bb[0], bb[3]) #L
                p.drawLine(bb[0], bb[3], bb[2], bb[3]) #B
                p.drawLine(bb[2], bb[1], bb[2], bb[3]) #R
            p.end()


        self.setPixmap(pixmap)

    #def sizeHint(self):
    #    if self.page:
    #        #print("SZ", self.page.pageSize())
    #        return self.page.pageSize()
    #    return QSize()
    #    return self.outsize

    def get_bounding_box(self, img):
        def find_nonwhite_row(array, backward):
            r = (lambda x: reversed(x) if backward else x)(range(array.shape[0]))
            for l in r:
                if np.mean(array[l]) < 250:
                    return l
            return r.stop

        img = img.convertToFormat(QImage.Format.Format_RGB32)
        b = img.constBits()
        h, w = img.height(), img.width()
        b.setsize(h * w * 4)
        arr_row = np.array(b).reshape((h, w, 4))
        arr_col = arr_row.transpose(1, 0, 2)
        return QRect(QPoint(find_nonwhite_row(arr_col, False),
                            find_nonwhite_row(arr_row, False)),
                     QPoint(find_nonwhite_row(arr_col, True),
                            find_nonwhite_row(arr_row, True)))

    #def resizeEvent(self, re):
    #    super().resizeEvent(re)
    #    self.loadPage(self.page_index, updateG = False)

    def next_page(self):
        #if len(self.page_splitpoints) > self.page_splitindex:
        #    self.page_splitindex += 1
        #    self.loadPage(self.page_index)
        #else:
            self.page_splitindex = 0
            self.loadPage(self.page_index + 1)

    def prev_page(self):
        #if len(self.page_splitpoints) > self.page_splitindex:
            self.page_splitindex = 0
            self.loadPage(self.page_index - 1)

