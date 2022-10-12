#!/usr/bin/python3
import argparse
import os
import sys
import json
import yaml
import re
import contextlib
import random
import sqlite3
import subprocess
from pathlib import Path

import lona
import lona_bootstrap_5
from lona import LonaView, LonaApp
from lona.html import NumberInput, A, Span, HTML, H1, Div, Node, Widget, Tr, Td, Ul, Li, Hr, Ol, Nav, Img, Small
from lona_bootstrap_5 import (
    BootstrapDiv,
    SecondaryButton,
    SuccessButton,
    PrimaryButton,
    DangerButton,
    Button,
)
from offcanvas import Offcanvas

from lona.static_files import StyleSheet, Script, SORT_ORDER

class Config:
    def __init__(self):
        y = yaml.load(open('config.yaml', 'r').read(), yaml.Loader)
        self.__dict__.update({k:v for k,v in y['webServer'].items()})

cfg = Config()
app = LonaApp(__file__)

class MyLonaView(LonaView):
    def trigger_view_event(self, name, data, urls=['/', '/client/', '/play/']):
        for url in urls:
            vc = self.server.get_view_class(url=cfg.url_prefix + url)
            if vc:
                #print(self, name, data, url)
                self.server.fire_view_event(name, data, view_classes=vc)

class PlaylistItem():
    def __repr__(self):
        return str(self.songId)

class Song():
    @classmethod
    def from_yaml(cls, loader, node):
        s = cls()
        attrs = ['id', 'name', 'file', 'store', 'notes', 'bpm']
        [setattr(s, x, node[x]) for x in attrs if x in node]
        [setattr(s, x, None) for x in attrs if x not in node]

        # Temporary conversion
        #if 'Tempo' in node: s.bpm = node['Tempo']
        #if 'Notes' in node: s.notes = node['Notes']
        s.played = 0
        return s

    @classmethod
    def to_yaml(cls, dumper, data):
        node = data.__dict__.copy()
        exclude = ['played', 'filename']
        for i in data.__dict__:
            if node[i] == None or i in exclude:
                del node[i]
        return node

class JSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Song):
            return {x: getattr(obj, x) for x in ['name', 'file', 'filename', 'store', 'notes', 'bpm', 'played']}
        if isinstance(obj, PlaylistItem):
            return {x: getattr(obj, x) for x in ['id', 'playlistId', 'songId']}
        return json.JSONEncoder.default(self, obj)

