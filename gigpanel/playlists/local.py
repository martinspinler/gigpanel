import yaml

from typing import Any
from ..playlist import PlaylistClient
from ..song import Song, PlaylistItem


class LocalPlaylistClient(PlaylistClient):
    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._filename: str = kwargs["dbpath"]
        self.db = yaml.load(open(self._filename, 'r').read(), yaml.Loader)

        self.songlist = {k: Song(id=k, name=s['name'], store=s['store']) for k, s in self.db['songlist'].items()}
        self.playlists = [
            [PlaylistItem(pi['id'], self.songlist[pi['song_id']], i) for i, pi in enumerate(pv['songs'].values())]
            for pk, pv in self.db['playlists'].items()
        ]

        self.playlist = self.playlists[0]
        self.songs = self.songlist

    @classmethod
    def to_yaml(cls, dumper: yaml.Dumper, data: Any) -> Any:
        node = data.__dict__.copy()
        exclude = ['played', 'filename', '_pattern']
        for i in data.__dict__:
            if node[i] is None or i in exclude:
                del node[i]
        return node

    async def connect(self) -> None:
        await self.get_songlist()
        await self.get_playlist()

    def save(self) -> None:
        with open(self._filename, 'w') as outfile:
            yaml.dump(self.db, outfile)
            #yaml.dump([YamlSong.to_yaml(None, self.songs[s]) for s in self.songs], yaml_file, default_flow_style=False, allow_unicode=True)

    def disconnect(self) -> None:
        pass

    def playlist_item_add(self, song: Song) -> None:
        id = 0
        while str(id) in self.songs:
            id += 1

        # TODO
        #self.songs.update({id: Song(id=id, 'song_id': song.id}})
        #for cb in self._cbs:
        #    cb.pe_update_playlist(self.songs.values())
        self.save()

    #def playlist_item_del(self, si) -> None:
    #    del self.songs[kk]
    #    self.save()
    #    for cb in self._cbs:
    #        cb.pe_update_playlist(self.songs)

    #def playlist_item_move(self, si, pos) -> None:
    #    pass

    #def playlist_item_set(self, id=None, off=None) -> None:
    #    pass

    async def get_playlist(self) -> None:
        data = self.playlists[0]
        for cb in self._cbs:
            cb.pe_update_playlist(data)

    async def get_songlist(self) -> None:
        for cb in self._cbs:
            cb.pe_update_songlist(self.songlist)
