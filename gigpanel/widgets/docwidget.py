#!/usr/bin/python3
import json
from typing import Optional, Callable

from PyQt5.QtWidgets import QLabel, QScrollArea, QAbstractScrollArea
from PyQt5.QtGui import QImage, QPixmap, QPainter, QMouseEvent, QResizeEvent
from PyQt5.QtCore import Qt, QPoint, QRect, QSize


from ..song import Song, PlaylistItem
from ..appconfig import AppConfig

import popplerqt5

try:
    from .utils import get_bounding_box
except Exception:
    def get_bounding_box(img: QImage) -> QRect:
        return QRect(0, 0, 0, 0)


class DocumentWidget(QLabel):
    MODE_NORMAL = 0
    MODE_SET_SPLITPOINTS = 1
    MODE_SET_BOUNDING_BOX = 2

    def __init__(self, app: AppConfig) -> None:
        QLabel.__init__(self)
        self.setObjectName("DocumentWidget")

        self.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.document: Optional[popplerqt5.Poppler.Document] = None
        self.page: Optional[popplerqt5.Poppler.Page] = None
        self.page_index = 0
        self.page_splitpoints: list[int] = []
        self.page_splitindex = 0
        self.bb: list[int] = []
        self.song: Optional[Song] = None

        self.mode = self.MODE_NORMAL
        if app.args.edit_splitpoints:
            self.mode = self.MODE_SET_SPLITPOINTS
        elif app.args.edit_bounding_box:
            self.mode = self.MODE_SET_BOUNDING_BOX

        self._click_callback: Optional[Callable[[QPoint, QSize], bool]] = None

    def loadSong(self, pli: PlaylistItem) -> None:
        self.pli = pli
        song = pli.song

        doc = popplerqt5.Poppler.Document
        self.sect = 0
        self.song = song

        self.page = None
        self.page_splitindex = 0
        self.document = doc.load(song.filename)
        if not self.document:
            return

        hints = doc.Antialiasing | doc.TextAntialiasing | doc.ThinLineShape | doc.TextSlightHinting
        self.document.setRenderHint(hints)
        #self.document.setRenderBackend(doc.SplashBackend)
        #self.document.setRenderBackend(doc.ArthurBackend)
        pg = song.pages[self.pli.pages[0] if self.pli.pages is not None else 0] if song.pages else 0
        self.loadPage(pg)

        #if 'Scenes' in song and song['Scenes']:
        #    if 'Registration' in song['Scenes'][0]:
        #        pass
        #        #midibox.setRegistration(song['Scenes'][0]['Registration'])

    def mouseMoveEvent(self, e: QMouseEvent) -> None:
        x = int(e.localPos().x())
        y = int(e.localPos().y())
        if self.mode == self.MODE_SET_BOUNDING_BOX and len(self.bb) == 2:
            self.bb += [x, y]
            self.loadPage(self.page_index)
            self.bb = self.bb[0:2]
            #self.update()
            pass

    def mouseReleaseEvent(self, e: QMouseEvent) -> None:
        if self.page is None:
            return

        #x = int(e.localPos().x())
        #y = int(e.localPos().y())
        #if self.mode == self.MODE_SET_BOUNDING_BOX:
        #    self.bb += [x, y]

        #    if 'Pages' not in self.song:
        #        self.song['Pages'] = []

        #    #if self.page_index >= len(self.song['Pages']):
        #    #print(len(self.song['Pages']))
        #    #print(max(0,  self.page_index + 1 - len(self.song['Pages'])))
        #    self.song['Pages'] += [{} for i in range(max(0, self.page_index + 1 - len(self.song['Pages'])))]

        #    ps = self.page.pageSize()
        #    s = [int(x * (ps.width() / self.width())) for x in self.bb]
        #    self.song['Pages'][self.page_index]['BoundingBox'] = s
        #    self.bb = []

    def mousePressEvent(self, e: QMouseEvent) -> None:
        if self.page is None:
            return

        pos = e.localPos()
        x = int(pos.x())
        y = int(pos.y())
        if self.mode == self.MODE_SET_SPLITPOINTS:
            #if 'Pages' not in self.song:
            #    self.song['Pages'] = []
            #self.song['Pages'] += [{} for i in range(max(0, self.page_index + 1 - len(self.song['Pages'])))]
            #if 'Splitpoints' not in self.song['Pages'][self.page_index]:
            #    self.song['Pages'][self.page_index]['Splitpoints'] = []
            #self.song['Pages'][self.page_index]['Splitpoints'].append(y)
            self.loadPage(self.page_index)
            #self.update()
        elif self.mode == self.MODE_SET_BOUNDING_BOX:
            self.bb = [x, y]
            self.loadPage(self.page_index)
        elif self.mode == self.MODE_NORMAL:
            if self._click_callback and not self._click_callback(pos.toPoint(), self.size()):
                if pos.x() > self.width() // 2:
                    self.next_page()
                else:
                    self.prev_page()

    def loadPage(self, index: int) -> None:
        if not self.document:
            return

        page = self.document.page(index)
        if not page:
            return

        self.page_splitpoints = []
        self.page_boundingbox = None
        #if self.horizontal and 'Pages' in self.song and len(self.song['Pages']) > index:
        #    if 'Splitpoints' in self.song['Pages'][index]:
        #        self.page_splitpoints = self.song['Pages'][index]['Splitpoints']
        #        print(self.page_splitpoints)

        #if 'Pages' in self.song and len(self.song['Pages']) > index:
        #    if 'BoundingBox' in self.song['Pages'][index]:
        #        self.page_boundingbox = self.song['Pages'][index]['BoundingBox']
        #        #print(self.page_boundingbox)

        self.page = page
        self.page_index = index

        mult = 2.1
        ps = self.page.pageSize()

        sp = self.page_splitpoints
        si = self.page_splitindex
        yfrom = sp[si - 1] if len(sp) > 0 and si > 0 else 0
        yto = sp[si - 0] if len(sp) > si else ps.height() - yfrom

        if self.mode == self.MODE_SET_SPLITPOINTS:
            yfrom, yto = 0, ps.height()

        ps *= mult
        yfrom = int(yfrom * mult)
        yto = int(yto * mult)

        dpi = int(72 * mult)
        img = self.page.renderToImage(dpi, dpi, 0, yfrom, ps.width(), yto)

        if False: # and np is not None:
            rect = get_bounding_box(img).adjusted(*(lambda x: [-x, -x, x, x])(20))
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
                p.drawLine(bb[0], bb[1], bb[2], bb[1])  # T
                p.drawLine(bb[0], bb[1], bb[0], bb[3])  # L
                p.drawLine(bb[0], bb[3], bb[2], bb[3])  # B
                p.drawLine(bb[2], bb[1], bb[2], bb[3])  # R
            p.end()

        #self.show_beats(pixmap, "/home/maestro/mstest/test.json", img2)

        self.setPixmap(pixmap)

    def show_beats(self, pixmap: QPixmap, filename: str, img2: QImage) -> None:
        x = json.load(open(filename))
        measures = x['measures']
        measures = measures[16:28]

        scale = 210 / img2.width()
        p = QPainter()
        p.begin(pixmap)
        for m in measures:
            bb = m['rect']
            bb = [int(x / scale) for x in bb]
            p.drawLine(bb[0], bb[1], bb[2], bb[1])  # T
            p.drawLine(bb[0], bb[1], bb[0], bb[3])  # L
            p.drawLine(bb[0], bb[3], bb[2], bb[3])  # B
            p.drawLine(bb[2], bb[1], bb[2], bb[3])  # R
        p.end()

        pixmap.save("/home/maestro/xxx.png")

    def setClickCallback(self, cb: Optional[Callable[[QPoint, QSize], bool]]) -> None:
        self._click_callback = cb

    #def sizeHint(self):
    #    if self.page:
    #        #print("SZ", self.page.pageSize())
    #        return self.page.pageSize()
    #    return QSize()
    #    return self.outsize

    def onResize(self, re: QSize) -> None:
        self.setFixedSize(re)
        self.loadPage(self.page_index)

    def next_page(self) -> None:
        self.page_splitindex = 0
        self.loadPage(self.page_index + 1)

    def prev_page(self) -> None:
        self.page_splitindex = 0
        self.loadPage(self.page_index - 1)


class DocumentWidgetScrollArea(QScrollArea):
    def __init__(self, document: DocumentWidget) -> None:
        super().__init__()
        self.document = document
        self.setWidget(self.document)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        self.setWidgetResizable(True)

    def resizeEvent(self, ev: QResizeEvent) -> None:
        super(QScrollArea, self).resizeEvent(ev)
        self.document.onResize(self.size())