class Database():
    def __init__(self):
        self.pli_counter = 1

        self.config = yaml.load(open('config.yaml', 'r').read(), yaml.Loader)

        songs = yaml.load(open('songs.yaml', 'r').read(), yaml.Loader)
        self.songs = {int(s['id']):Song.from_yaml(None, s) for s in songs}

        for song in self.songs.values():
            store = (self.config['stores'][song.store]) if song.store != None else (self.config['stores'][self.config['defaultStore']])
            song.filename = self.config['prefixes'][store['prefix']] + store['path'] + song.file + store['suffix'] if song.file != None else None

        self.playlist = yaml.load(open('playlist.yaml', 'r').read(), yaml.Loader)
        #print(self.playlist)

        for p in self.playlist.values():
            if not hasattr(p, 'currentItemId'):
                p['currentItemId'] = None

        for p in self.playlist.values():
            for i in range(len(p['items'])):
                pli = p['items'][i]
                self.songs[pli.songId].played += 1
                p['items'][i].id = self.pli_counter
                #self.songs[i.songId].played += 1
                self.pli_counter += 1

        self.save()

    def save(self):
        with open('playlist.yaml', 'w') as yaml_file:
            yaml.dump(self.playlist, yaml_file, default_flow_style=False)

        # Temporary conversion
        #with open('songs.yaml', 'w') as yaml_file:
        #    yaml.dump([Song.to_yaml(None, s) for s in self.songs.values()], yaml_file, default_flow_style=False, allow_unicode=True)

    def newPlaylistItem(self, pl, song):
        item = PlaylistItem()
        item.id = self.pli_counter
        item.playlistId = pl
        item.songId = song.id
        item.played = False
        #item.pos = len(self.playlist[pl]['items'])
        self.pli_counter += 1

        #self.playlist[pl]['items'][item.id] = item
        self.playlist[pl]['items'].append(item)

        self.save()

        return item

    def deletePlaylistItem(self, pli):
        i = self.playlist[pli.playlistId]['items'].index(pli)
        del self.playlist[pli.playlistId]['items'][i]
        #del self.playlist[pli.playlistId]['items'][pli.id]

        self.save()

    def playlistItemMove(self, item, new_index, relative=False):
        pl = self.playlist[item.playlistId]['items']
        index = pl.index(item) # item.pos
        if relative:
            if index + new_index not in range(0, len(pl) + 1):
                return False
            pl.pop(index)
            pl.insert(index + (-1 if new_index < 0 else 1), item)

        self.save()
        return True

    def get_currentPlaylistItem(self, playlistId):
        playlist = db.playlist[playlistId]
        pl = playlist['items']
        ci = playlist['currentItemId']
        if ci == None:
            return None
        pli = [x for x in pl if x.id == ci]
        # Can be deleted
        if pli:
            return pli[0]
        return None

    def set_currentPlaylistItem(self, playlistId, item):
        playlist = db.playlist[playlistId]
        pl = playlist['items']
        playlist['currentItemId'] = item.id

    def get_playlistItemNeighbour(self, playlistId, pli, offset):
        playlist = db.playlist[playlistId]
        if pli == None:
            #i = len(playlist['items']) if offset < 0 else -offset
            i = -1 if offset < 0 else -offset
        else:
            i = playlist['items'].index(pli)
        if i + offset not in range(len(playlist['items'])):
            return None
        else:
            return playlist['items'][i + offset]


    #def get_currentPlaylistItem(self, playlistId):
    #    playlist  = db.playlist[playlistId]
    #    ci = pli['currentItemId']



class Keypad(Widget):
    nummap = {'1': "^\n", '2': "2aábcč", '3': "3dďeéf", '4': "4ghií", '5': "5jkl", '6': "6mnňoó", '7': "7pqrřsš", '8': "8tťuúův", '9': "9wxyýzž", '0': "0 "}
    keypad_btns = ['1', '2 ABC', '3 DEF', '4 GHI ', '5 JKL', '6 MNO', '7 PQRS', '8 TUV', '9 WXYZ', 'BS', '0', 'Clr']
    def __init__(self):
        btns = [PrimaryButton(t, handle_click=self.on_keypad, _class="btn-lg") for i, t in enumerate(Keypad.keypad_btns)]
        self.nodes = Div([Tr([Td(Div(btns[y*3+x], _class="d-grid p-1"), _class="gap-2") for x in range(3)], _class="gap-2") for y in range(4)])
        self.listeners = []

    def on_keypad(self, ev):
        key = ev.node.get_text()[0]
        [l(key) for l in self.listeners]

class PlaylistPanel(Offcanvas):
    def __init__(self, on_song, _id):
        Offcanvas.__init__(self, _id)
        btns = []
        for i, p in db.playlist.items():
            bt = PrimaryButton(p['date'] + " " + p['note'], handle_click=on_song)
            bt.playlistId = i
            btns.append(bt)

        items = [Div(b, _class="list-group-item") for b in btns]
        self.div_play_list = Div(*items, _class="list-group gap-1")

        self.set_title("Playlists")
        self.set_body(self.div_play_list)


