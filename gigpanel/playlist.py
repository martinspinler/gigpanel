#!/usr/bin/python3
import json
import asyncio
import aiohttp
import ssl
import urllib.parse


class PlaylistClient():
    def __init__(self, url, prefix='', currentBand=1):
        addr = urllib.parse.urlsplit(url)
        secure = "s" if addr.scheme == 'https' else ""
        self._addr = f"{addr.scheme}://{addr.netloc}"
        self._wsaddr = f"ws{secure}://{addr.netloc}"
        self._prefix = prefix
        self._queue = asyncio.Queue()
        self._currentBand = currentBand
        self._cbs = []

    def add_callback(self, cb):
        self._cbs.append(cb)

    async def _receive_msg(self, msgid):
        i = 0
        while True:
            i += 1
            if i > 100:
                #print("Keep-alive", time.time())
                await self.ws.send_str("client:keep-alive-hotfix:{}")
                i = 0

            try:
                msg = self._queue.get_nowait()
                if msg == "close":
                    await self._disconnect()
                    return None, None
            except asyncio.QueueEmpty:
                pass
            else:
                await self.ws.send_str("client:" + msg)

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

                await self.get_playlist()
            else:
                print(msg.type)
        return None, None

    async def connect(self):
        self.session = aiohttp.ClientSession()
        ssl._create_default_https_context = ssl._create_unverified_context
        self.context = ssl._create_unverified_context()

        self.headers = {}
        resp = await self.session.get(f'{self._addr}/client/', ssl=self.context, headers=self.headers)
        t1 = await resp.text()
        if 'refresh' in t1:
            resp = await self.session.get(f'{self._addr}/client/', ssl=self.context, headers=self.headers)
            t1 = await resp.text()
        await self._reconnect()

    async def _reconnect(self):
        self.ws = await self.session.ws_connect(f'{self._wsaddr}/client/', ssl=self.context, headers=self.headers)
        msg = f"""lona:[1,null,101,["{self._prefix}/client/",null]]"""

        await self.ws.send_str(msg)

    async def _disconnect(self):
        await self.ws.close()
        await self.session.close()

    def disconnect(self):
        self._queue.put_nowait('close')

    def playlist_item_add(self, si):
        self.send_msg('add', {'song_id': si.song['id'], 'playlist_id': self.currentPlaylistId})

    def playlist_item_del(self, si):
        self.send_msg('delete', {'id': si, 'playlist_id': self.currentPlaylistId})

    def playlist_item_move(self, si, pos):
        self.send_msg('move', {'id': si, 'playlist_id': self.currentPlaylistId, 'pos': pos})

    def playlist_item_set(self, id=None, off=None):
        self.send_msg('play', {'id': id, 'playlist_id': self.currentPlaylistId, 'off': off})

    def send_msg(self, msg, data={}):
        self._queue.put_nowait(f'{msg}:' + json.JSONEncoder().encode(data))

    async def send_msg_async(self, msg: str, data={}):
        await self.ws.send_str(f"client:{msg}:" + json.JSONEncoder().encode(data))

    async def get_messages(self):
        req = True if hasattr(self, 'ws') else False
        while req:
            req, data = await self._receive_msg(None)
            if req in ['add', 'delete', 'update', 'play']:
                for cb in self._cbs:
                    cb(req, data)

    async def get_playlist(self):
        await self.send_msg_async("get-playlist", {'playlist_id': self.currentPlaylistId})
        _, data = await self._receive_msg('playlist')
        return data

    async def get_db(self):
        await self.send_msg_async("get-active-playlist", {'band_id': self._currentBand})
        _, data = await self._receive_msg('active-playlist')
        self.currentPlaylistId = data['playlist_id']

        await self.send_msg_async("get-songlist", {'band_id': self._currentBand})
        _, data = await self._receive_msg('songlist')
        j = data
        j = {int(k): v for k, v in j.items()}
        j = {k: v for k, v in j.items()}
        [j[k].update({'id': k}) for k in j.keys()]
        return j
