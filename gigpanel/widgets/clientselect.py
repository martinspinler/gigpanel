from typing import Any, Optional

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QListWidget, QListWidgetItem, QComboBox, QPushButton, QLabel
from PyQt5.QtCore import Qt

from ..app import Application


def _instrument_names(spec: Any) -> list[str]:
    """Extract instrument names from a config value (list of names, dict keyed
    by name, or list of dicts with a name-like key)."""
    if isinstance(spec, dict):
        return [str(k) for k in spec]
    if isinstance(spec, (list, tuple)):
        names = []
        for i in spec:
            if isinstance(i, dict):
                i = next((i[k] for k in ('id', 'key', 'name') if k in i), None)
            if i is not None:
                names.append(str(i))
        return names
    return []


class PlaylistClientDialog(QDialog):
    """Pick a playlist client from ``playlistClients`` and the sheet instrument."""

    def __init__(self, parent: Any, app: Application) -> None:
        super().__init__(parent)
        self.app = app
        self.setWindowTitle("Playlist client")
        self.setModal(True)

        cfg = app.config
        self.clients: dict[str, dict[str, Any]] = cfg.get('playlistClients', {}) or {}

        self.list = QListWidget()
        for name, cpc in self.clients.items():
            label = name
            ptype = (cpc or {}).get('pc_type', 'socketiolivelist')
            if ptype == 'local':
                label += "  (local)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self.list.addItem(item)
            if name == app.pc_name:
                self.list.setCurrentItem(item)
        self.list.currentItemChanged.connect(lambda *x: self._update_instruments())
        self.list.itemActivated.connect(lambda *x: self.accept())

        self.instrument = QComboBox()
        self.instrument.setEditable(True)
        self.instrument.setInsertPolicy(QComboBox.NoInsert)

        form = QFormLayout()
        form.addRow(QLabel("Instrument"), self.instrument)

        btn_ok = QPushButton("Switch")
        btn_ok.setDefault(True)
        btn_ok.clicked.connect(self.accept)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        buttons = QHBoxLayout()
        buttons.addWidget(btn_cancel)
        buttons.addWidget(btn_ok)

        layout = QVBoxLayout()
        layout.addWidget(self.list)
        layout.addLayout(form)
        layout.addWidget(QLabel("Switching restarts the panel."))
        layout.addLayout(buttons)
        self.setLayout(layout)

        self._update_instruments()

        # Size for touch use: a good part of the panel window, not just the
        # minimal size hint (which is tiny with the large fullscreen fonts).
        self.ensurePolished()  # apply the app stylesheet fonts before measuring
        self.list.setSpacing(self.list.fontMetrics().height() // 3)
        for btn in (btn_ok, btn_cancel):
            btn.setMinimumHeight(btn.fontMetrics().height() * 2)
        if parent is not None:
            self.resize(max(self.sizeHint().width(), int(parent.width() * 0.6)),
                        max(self.sizeHint().height(), int(parent.height() * 0.7)))

    def selected_client(self) -> Optional[str]:
        item = self.list.currentItem()
        return item.data(Qt.ItemDataRole.UserRole) if item is not None else None

    def selected_instrument(self) -> Optional[str]:
        if not self.instrument.isEnabled():
            return None
        return self.instrument.currentText().strip() or None

    def _default_instrument(self, cpc: dict[str, Any]) -> Optional[str]:
        return cpc.get('sheet_store_instrument', self.app.config.get('sheet_store_instrument'))

    def _update_instruments(self) -> None:
        name = self.selected_client()
        cpc = (self.clients.get(name) or {}) if name else {}
        is_local = cpc.get('pc_type') == 'local'

        names: list[str] = []
        # Known instruments: per-client config, global config, and (for the
        # running online client) the band config fetched from the server.
        for spec in (cpc.get('instruments'), self.app.config.get('instruments')):
            names += _instrument_names(spec)
        if name == self.app.pc_name:
            client = getattr(self.app.pc, '_client', None)
            band_config = getattr(client, 'band_config', None) or {}
            if isinstance(band_config, dict):
                names += _instrument_names(band_config.get('instruments'))

        current: Optional[str]
        if name == self.app.pc_name and self.app.pc_instrument:
            current = self.app.pc_instrument
        else:
            current = self._default_instrument(cpc)
        if current:
            names.insert(0, current)

        self.instrument.clear()
        self.instrument.addItems(list(dict.fromkeys(names)))
        if current:
            self.instrument.setCurrentText(current)
        # Local playlists resolve sheets without an instrument.
        self.instrument.setEnabled(not is_local)

    def get(self) -> Optional[tuple[str, Optional[str]]]:
        if self.exec_() != QDialog.Accepted:
            return None
        name = self.selected_client()
        if name is None:
            return None
        return name, self.selected_instrument()