class SonglistItem(Div):
    def __init__(self, song, h):
        Div.__init__(self)
        #self.class_list.append("d-grid")
        #self.class_list.append("d-md-block d-grid")
        self.class_list.append("clearfix")
        self.class_list.append("d-flexlock")
        self.class_list.append("d-md-block")

        name = song.name if len(song.name) <= 30 else song.name[:30] + "..."
        self.btn = SecondaryButton(
                Span(name, _class="d-grid flex-grow-1"),
                handle_click=h,
                _class="flex-grow-1",
                )
        self.song = self.btn.song = song
        self.nodes = [
                self.btn,
                Span(str(song.played), _class="badge bg-primary rounded-pill float-end"),
            ] + ([Span(song.bpm, _class="bi bi-music-note float-end")] if song.bpm else [])

class SonglistPanel(Offcanvas):
    def __init__(self, on_song, _id):
        Offcanvas.__init__(self, _id)
        self.on_song_cb = on_song
        self.kp = Keypad()
        self.kp.listeners.append(self.keypad_btns)

        self.div_song_list = Div(_class="list-group gap-1")
        #n = [SonglistItem(db.songs[s], on_song) for s in db.songs]
        #self.div_song_list.nodes = n
        self.on_sort(None)

        self.sort_alp = PrimaryButton(_class="bi bi-sort-alpha-down", handle_click=self.on_sort)
        self.sort_bpm = PrimaryButton(_class="bi bi-sort-numeric-down", handle_click=self.on_sort)

        self.kpfs = Small()
        self.set_title("Song list")
        self.set_body(self.kp, Hr(), Div(self.sort_alp, self.sort_bpm, self.kpfs, _class="d-flex gap-2"), Hr(), self.div_song_list)

        self.kpf = ""
        self.keypad_btns("C")

    def on_sort(self, ev):
        n = [SonglistItem(db.songs[s], self.on_song_cb) for s in db.songs]
        if ev and ev.node == self.sort_bpm:
            n = sorted(n, key=lambda x: x.song.bpm)
        self.div_song_list.nodes = n

    def keypad_btns(self, key):
        if key == 'B':
            self.kpf = self.kpf[:-1]
        elif key == 'C':
            self.kpf = ""
        else:
            self.kpf += key
        kf = "".join(["[" + Keypad.nummap[num] + "]" for num in self.kpf])

        kb = {x[0]:x for x in Keypad.keypad_btns}
        self.kpfs.set_text("|".join([kb[num] for num in self.kpf]).replace(" ",""))

        for n in self.div_song_list.nodes:
            if re.search(kf, n.song.name, re.I) != None:
                n.show()
                #n.class_list.append("d-grid")
                n.class_list.append("d-md-block")
            else:
                n.hide()
                #n.class_list.remove("d-grid")
                n.class_list.remove("d-md-block")

class InstrumentSelector(Div):
    def __init__(self):
        Div.__init__(self, _class="dropdown")
        self.nodes = HTML("""<button class="btn btn-secondary dropdown-toggle" type="button" id="dropdownMenu2" data-bs-toggle="dropdown" aria-haspopup="true" aria-expanded="false">Instrument</button>
  <div class="dropdown-menu" aria-labelledby="dropdownMenu2">
    <button class="dropdown-item" type="button">Piano</button>
    <button class="dropdown-item disabled" type="button">Vocal</button>
    <button class="dropdown-item disabled" type="button">Sax</button>
  </div>""")

