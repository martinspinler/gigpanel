import os
from typing import Any, Optional

from livelist.songfind import build_store, find_documents, format_pattern, pick_best_for_instrument

from ..song import Song


# Used when no instrument config is available (local playlist client, or the
# server config not fetched yet): {instrument} is then an empty suffix.
_NO_INSTRUMENTS = {'': {'name': '', 'patterns': ['']}}


def store_patterns(store: dict[str, Any]) -> list[Any]:
    """Patterns of a local store config: ``patterns`` (a list, tried in
    order) or the single ``pattern`` shorthand."""
    if store.get('patterns'):
        return list(store['patterns'])
    if store.get('pattern'):
        return [store['pattern']]
    return []


def resolve_local_file(
    song: Song,
    stores: Optional[dict[str, Any]],
    prefixes: Optional[dict[str, str]],
    default_store: Optional[str],
    instruments: Optional[dict[str, Any]] = None,
    instrument: Optional[str] = None,
    orientation: Optional[str] = None,
) -> Optional[str]:
    """Resolve a song's sheet file from the local {stores, prefixes} config.

    The store is ``song.store`` (if defined locally) or ``default_store``.
    Its patterns (``song.pattern`` if set, else the store's ``patterns`` list
    or single ``pattern``) are resolved under the store prefix with the
    livelist finder. Placeholders:

    - ``{name}``: song filename or name
    - ``{instrument}``: instrument filename suffix (e.g. ``-Drums``) from
      ``instruments`` (as in the server band config); empty without it
    - ``{instrument_id}``: the selected ``instrument`` itself (e.g. ``drums``),
      e.g. for per-instrument folders
    - ``{user_id}``: the song's user_id

    A pattern using ``{user_id}`` / ``{instrument_id}`` is skipped when the
    song has no user_id / no instrument is selected. A pattern is a string
    or a dict in the server pattern format (``pattern``, optional
    ``render``, ``label``, ``instr``). A pattern without ``{name}`` names one
    shared file (e.g. a single PDF with all songs, paired with per-song
    ``pages``). Then ``prefix + path + (filename | name) + suffix`` is tried;
    ``path`` may use ``{instrument_id}`` and ``{user_id}`` too.
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
    fields = {'user_id': song.user_id or None, 'instrument_id': instrument or None}

    names = [n for n in (song.filename, song.name) if n]

    patterns = [song.pattern] if song.pattern is not None else store_patterns(store)
    if patterns and names:
        pcfg = {}
        for i, p in enumerate(patterns):
            p = {'pattern': p} if isinstance(p, str) else dict(p)
            pid = str(p.pop('id', f'p{i}'))
            pcfg[pid] = {'render': 'pdf', 'label': pid, **p}
        fstore = build_store({'patterns': pcfg, 'instruments': instruments or _NO_INSTRUMENTS}, prefix)
        documents = find_documents(names, fstore, orientation=orientation, fields=fields)
        doc = pick_best_for_instrument(documents, instrument)
        if doc is not None:
            return prefix + doc['path']

    path = format_pattern(store.get('path', ''), **fields)
    if path is None:
        return None
    for name in names:
        candidate = prefix + path + name
        if not candidate.endswith(suffix):
            candidate += suffix
        if os.path.isfile(candidate):
            return candidate

    return None
