from typing import Any, Optional

from .song import Song, Songlist, Playlist, PlaylistItem


class PlaylistEventListener():
    def pe_update_playlist(self, data: Playlist) -> None:
        pass

    def pe_update_songlist(self, songlist: Songlist) -> None:
        pass

    def pe_add(self, pi: PlaylistItem) -> None:
        pass

    def pe_del(self, pi: PlaylistItem) -> None:
        pass

    def pe_play(self, pi: PlaylistItem) -> None:
        pass


class PlaylistClient():
    def __init__(self, **kwargs: Any) -> None:
        self._cbs: list[PlaylistEventListener] = []
        self.bookmarks: dict[str, PlaylistItem | None] = {}

    def show_config(self):
        pass

    def add_callback(self, cb: PlaylistEventListener) -> None:
        self._cbs.append(cb)

    async def connect(self) -> None:
        pass

    async def get_songlist(self) -> None:
        pass

    async def get_playlist(self) -> None:
        pass

    def disconnect(self) -> None:
        pass

    def playlist_item_add(self, si: Song) -> None:
        pass

    def playlist_item_del(self, si: int) -> None:
        pass

    def playlist_item_move(self, si: int, pos: int) -> None:
        pass

    def playlist_item_set(self, id: Optional[int] = None, off: int | None = None) -> None:
        pass

    def playlist_item_play(self, id: Optional[int] = None, off: int | None = None) -> None:
        pass

    async def run(self) -> None:
        pass