@app.route(cfg.url_prefix + '/')
class PlaylistView(MyLonaView):
    def on_play(self, ev):
        item = ev.node.parent.playlistItem
        db.set_currentPlaylistItem(self.currentPlaylist, item)
        self.trigger_view_event('play', {'playlistItem': item})

    def on_recycle(self, ev):
        return
        ev.node.parent.class_list.remove("list-group-item-secondary")

    def on_up(self, ev):
        item = ev.node.parent.playlistItem
        if db.playlistItemMove(item, -1, True):
            self.trigger_view_event('update', {'playlistId': item.playlistId})

    def on_down(self, ev):
        item = ev.node.parent.playlistItem
        if db.playlistItemMove(item, 1, True):
            self.trigger_view_event('update', {'playlistId': item.playlistId})

    def on_delete(self, ev):
        item = ev.node.parent.playlistItem
        db.deletePlaylistItem(item)
        self.trigger_view_event('delete', {'playlistItem': item})

    def song_delete(self, pli):
        node = [x for x in self.playlist.nodes if x.playlistItem == pli]
        same = [x for x in self.playlist.nodes if x.playlistItem.songId == pli.songId]
        if node: self.playlist.nodes.remove(node[0])
        songNode = [s for s in self.songlist.div_song_list.nodes if s.song.id == pli.songId]
        if songNode and len(same) == 1: songNode[0].btn.class_list.remove("btn-dark")

    def on_playlist(self, ev):
        self.setCurrentPlaylist(ev.node.playlistId)

    def setCurrentPlaylist(self, pid):
        pl = [x for x in self.playlistPanel.div_play_list if x.nodes[0].playlistId == self.currentPlaylist]
        for p in pl:
            p.class_list.remove("active")

        self.currentPlaylist = pid

        self.btn_play.set_href(f'{cfg.url_prefix}/play/{self.currentPlaylist}')

        pl = [x for x in self.playlistPanel.div_play_list if x.nodes[0].playlistId == self.currentPlaylist]
        pl[0].class_list.append("active")

        self.populate_playlist()

    def on_songlist(self, ev):
        song = ev.node.song
        pli = db.newPlaylistItem(self.currentPlaylist, song)
        self.trigger_view_event('add', {'playlistItem': pli})
        #self.fire_view_event('add', {'playlistItem': pli})
        #self.server.fire_view_event('add', {'playlistItem': item},
        #        view_classes=self.server.get_view_class(url=cfg.url_prefix + '/client/'))

    def play_item(self, item):
        if self.playing:
            self.playing.class_list.remove("active")
            #self.playing.class_list.append("list-group-item-secondary")
        self.playing = [x for x in self.playlist.nodes if x.playlistItem == item][0]
        self.playing.class_list.append("active")

    def add_playlist_item(self, pli):
        song = db.songs[pli.songId]

        songNode = [s for s in self.songlist.div_song_list.nodes if s.song.id == song.id]
        if songNode:
            songNode[0].btn.class_list.append("btn-dark")

        li = Li(
            SuccessButton(_class="bi bi-play-fill", handle_click=self.on_play),
            Div(song.name, _class="flex-grow-1"),
            PrimaryButton(_class="bi bi-arrow-up btn-edit d-xxl-block", handle_click=self.on_up),
            PrimaryButton(_class="bi bi-arrow-down btn-edit d-xxl-block", handle_click=self.on_down),
            SuccessButton(_class="bi bi-recycle btn-edit d-xxl-block", handle_click=self.on_recycle),
            DangerButton (_class="bi bi-trash btn-edit d-xxl-block", handle_click=self.on_delete),
            _class="list-group-item gap-3 d-flex")

        li.playlistItem = pli
        #self.playlist.nodes.insert(pli.pos, li) # CHECK
        self.playlist.nodes.append(li)

    def populate_playlist(self):
        self.playlist.nodes.clear()
        songNode = [s.btn.class_list.remove("btn-dark") for s in self.songlist.div_song_list.nodes]

        for pli in db.playlist[self.currentPlaylist]['items']:
            self.add_playlist_item(pli)
        pli = db.get_currentPlaylistItem(self.currentPlaylist)
        if pli:
            self.play_item(pli)

    def hide_edit(self, x):
        items = self.playlist.query_selector_all('button.bi-recycle,button.bi-trash,button.bi-arrow-up,button.bi-arrow-down')
        [f.show() for f in items] if self._e_hidden else [f.hide() for f in items]
        self._e_hidden = not self._e_hidden

    def handle_request(self, request):
        self._e_hidden = False
        self.playing = None
        self.currentPlaylist = None

        self.playlist = Ul(_class="list-group gap-2", _id="playlist")
        self.songlist = sl = SonglistPanel(self.on_songlist, "songlistpanel")
        self.playlistPanel = pp = PlaylistPanel(self.on_playlist, "playlistpanel")
        self.btn_play = A("Live", _class="btn btn-primary bi bi-file-play", attributes={'href': f'{cfg.url_prefix}/play/{self.currentPlaylist}', 'target': "_blank"})
        #print(type(self.btn_play), self.btn_play)

        self.setCurrentPlaylist(1)
        self.populate_playlist()
        self.hide_edit(None)

        nav = Nav(
            Button("Add song", _class="btn btn-primary bi bi-plus", attributes={'data-bs-toggle': "offcanvas", 'data-bs-target': "#songlistpanel"}),
            Button("Playlists", _class="btn btn-primary bi bi-list-ul", attributes={'data-bs-toggle': "offcanvas", 'data-bs-target': "#playlistpanel"}),
            self.btn_play,
            Button("Edit", _class="btn btn-primary bi bi-pencil-fill", handle_click=self.hide_edit),
            _class="navbar navbar-expand-lg gap-2"
        )

        html = HTML(
            """<meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">""",
            nav,
            self.songlist,
            self.playlistPanel,
            self.playlist
        )

        #self.songlist.show()

        self.show(html)

    def on_view_event(self, e):
        if e.name == 'add' and e.data['playlistItem'].playlistId == self.currentPlaylist:
            #print(e)
            self.add_playlist_item(e.data['playlistItem'])
        if e.name == 'delete' and e.data['playlistItem'].playlistId == self.currentPlaylist:
            self.song_delete(e.data['playlistItem'])
        if e.name == 'play' and e.data['playlistItem'].playlistId == self.currentPlaylist:
            self.play_item(e.data['playlistItem'])
        if e.name == 'update' and e.data['playlistId'] == self.currentPlaylist:
            self.populate_playlist()

    def on_cleanup(self):
        pass

