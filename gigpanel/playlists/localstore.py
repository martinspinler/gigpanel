import os
from typing import Any, Optional

from ..song import Song


def resolve_local_file(
    song: Song,
    stores: Optional[dict[str, Any]],
    prefixes: Optional[dict[str, str]],
    default_store: Optional[str],
) -> Optional[str]:
    """Resolve a song's sheet file from the local {stores, prefixes} config.

    The store is ``song.store`` (if defined locally) or ``default_store``. If the store (or the
    song) has a ``pattern``, it is formatted with the song name and prefixed
    with the store prefix; a pattern without ``{name}`` names one shared file
    (e.g. a single PDF with all songs, paired with per-song ``pages``).
    Then ``prefix + path + (filename | name) + suffix`` is tried.
    Returns the existing file path, or None.
    """
    stores = stores or {}
    store = stores.get(song.store) if song.store is not None else None
    if store is None and default_store is not None:
        store = stores.get(default_store)
    if store is None:
        return None

    prefix = (prefixes or {}).get(store.get('prefix'), '') if store.get('prefix') else ''
    suffix = store.get('suffix', '.pdf')
    base = prefix + store.get('path', '')

    pattern = song.pattern if song.pattern is not None else store.get('pattern')
    if pattern is not None:
        for name in (song.filename, song.name):
            if not name:
                continue
            candidate = prefix + pattern.format(name=name, instrument='')
            if os.path.isfile(candidate):
                return candidate

    for name in (song.filename, song.name):
        if not name:
            continue
        candidate = base + name
        if not candidate.endswith(suffix):
            candidate += suffix
        if os.path.isfile(candidate):
            return candidate

    return None
