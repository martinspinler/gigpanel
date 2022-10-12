#!/usr/bin/python3
import sys
import time
import threading

from typing import List, Tuple, Union, Any, Iterable

from pythonosc import osc_packet
from pythonosc.osc_message_builder import OscMessageBuilder

import socket
import threading
import socketserver


import mido
from mido import Message

class RolandClient():
    def __init__(self, clients):
        self.clients = clients
        self.pedal_on = None

        self.portout = None
        self.portin  = None

    def connect(self, name):
        def find_substr(strings, substr):
            for i in strings:
                if substr in i:
                    return i
            raise FileNotFoundError(f"MIDI: {name}")

        portin_name  = find_substr(mido.get_input_names(), name)
        portout_name = find_substr(mido.get_output_names(), name)

        self.portout = mido.open_output(portout_name)
        self.portin  = mido.open_input(portin_name)
        self.portin.callback = self.input_callback

    def drawbar_handler(self, addr, args, value):
        #self.send(Message('sysex', data = [0x40, 0x41, 0x51, 0x00, 0x01] + drawbars))
        pass

    def send(self, msg):
        print(msg)
        self.portout.send(msg)

    def roland_sysex(self, data):
        print("RS", data)
        return Message('sysex', data = ([0x41, 0x10, 0x42, 0x12] + data + [(128 - sum(data)) & 0x7F]))
        #return ([0xF0, 0x41, 0x10, 0x42, 0x12] + data + [128 - (sum(data) & 0x7F), 0xF7])
        #f.send(Message('sysex', data = [0x40, 0x41, 0x51, 0x00, 0x01] + drawbars))


    def input_callback(self, msg):
        if msg.type == 'clock':
            return

        print(msg)
        if msg.type == 'control_change' and msg.control == 67: # SOFT pedal
            if self.pedal_on == None and msg.value > 0:
                self.pedal_on = time.time()
            elif self.pedal_on != None and msg.value == 0:
                diff = time.time() - self.pedal_on
                self.pedal_on = None
                for c in self.clients:
                    c.send_message("/next" if diff < 0.5 else "/prev", 1.0)


class ThreadedTCPOSCRequestHandler(socketserver.BaseRequestHandler):
    def setup(self):
        print("OSC TCP client connected")
        self.server.clients.append(self)

    def handle(self):
        while True:
            sz = self.request.recv(4)
            if not sz:
                break
            data = self.request.recv(int.from_bytes(sz, byteorder='little'))
            for m in osc_packet.OscPacket(data).messages:
                self.handle_message(m.message.address, m.message.params)


    def finish(self):
        self.server.clients.remove(self)
        print("OSC TCP client disconnected")

    def handle_message(self, address, params):
        rc = self.server.rc
        print(address, params)

        if address == "/6/button3":
            rc.send(mido.Message('note_on' if params[0] else 'note_off', note=60))
            rc.send(rc.roland_sysex([64,65,35,0,64,50,64,50,0]))
        if address == "/6/fader32":
            p = int(params[0]*127)
            print(p, params[0])
            rc.send(rc.roland_sysex([0x40, 0,0x04, int(params[0]*127)]))
        if address == "/6/button1":
            #rc.send(mido.Message('program_change', program = 0))
            #rc.send(rc.roland_sysex([0x40, 0x11, 0x00, 0x00, 0x68]))
            #rc.send(rc.roland_sysex([0x40, 0x11, 0x13, 0x01]))
            rc.send(rc.roland_sysex([0x40, 0x11, 0x00, 0x00, 0x0]))

        if address == "/6/button2":
            #rc.send(mido.Message('note_on' if params[0] else 'note_off', note=60))
            #rc.send(rc.roland_sysex(
            #rc.send(mido.Message('control_change', channel = 0, control = 0, value=0))
            #rc.send(mido.Message('control_change', channel = 0, control = 32, value=67))
            #rc.send(mido.Message('program_change', channel = 0, program = 4))
            #rc.send(mido.Message('program_change', program = 4))
            #rc.send(mido.Message('control_change', channel = 0, control = 7, value=32 if params[0] else 120))
            #rc.send(rc.roland_sysex([0x40, 0x11, 0x00, 0x00]))
            rc.send(rc.roland_sysex([0x40, 0x11, 0x00, 0x04, 0x4]))
            #for i in range(16):
            #    rc.send(rc.roland_sysex([0x40, 0x10 + i, 0x13, 0x00]))
        pass

    def send_message(self, address: str, value: Union[int, float, bytes, str, bool, tuple, list]) -> None:
        builder = OscMessageBuilder(address=address)
        if value is None:
            values = []
        elif not isinstance(value, Iterable) or isinstance(value, (str, bytes)):
            values = [value]
        else:
            values = value
        for val in values:
            builder.add_arg(val)
        msg = builder.build()
        try:
            self.request.sendall(msg.size.to_bytes(length=4, byteorder='little') + msg._dgram)
        except:
            pass

class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True

class RolandTCPServer():
    def __init__(self, addr):
        self.clients = []

        rc = RolandClient(self.clients)

        self.server = ThreadedTCPServer(addr, ThreadedTCPOSCRequestHandler)
        self.server.clients = self.clients
        self.server.rc = rc
        server_thread = threading.Thread(target=self.server.serve_forever)
        server_thread.daemon = True
        server_thread.start()

        while not rc.portin:
            try:
                rc.connect("Roland")
                #rc.connect("VMPK")
            except FileNotFoundError as e:
                time.sleep(0.1)
        print("MIDO connected")

    def shutdown(self):
        self.server.shutdown()

if __name__ == "__main__":
    addr = "0.0.0.0", 4300
    rc = RolandTCPServer(addr)
    
    try:
        while True:
            time.sleep(0.1)
    except KeyboardInterrupt:
        rc.shutdown()
        raise
