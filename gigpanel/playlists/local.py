import yaml

from typing import Any
import os

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton

from ..playlist import PlaylistClient
from ..song import Song, PlaylistItem, PlaylistItemId


class ConfigDialog(QDialog):
    def __init__(self, lpc: "LocalPlaylistClient") -> None:
        super().__init__()
        self.lpc = lpc

        self.setModal(True)

        h = QHBoxLayout()
        self.setLayout(h)

        v = QVBoxLayout()
        h.addLayout(v)
        btn = QPushButton("Save")
        btn.clicked.connect(lambda ch: self.lpc.save())
        v.addWidget(btn)


class LocalPlaylistClient(PlaylistClient):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._filename: str = kwargs["dbpath"]
        self._stores = kwargs["stores"]
        self._prefixes = kwargs["prefixes"]
        defstore = kwargs.get("defaultStore")
        self.db = yaml.load(open(self._filename, 'r').read(), yaml.Loader)

        self.songlist = {
            k: Song(
                id=k,
                name=s['name'],
                store=(s['store'] if 'store' in s else defstore),
                filename=s.get('filename'),
                pages=[p-1 for p in s['pages']] if 'pages' in s else None,
            ) for k, s in self.db['songlist'].items()
        }

        slss = self.db.get("songlist_scan")
        if slss:
            for sls in slss:
                sname = sls['store']
                store = self._stores[sname]
                pfx = self._prefixes[store['prefix']]
                path = pfx + store['path']
                for folder in sls['folders']:
                    files = os.listdir(path + folder)
                    for f in files:
                        if f.endswith(store['suffix']):
                            song = Song(id=f, name=f[:-len(store['suffix'])], store=sname, pattern=f'{folder}/{{name}}.pdf')
                            self.songlist.update({f: song})

        self.playlists = [
            {pid: PlaylistItem(pid, self.songlist[pi['song_id'] if isinstance(pi, dict) else pi], i) for i, (pid, pi) in enumerate(pv['songs'].items())}
            for pk, pv in self.db['playlists'].items()
        ]

        self.playlist = self.playlists[0]
        self.currentPliId: PlaylistItemId | None = None
        self.songs = self.songlist

        bm = self.db.get("bookmarks")
        if bm is not None:
            self.bookmarks = {k: (self.playlist[v] if v in self.playlist else None) for k, v in bm.items() if not k.startswith("_")}

    def show_config(self) -> None:
        ConfigDialog(self).exec_()

    @classmethod
    def to_yaml(cls, dumper: yaml.Dumper, data: Any) -> Any:
        node = data.__dict__.copy()
        exclude = ['played', 'filename', '_pattern']
        for i in data.__dict__:
            if node[i] is None or i in exclude:
                del node[i]
        return node

    async def run(self) -> None:
        await self.get_songlist()
        await self.get_playlist()

    def save(self) -> None:
        with open(self._filename, 'w') as outfile:
            self.db['playlists'][1]['songs'] = {p: {'id': v.id, 'song_id': v.song.id} for p, v in self.playlist.items()}
            yaml.dump(self.db, outfile, allow_unicode=True)

    def disconnect(self) -> None:
        pass

    def playlist_item_add(self, song: Song) -> None:
        pid = 0
        while pid in self.playlist:
            pid += 1

        self.playlist.update({pid: PlaylistItem(pid, song, len(self.playlist))})
        for cb in self._cbs:
            cb.pe_update_playlist(list(self.playlist.values()))

    def playlist_item_del(self, si: PlaylistItemId) -> None:
        del self.playlist[si]
        for cb in self._cbs:
            cb.pe_update_playlist(list(self.playlist.values()))

    #def playlist_item_move(self, si, pos) -> None:
    #    pass

    def playlist_item_play(self, id: PlaylistItemId | None = None, off: int | None = None) -> None:
        self.playlist_item_set(id, off)

    def playlist_item_set(self, id: PlaylistItemId | None = None, off: int | None = None) -> None:
        pid = self.currentPliId if id is None else id
        keys = list(self.playlist.keys())

        pid = keys[0] if pid not in keys else pid
        pindex = keys.index(pid)

        if off is not None:
            pindex += off
            if pindex < 0:
                pindex = 0
            elif pindex >= len(self.playlist):
                pindex = len(self.playlist) - 1
        pid = keys[pindex]

        if self.currentPliId != pid:
            self.currentPliId = pid
            for cb in self._cbs:
                cb.pe_play(self.playlist[pid])

    async def get_playlist(self) -> None:
        data = self.playlists[0]
        for cb in self._cbs:
            cb.pe_update_playlist(list(data.values()))

    async def get_songlist(self) -> None:
        for cb in self._cbs:
            cb.pe_update_songlist(self.songlist)
