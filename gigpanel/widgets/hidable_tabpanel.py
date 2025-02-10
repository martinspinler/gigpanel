from PyQt5.QtWidgets import QWidget, QGridLayout, QSizePolicy, QScrollArea, QAbstractScrollArea, QTabBar

from PyQt5.QtCore import QPropertyAnimation, QParallelAnimationGroup


class HidableTabWidget(QScrollArea):
    def __init__(self, widget) -> None:
        super().__init__()

        contentArea = self
        contentArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        #contentArea.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        contentArea.setMaximumHeight(0)
        contentArea.setMinimumHeight(0)
        contentArea.setWidget(widget)

        contentArea.setSizeAdjustPolicy(QAbstractScrollArea.AdjustToContents)
        contentArea.setWidgetResizable(True)

        toggleAnimation = QParallelAnimationGroup()
        toggleAnimation.addAnimation(QPropertyAnimation(contentArea, b"maximumHeight"))

        self.contentArea = contentArea
        self.toggleAnimation = toggleAnimation


class HidableTabPanel(QWidget):
    def __init__(self, title="") -> None:
        QWidget.__init__(self)

        tabBar = QTabBar()

        mainLayout = QGridLayout()
        mainLayout.setVerticalSpacing(0)
        mainLayout.setContentsMargins(0, 0, 0, 0)
        mainLayout.addWidget(tabBar, 0, 0, 1, 2)

        self.setLayout(mainLayout)
        self.tb = tabBar

        self.ci = 0
        self.content = []

        tabBar.currentChanged.connect(self.on_tab_changed)

    def addTab(self, name, widget) -> None:
        self.tb.addTab(name)
        w = HidableTabWidget(widget)

        self.content.append(w)
        self.layout().addWidget(w, len(self.content), 0, 1, 2)

        if len(self.content) == 1:
            self.on_tab_changed(0)

    def _animate(self, animation, startHeight, endHeight) -> None:
        animationDuration = 100
        for i in range(animation.animationCount() - 1):
            SectionAnimation = animation.animationAt(i)
            SectionAnimation.setDuration(animationDuration)
            SectionAnimation.setStartValue(startHeight)
            SectionAnimation.setEndValue(endHeight)

        contentAnimation = animation.animationAt(animation.animationCount() - 1)
        contentAnimation.setDuration(animationDuration)
        contentAnimation.setStartValue(startHeight)
        contentAnimation.setEndValue(endHeight)
        animation.start()

    def on_tab_changed(self, index) -> None:
        if not self.content:
            return

        wstart = self.content[self.ci]
        wend = self.content[index]

        self.ci = index

        h = wend.sizeHint().height()
        self._animate(wstart.toggleAnimation, wstart.maximumHeight(), 0)
        self._animate(wend.toggleAnimation, 0, h)