@app.route(cfg.url_prefix + '/play/<playlistId:.*>')
class PlayView(MyLonaView):
    def on_forward(self, ev):
        self.on_to(+1)
    def on_backward(self, ev):
        self.on_to(-1)
    def on_to(self, offset):
        pli = db.get_currentPlaylistItem(self.activePlaylist)
        item = db.get_playlistItemNeighbour(self.activePlaylist, pli, offset)
        if item != None:
            db.set_currentPlaylistItem(self.activePlaylist, item)
            self.trigger_view_event('play', {'playlistItem': item})

    def handle_request(self, request):
        self.currentSong = Div()
        self.activePlaylist = None
        if 'playlistId' in request.match_info and request.match_info['playlistId']:
            self.activePlaylist = int(request.match_info['playlistId'])
        self.img = Div()
        self.instr_select = InstrumentSelector()

        self.forward = SuccessButton(_class="bi bi-skip-forward-fill push-right", handle_click=self.on_forward)
        self.backward = SuccessButton(_class="bi bi-skip-backward-fill", handle_click=self.on_backward)
        self.pagination = HTML("""<ul class="pagination">
    <li class="page-item">
      <a class="page-link disabled" href="#" aria-label="Previous">
        <span aria-hidden="true">&laquo;</span>
      </a>
    </li>
    <li class="page-item"><a class="page-link disabled" href="#">1</a></li>
    <li class="page-item"><a class="page-link disabled" href="#">2</a></li>
    <li class="page-item"><a class="page-link disabled" href="#">3</a></li>
    <li class="page-item">
      <a class="page-link disabled" href="#" aria-label="Next">
        <span aria-hidden="true">&raquo;</span>
      </a>
    </li>
  </ul>""")
        nav = Nav(
            self.backward,
            A("Playlist", _class="btn btn-primary bi bi-list-ul", attributes={'href': f'{cfg.url_prefix}/', 'target': "_blank"}),
            self.forward,
            self.instr_select,
#            self.pagination,
            Div("Current Playlist: " + db.playlist[self.activePlaylist]['date'] + " | song: ", self.currentSong),
            _class="navbar navbar-expand-lg gap-2"
        )
        pli = db.get_currentPlaylistItem(self.activePlaylist)
        if pli != None:
            #pli = [x for x in db.playlist[self.activePlaylist]['items'] if x.id == pli][0]
            self.loadSong(pli)

        self.update_btns()

        return HTML(nav, self.img)

    def update_btns(self):
        if self.activePlaylist == None:
            return
        ci = db.get_currentPlaylistItem(self.activePlaylist)
        bw, fw = [db.get_playlistItemNeighbour(self.activePlaylist, ci, o) for o in [-1, 1]]
        self.backward.set_text(db.songs[bw.songId].name if bw else "")
        self.backward.class_list.remove("disabled") if bw else self.backward.class_list.append("disabled")
        self.forward.set_text (db.songs[fw.songId].name if fw else "")
        self.forward.class_list.remove("disabled") if fw else self.forward.class_list.append("disabled")
        return

        if ci != None:
            pl = playlist['items']
            pli = [x for x in pl if x.id == ci][0]
            i = pl.index(pli)
            self.backward.set_text(db.songs[pl[i-1].songId].name if i > 0 else "")
            self.backward.class_list.remove("disabled") if i > 0 else self.backward.class_list.append("disabled")
            self.forward.set_text (db.songs[pl[i+1].songId].name if i < len(pl) - 1 else "")
            self.forward.class_list.remove("disabled") if i < len(pl) -1 else self.forward.class_list.append("disabled")

    def on_view_event(self, e):
        if e.name == 'play' and e.data['playlistItem'].playlistId == self.activePlaylist:
            playlistItem = e.data['playlistItem']
            self.loadSong(playlistItem)
            self.update_btns()
        if e.name == 'update' and e.data['playlistId'] == self.activePlaylist:
            self.update_btns()


    def loadSong(self, playlistItem):
        song = db.songs[playlistItem.songId]
        self.currentSong.set_text(song.name)
        self.img.nodes = []
        if song.filename == None or not os.path.isfile(song.filename):
            return

        pages = subprocess.check_output(f'pdfinfo "{song.filename}" |grep -a Pages:', shell = True).decode()
        pages = int(pages.split(":")[1].strip())
        self.img.nodes = [Img(attributes={'src': cfg.url_prefix + "/sheets/" + str(song.id) + f"-piano--{i+1}.jpg"}) for i in range(pages)]


