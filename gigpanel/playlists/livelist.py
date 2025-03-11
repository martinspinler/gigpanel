import json
import asyncio
import aiohttp
import ssl
import urllib.parse

from typing import Any, Dict, Optional, Tuple
from dataclasses import fields

from ..playlist import PlaylistClient
from ..song import Song, PlaylistItem, PlaylistItemId


class LivelistPlaylistClient(PlaylistClient):
    def __init__(self, url: Optional[str] = None, prefix: str = '', currentBand: int = 1):
        super().__init__()
        addr = urllib.parse.urlsplit(url)
        secure = "s" if addr.scheme == 'https' else ""
        self._addr = f"{str(addr.scheme)}://{str(addr.netloc)}"
        self._wsaddr = f"ws{secure}://{str(addr.netloc)}"
        self._prefix = prefix
        self._queue: asyncio.Queue[str] = asyncio.Queue()
        self._currentBand = currentBand

    async def _receive_msg(self, msgid: Optional[str]) -> Tuple[str, Dict[str, Any]]:
        i = 0
        while True:
            i += 1
            if i > 100:
                #print("Keep-alive", time.time())
                await self.ws.send_str("client:keep-alive-hotfix:{}")
                i = 0

            try:
                msg_txt = self._queue.get_nowait()
                if msg_txt == "close":
                    await self._disconnect()
                    raise ConnectionError
            except asyncio.QueueEmpty:
                pass
            else:
                await self.ws.send_str("client:" + msg_txt)

            try:
                msg = await self.ws.receive(timeout=0.1)
            except asyncio.TimeoutError:
                continue

            if msg.type == aiohttp.WSMsgType.TEXT:
                text = msg.data
                if text.startswith("client:"):
                    _, req, jdata = text.split(":", 2)
                    data = json.JSONDecoder().decode(jdata)
                    if msgid is None or req == msgid:
                        return req, data
                elif text.startswith("lona:"):
                    pass
                else:
                    print(msg)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                print("Err")
                break
            elif msg.type == aiohttp.WSMsgType.CLOSE:
                print("Close")
                #self._reconnect()
                #await self.ws.close()
                break
            elif msg.type == aiohttp.WSMsgType.CLOSED:
                print("Closed")
                #await self._reconnect()
                await self.session.close()
                await self.connect()

                try:
                    await self.get_songlist()
                    await self.get_playlist()
                except ConnectionError:
                    pass

            else:
                print(msg.type)
        raise ConnectionError

    async def _session_get(self, addr: str) -> str:
        resp = await self.session.get(addr, ssl=self.context)#, headers=self.headers)
        return await resp.text()

    async def connect(self) -> None:
        self.session = aiohttp.ClientSession()
        ssl._create_default_https_context = ssl._create_unverified_context
        self.context = ssl._create_unverified_context()

        #self.headers = {}
        t = await self._session_get(f'{self._addr}/client/')
        if 'refresh' in t:
            await self._session_get(f'{self._addr}/client/')

        await self._reconnect()

        try:
            await self.get_songlist()
            await self.get_playlist()
        except ConnectionError:
            pass

    async def _reconnect(self) -> None:
        self.ws = await self.session.ws_connect(f'{self._wsaddr}/client/', ssl=self.context) #, headers=self.headers)
        msg = f"""lona:[1,null,101,["{self._prefix}/client/",null]]"""

        await self.ws.send_str(msg)

    async def _disconnect(self) -> None:
        await self.ws.close()
        await self.session.close()

    def disconnect(self) -> None:
        self._queue.put_nowait('close')

    def playlist_item_add(self, si: Song) -> None:
        self.send_msg('add', {'song_id': si.id, 'playlist_id': self.currentPlaylistId})

    def playlist_item_del(self, si: PlaylistItemId) -> None:
        self.send_msg('delete', {'id': si, 'playlist_id': self.currentPlaylistId})

    def playlist_item_move(self, si: PlaylistItemId, pos: int) -> None:
        self.send_msg('move', {'id': si, 'playlist_id': self.currentPlaylistId, 'pos': pos})

    def playlist_item_set(self, id: Optional[PlaylistItemId] = None, off: Optional[int] = None) -> None:
        print("PIS", id, off)
        self.send_msg('play', {'id': id, 'playlist_id': self.currentPlaylistId, 'off': off})

    def send_msg(self, msg: str, data: Any = {}) -> None:
        self._queue.put_nowait(f'{msg}:' + json.JSONEncoder().encode(data))

    async def send_msg_async(self, msg: str, data: Any = {}) -> None:
        await self.ws.send_str(f"client:{msg}:" + json.JSONEncoder().encode(data))

    async def get_messages(self) -> None:
        if not hasattr(self, 'ws'):
            return

        while True:
            try:
                req, data = await self._receive_msg(None)
            except ConnectionError:
                break

            m = {
                'update': self.receive_playlist,
                'play': self.receive_play,
                'add': self.receive_add,
                'delete': self.receive_del,
            }
            if req in m:
                m[req](data)

    async def get_playlist(self) -> None:
        await self.send_msg_async("get-playlist", {'playlist_id': self.currentPlaylistId})
        _, data = await self._receive_msg('playlist')
        self.receive_playlist(data)

        await self.send_msg_async("get-playlist-current-item", {'playlist_id': self.currentPlaylistId})
        _, data = await self._receive_msg('playlist-current-item')
        self.receive_playlist_current_item(data)

    def receive_playlist(self, data: Any) -> None:
        f = [s.name for s in fields(PlaylistItem) if s.name not in ['id']]
        pli = {v['id']: PlaylistItem(id=v['id'], song=self.songlist[int(v['song_id'])], pos=i, **{kk: vv for kk, vv in v.items() if kk in f}) for i, (k, v) in enumerate(data.items())}
        self.playlist = pli

        for cb in self._cbs:
            cb.pe_update_playlist(list(self.playlist.values()))

    def receive_playlist_current_item(self, data: Any) -> None:
        cpid = data['playlist_item_id']
        cpi = self.playlist[cpid]
        for cb in self._cbs:
            cb.pe_play(cpi)

    def receive_play(self, data: Any) -> None:
        pli = self.playlist[data['id']]
        for cb in self._cbs:
            cb.pe_play(pli)

    def receive_add(self, data: Any) -> None:
        id = data['id']
        pli = PlaylistItem(id=id, song=self.songlist[int(data['song_id'])], pos=len(self.playlist))
        self.playlist.update({id: pli})
        for cb in self._cbs:
            cb.pe_add(pli)

    def receive_del(self, data: Any) -> None:
        del self.playlist[data['id']]
        for cb in self._cbs:
            cb.pe_update_playlist(list(self.playlist.values()))

    async def get_songlist(self) -> None:
        await self.send_msg_async("get-active-playlist", {'band_id': self._currentBand})
        _, data = await self._receive_msg('active-playlist')
        self.currentPlaylistId = data['playlist_id']

        await self.send_msg_async("get-songlist", {'band_id': self._currentBand})
        _, data = await self._receive_msg('songlist')
        s = {int(k): v for k, v in data.items()}
        j = {k: v for k, v in s.items()}
        [j[k].update({'id': k}) for k in j.keys()]

        f = [s.name for s in fields(Song)]

        songlist = {v['id']: Song(**{kk: vv for kk, vv in v.items() if kk in f}) for k, v in j.items()}

        self.songlist = songlist
        for cb in self._cbs:
            cb.pe_update_songlist(songlist)
