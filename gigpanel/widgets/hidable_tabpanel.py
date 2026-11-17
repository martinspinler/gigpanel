from PyQt5.QtWidgets import QWidget, QVBoxLayout, QSizePolicy, QTabBar, QWIDGETSIZE_MAX
from PyQt5.QtCore import QVariantAnimation, QAbstractAnimation


class _PageArea(QWidget):
    """Holds the pages, only the current one is visible.

    Hidden widgets don't take part in a layout, so the size hint of this
    area is always the live size hint of the current page. With a Fixed
    vertical policy the panel therefore sits at the lowest height the page
    needs and follows it when the page content changes.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)


class HidableTabPanel(QWidget):
    """Tab bar with pages below it; switching tabs animates the height."""

    ANIMATION_MS = 100

    def __init__(self, title: str = "") -> None:
        QWidget.__init__(self)
        # Fixed vertically, so the dock can't be dragged taller than the page.
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Fixed)

        self.tb = QTabBar()
        self.area = _PageArea()
        self.pages: list[QWidget] = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.tb)
        layout.addWidget(self.area)

        # One animation for all switches: a new switch just restarts it from
        # the current height, so quick switching can't leave stale state.
        self.anim = QVariantAnimation(self)
        self.anim.setDuration(self.ANIMATION_MS)
        self.anim.valueChanged.connect(lambda h: self.area.setFixedHeight(int(h)))
        self.anim.finished.connect(self._release_height)

        self.tb.currentChanged.connect(self.on_tab_changed)

    def addTab(self, name: str, widget: QWidget) -> None:
        self.pages.append(widget)
        self.area.layout().addWidget(widget)
        widget.setVisible(len(self.pages) - 1 == self.tb.currentIndex() or not self.tb.count())
        self.tb.addTab(name)

    def _release_height(self) -> None:
        # Back to layout-driven height (the current page's size hint).
        self.area.setMinimumHeight(0)
        self.area.setMaximumHeight(QWIDGETSIZE_MAX)

    def on_tab_changed(self, index: int) -> None:
        if not (0 <= index < len(self.pages)):
            return

        start = self.area.height()
        self.anim.stop()
        for i, page in enumerate(self.pages):
            page.setVisible(i == index)
        end = self.area.sizeHint().height()

        if not self.isVisible() or start == end:
            self._release_height()
            return

        # Pin the current height first so the page swap doesn't jump.
        self.area.setFixedHeight(start)
        self.anim.setStartValue(start)
        self.anim.setEndValue(end)
        self.anim.start(QAbstractAnimation.KeepWhenStopped)