@app.route(cfg.url_prefix + '/sheets/<song>', interactive=False)
class SheetView(MyLonaView):
    def handle_request(self, request):
        p = re.compile(r'(\w+)-(\w*)-(\w*)-(\w*).(\w+)')
        songId, instrument, mod, page, suffix = p.match(request.match_info['song']).groups()
        songId, page = int(songId), int(page)

        fn = db.songs[songId].filename
        if not fn:
            return None

        ofn = f'{cfg.img_cache_path}{songId}-{instrument}-{mod}-{page}'

        if not Path(f"{ofn}-{page}.jpg").is_file():
            cmd = f'pdftoppm -jpeg -singlefile -f {page} -l {page} "{fn}" {ofn}'
            pages = subprocess.check_output(cmd, shell=True)

        return {
            'content_type': 'image/jpeg',
            'body': open(f'{ofn}.jpg', 'rb').read(),
        }

@app.route(cfg.url_prefix + '/client/')
class Client(MyLonaView):
    def on_view_event(self, e):
        if e.name == 'add' and e.data['playlistItem'].playlistId == self.activePlaylist:
            data = JSONEncoder().encode(e.data['playlistItem'])
            self.send_str(f"client:{e.name}:{data}")
        elif e.name == 'delete' and e.data['playlistItem'].playlistId == self.activePlaylist:
            data = JSONEncoder().encode(e.data['playlistItem'])
            self.send_str(f"client:{e.name}:{data}")
        elif e.name == 'play' and e.data['playlistItem'].playlistId == self.activePlaylist:
            data = JSONEncoder().encode(e.data['playlistItem'])
            self.send_str(f"client:{e.name}:{data}")
        elif e.name == "update" and e.data['playlistId'] == self.activePlaylist:
            playlistId = e.data['playlistId']
            data = JSONEncoder().encode({x:y for x,y in db.playlist[playlistId].items()})
            self.send_str(f"client:{e.name}:" + data)

    def handle_request(self, request):
        self.activePlaylist = None
        #print(self.connection)

