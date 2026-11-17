import os
import string
from typing import Any, Optional

from ..song import Song


def format_pattern(pattern: str, **fields: Any) -> Optional[str]:
    """Format a store pattern, e.g. ``'{user_id} {name}.pdf'``.

    Returns None when the pattern uses a field that is missing (None) for
    this song (e.g. ``{user_id}`` of a song without one), so such a pattern
    is skipped instead of producing a bogus path or raising KeyError.
    """
    for _, field, _, _ in string.Formatter().parse(pattern):
        if field and fields.get(field) is None:
            return None
    return pattern.format(**fields)


def resolve_local_file(
    song: Song,
    stores: Optional[dict[str, Any]],
    prefixes: Optional[dict[str, str]],
    default_store: Optional[str],
) -> Optional[str]:
    """Resolve a song's sheet file from the local {stores, prefixes} config.

    The store is ``song.store`` (if defined locally) or ``default_store``. If the store (or the
    song) has a ``pattern``, it is formatted with the song name (``{name}``)
    and ``{user_id}`` and prefixed with the store prefix; a pattern without ``{name}`` names one shared file
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
            formatted = format_pattern(pattern, name=name, user_id=song.user_id or None, instrument='')
            if formatted is None:
                continue
            candidate = prefix + formatted
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
