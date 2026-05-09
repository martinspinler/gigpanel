from typing import Any, Optional

from ..playlist import PlaylistClient
from ..song import Song, PlaylistItem, PlaylistItemId

from livelist.client import AsyncLivelistClient
from livelist.client.models import Song as LibSong, PlaylistItem as LibPlaylistItem
from livelist.songfind import build_store, find_documents, pick_best_for_instrument


def _name_candidates(song: Song) -> list[str]:
    """Ordered name candidates: prefer song.filename, fall back to song.name."""
    cands = [song.filename] if song.filename else []
    if song.name not in cands:
        cands.append(song.name)
    return cands


def _convert_song(lib_song: LibSong) -> Song:
    """Convert a library Song into the project's Song model."""
    return Song(
        id=lib_song.id,
        name=lib_song.name or "",
        store=lib_song.store,
        user_id=lib_song.user_id,
        filename=lib_song.filename,
        pages=lib_song.pages,
        bpm=lib_song.bpm,
        meta=lib_song.meta,
    )


def _convert_playlist_item(lib_item: LibPlaylistItem, song_map: dict[int, Song]) -> PlaylistItem:
    """Convert a library PlaylistItem into the project's PlaylistItem model."""
    if lib_item.song is not None:
        song = song_map.get(lib_item.song.id)
        if song is None:
            # Song not in cached songlist — convert from library model directly
            song = _convert_song(lib_item.song)
    else:
        # Break / separator item — create a placeholder song so pli.song is never None
        song = Song(id=0, name="")
    pli = PlaylistItem(
        id=lib_item.id,
        song=song,
        pos=lib_item.pos,
    )
    # Copy per-instrument page info from meta if present
    if lib_item.meta:
        pli.pages = lib_item.meta.get("pages")
        pli.current_page = lib_item.meta.get("current_page")
    return pli


class SocketioLivelistPlaylistClient(PlaylistClient):
    """Thin adapter that wraps the official AsyncLivelistClient
    behind the project's PlaylistClient interface."""

    def __init__(self, url: Optional[str] = None, band: str = '', passwd: str = '', prefix: str = '', currentBand: int = 1, **kwargs: Any) -> None:
        super().__init__()
        self._client = AsyncLivelistClient(
            url=url,
            band=band,
            key=passwd,
            default_store=kwargs.get("defaultStore"),
        )
        # Local filesystem prefix for the band's sheet store. The
        # {patterns, instruments} config comes from the server (cached in
        # self._client.band_config); the prefix is machine-specific and
        # stays here so the gigpanel resolves files on its own disk.
        self._sheet_prefix: str = kwargs.get("sheet_store_prefix", "") or ""
        # Instrument the gigpanel auto-picks (no dialog), e.g. 'pno'.
        self._sheet_instrument: Optional[str] = kwargs.get("sheet_store_instrument")
        # Converted caches (project-model objects)
        self._songlist: dict[int, Song] = {}
        self._playlist: dict[int, PlaylistItem] = {}
        # Bridge: forward events from the library's callback system into our _cbs list
        self._client.register(_BridgeCallback(self))

    def resolve_song_file(self, song: Song, horizontal: bool = False) -> None:
        """Resolve ``song.file`` via the shared finder using the server-fetched
        band config + local prefix; pick the configured instrument."""
        cfg = getattr(self._client, "band_config", None)
        if not cfg:
            song.file = None
            return
        store = build_store(cfg, self._sheet_prefix)
        orientation = 'L' if horizontal else 'P'
        documents = find_documents(_name_candidates(song), store, orientation=orientation)
        doc = pick_best_for_instrument(documents, self._sheet_instrument)
        song.file = (store.prefix + doc['path']) if doc is not None else None


    # -- Callback registration (project uses add_callback, library uses register) --

    def add_callback(self, cb: Any) -> None:
        self._cbs.append(cb)

    # -- Connection lifecycle --

    async def connect(self) -> None:
        await self._client.connect()

    def disconnect(self) -> None:
        self._client.disconnect()

    async def run(self) -> None:
        await self._client.run()

    # -- Playlist item operations (adapt project API → library API) --

    def playlist_item_add(self, si: Song) -> None:
        self._client.playlist_item_add(si.id)

    def playlist_item_del(self, si: PlaylistItemId) -> None:
        self._client.playlist_item_delete([si])

    def playlist_item_move(self, si: PlaylistItemId, pos: int) -> None:
        self._client.playlist_item_move([si], pos)

    def playlist_item_set(self, id: Optional[PlaylistItemId] = None, off: Optional[int] = None) -> None:
        pass

    def playlist_item_play(self, id: Optional[PlaylistItemId] = None, off: Optional[int] = None) -> None:
        self._client.playlist_item_play(item_id=id, off=off)

    # -- State access (project-model objects, converted from library models) --

    @property
    def songlist(self):
        return self._songlist

    @songlist.setter
    def songlist(self, value):
        self._songlist = value

    @property
    def playlist(self):
        return self._playlist

    @playlist.setter
    def playlist(self, value):
        self._playlist = value

    @property
    def currentPlaylistId(self):
        return self._client.currentPlaylistId

    @currentPlaylistId.setter
    def currentPlaylistId(self, value):
        self._client.currentPlaylistId = value

    # -- Internal: rebuild project-model caches from library state --

    def _rebuild_songlist(self) -> None:
        """Convert the library's songlist into project Song objects."""
        self._songlist = {sid: _convert_song(s) for sid, s in self._client.songlist.items()}

    def _rebuild_playlist(self) -> None:
        """Convert the library's playlist into project PlaylistItem objects."""
        self._playlist = {
            pid: _convert_playlist_item(pi, self._songlist)
            for pid, pi in self._client.playlist.items()
        }


class _BridgeCallback:
    """Forwards PlaylistCallback protocol calls from the library
    into the project's _cbs list, converting models on the fly."""

    def __init__(self, adapter: SocketioLivelistPlaylistClient) -> None:
        self._adapter = adapter

    def pe_update_songlist(self, songs):
        self._adapter._rebuild_songlist()
        for cb in self._adapter._cbs:
            cb.pe_update_songlist(self._adapter._songlist)

    def pe_update_playlist(self, items):
        self._adapter._rebuild_playlist()
        for cb in self._adapter._cbs:
            cb.pe_update_playlist(list(self._adapter._playlist.values()))

    def pe_play(self, item):
        pli = self._adapter._playlist.get(item.id) if item else None
        if pli is not None:
            for cb in self._adapter._cbs:
                cb.pe_play(pli)

    def pe_add(self, item):
        pli = _convert_playlist_item(item, self._adapter._songlist)
        self._adapter._playlist[pli.id] = pli
        for cb in self._adapter._cbs:
            cb.pe_add(pli)