class ClientMiddleware:
    def handle_request(self, data):
        if isinstance(data.view, Client):
            data.connection.view = data.view
            data.view.connection = data.connection
        return data

    def handle_websocket_message(self, data):
        server = data.server
        connection = data.connection
        message = data.message
        if message.startswith("client:"):
            _, cmd, d = message.split(":", 2)
            view = connection.view
            #print(cmd, d)
            if cmd == "get-songlist":
                js = JSONEncoder().encode({x:y for x,y in db.songs.items()})
                connection.send_str("client:songlist:" + js)
            elif cmd == "get-playlist":
                msg = json.JSONDecoder().decode(d)
                view.activePlaylist = msg['playlistId']
                js = JSONEncoder().encode({x:y for x,y in db.playlist[view.activePlaylist].items()})
                connection.send_str("client:playlist:" + js)
            elif cmd == "add":
                msg = json.JSONDecoder().decode(d)
                pli = db.newPlaylistItem(msg['playlistId'], db.songs[msg['songId']])
                trigger_view_event(server, 'add', {'playlistItem': pli})
            elif cmd == "delete":
                msg = json.JSONDecoder().decode(d)
                pli = [x for x in db.playlist[msg['playlistId']]['items'] if x.id == msg['id']][0]
                trigger_view_event(server, 'delete', {'playlistItem': pli})
            elif cmd == "move":
                msg = json.JSONDecoder().decode(d)
                pli = [x for x in db.playlist[msg['playlistId']]['items'] if x.id == msg['id']][0]
                if db.playlistItemMove(pli, msg['pos'], True):
                    trigger_view_event(server, 'update', msg)
            elif cmd == "play":
                msg = json.JSONDecoder().decode(d)
                offset = msg['off']
                playlistId = msg['playlistId']
                pli = db.get_currentPlaylistItem(playlistId)
                pli = db.get_playlistItemNeighbour(playlistId, pli, offset)
                if pli != None:
                    db.set_currentPlaylistItem(playlistId, pli)
                    trigger_view_event(server, 'play', {'playlistItem': pli})
        return data

def trigger_view_event(server, name, data, urls= ['/', '/client/', '/play/']):
    for url in urls:
        vc = server.get_view_class(url=cfg.url_prefix + url)
        #print(vc)
        if vc:
            server.fire_view_event(name, data, view_classes=vc)

class BootstrapThemeHTML(HTML):
    STATIC_FILES = [StyleSheet(
            name='bootstrap-darkly',
            path='static/bootstrap-darkly.min.css',
        )]

app.add_template('lona/frontend.js', """
    lona_context.add_disconnect_hook(function(lona_context, event) {
        document.querySelector('#lona').innerHTML = `
            Server disconnected <br> Trying to reconnect...
        `;

        setTimeout(function() {
            lona_context.reconnect();

        }, 2000);
    });
""")

db = Database()

app.settings.STATIC_URL_PREFIX = cfg.url_prefix + '/static/'
app.settings.MIDDLEWARES = [ClientMiddleware]
app.add_static_file('lona/style.css', """ """)
app.run(host=cfg.addr, port=cfg.port)
