import re
import yaml

from typing import Any
import os

from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton

from ..playlist import PlaylistClient
from ..song import Song, PlaylistItem, PlaylistItemId
from .localstore import resolve_local_file


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
        self._default_store = kwargs.get("defaultStore")
        self.db = yaml.load(open(self._filename, 'r').read(), yaml.Loader)

        self.songlist = {
            k: Song(
                id=k,
                name=s['name'],
                store=(s['store'] if 'store' in s else self._default_store),
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
                # 'path' and 'pattern' are optional in the store config (e.g. the
                # 'mse' store uses only prefix + suffix); default to empty/no-op.
                path = pfx + store.get('path', '')
                suffix = store.get('suffix', '.pdf')
                for folder in sls['folders']:
                    files = sorted(os.listdir(path + folder))
                    for f in files:
                        if f.endswith(suffix):
                            song = Song(id=f, name=f[:-len(suffix)], store=sname, pattern=f'{folder}/{{name}}{suffix}')
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

    def resolve_song_file(self, song: Song, horizontal: bool = False) -> None:
        """Resolve ``song.file`` from the local {prefix, suffix} config.

        LPC stores are plain PDF collections; songs discovered by the folder
        scan carry their own per-song pattern ('folder/{name}{suffix}'), so
        resolution is: format the pattern with the song name, prepend the
        store prefix, and check existence. A direct prefix+name fallback
        covers explicit songlist entries that omit a pattern. Orientation
        is ignored (LPC sheets have no -L/-P variants).
        """
        song.file = resolve_local_file(song, self._stores, self._prefixes, self._default_store)

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

    def can_save(self) -> bool:
        return True

    def save(self) -> None:
        """Store the current playlist back into the YAML db file.

        Only the top-level ``playlists:`` section is rewritten; the rest of the
        file (comments, songlist with duplicate keys, ...) is kept verbatim.
        """
        pkey = next(iter(self.db['playlists']))
        self.db['playlists'][pkey]['songs'] = {
            p: {'id': v.id, 'song_id': v.song.id} for p, v in self.playlist.items()
        }
        section = yaml.dump(
            {'playlists': self.db['playlists']},
            allow_unicode=True, sort_keys=False, default_flow_style=None,
        )

        with open(self._filename, 'r') as f:
            lines = f.read().splitlines(keepends=True)

        top_key = re.compile(r'^[^\s#]')
        start = next((i for i, ln in enumerate(lines) if re.match(r'^playlists\s*:', ln)), None)
        if start is None:
            if lines and not lines[-1].endswith('\n'):
                lines[-1] += '\n'
            start = end = len(lines)
            section = '\n' + section
        else:
            end = next((i for i in range(start + 1, len(lines)) if top_key.match(lines[i])), len(lines))
            # keep trailing blank lines / column-0 comments that precede the next key
            while end > start + 1 and (not lines[end - 1].strip() or lines[end - 1].startswith('#')):
                end -= 1

        content = ''.join(lines[:start]) + section + ''.join(lines[end:])
        tmp = self._filename + '.tmp'
        with open(tmp, 'w') as f:
            f.write(content)
        os.replace(tmp, self._filename)

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

    def playlist_item_move(self, si: PlaylistItemId, pos: int) -> None:
        """Move playlist item ``si`` by ``pos`` places (negative = up)."""
        keys = list(self.playlist.keys())
        if si not in keys:
            return
        old = keys.index(si)
        new = max(0, min(len(keys) - 1, old + pos))
        if new == old:
            return
        keys.insert(new, keys.pop(old))

        items = {k: self.playlist[k] for k in keys}
        self.playlist.clear()  # keep the same dict object (shared with self.playlists[0])
        for i, (k, v) in enumerate(items.items()):
            v.pos = i
            self.playlist[k] = v
        for cb in self._cbs:
            cb.pe_update_playlist(list(self.playlist.values()))

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
