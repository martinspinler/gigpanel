from typing import Dict, Optional, TypeAlias
from dataclasses import dataclass


SongId: TypeAlias = int
PlaylistItemId: TypeAlias = int


#Song = Dict[str, Any]
@dataclass
class Song:
    id: SongId
    name: str
    store: Optional[str] = None
    user_id: Optional[str] = None
    filename: Optional[str] = None
    bpm: Optional[int] = None


@dataclass
class PlaylistItem:
    id: PlaylistItemId
    song: Song
    pos: int


Songlist: TypeAlias = Dict[SongId, Song]
Playlist: TypeAlias = list[PlaylistItem]  # TODO: Fixme
