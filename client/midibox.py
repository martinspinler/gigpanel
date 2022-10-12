class MidiBox():
    programs = {          #PC MSB LSB
        'Piano'         : ( 1,  0, 68, [[0x40, 0x40, 0x23, 0x00, 0x40, 0x32, 0x40, 0x32, 0x00]]),
        'Vintage EP'    : ( 5,  0, 67, [[0x40, 0x40, 0x23, 0x01, 0x42, 0x00, 0x40, 0x37, 0x02]]),
        'AcousticBass'  : (33,  0, 71, [[0x40, 0x40, 0x23, 0x00, 0x00, 0x00, 0x00, 0x08, 0x04]]),
        'hammond'       : (17, 32, 68, [[0x40, 0x40, 0x23, 0x01, 0x22, 0x00, 0x40, 0x00, 0x7F]]),
        'Vibraphone'    : (12,  0,  0, [[0x40, 0x40, 0x23, 0x01, 0x22, 0x00, 0x40, 0x00, 0x7F]]),
        'Marimba'       : (12,  0,  0, [[0x40, 0x40, 0x23, 0x01, 0x22, 0x00, 0x40, 0x00, 0x7F]]),
        'FretlessBass'  : (36,  0,  0, [[0x40, 0x40, 0x23, 0x00, 0x00, 0x00, 0x00, 0x08, 0x04]]),
    }

    def __init__(self, w):
        self.midiin = rtmidi.MidiIn(name = "GigPanel")
        self.midiout = rtmidi.MidiOut(name = "GigPanel")
        self.midiin.open_virtual_port("MB Input")
        self.midiout.open_virtual_port("MB Output")
        self.midiin.ignore_types(False, False, False)

        self.timer = QTimer(w)
        self.timer.timeout.connect(self.poll)
        self.timer.start(50)

    def _write(self, data):
        self.midiout.send_message(data)

    def _send_sysex(self, sysex):
        return self._write(sysex)

    def setProgram(self, ch, value):
        #if value == self._program:
        #    return
        assert value in self.programs
        #self._program = value
        p = self.programs[value]
        pc, msb, lsb = p[0], p[1], p[2]

        self.cc(ch, 0, msb)
        self.cc(ch, 32, lsb)
        self.pc(ch, pc-1)

        for sysex in p[3]:
            sysex[1] = 0x40 | (ch + 1)
            self.roland_sysex(sysex)


    def note_on(self, channel, note, vel):
        self._write([0x90 | (channel & 0xF), note & 0x7F, vel & 0x7F])

    def note_off(self, channel, note, vel):
        self._write([0x80 | (channel & 0xF), note & 0x7F, vel & 0x7F])

    def cc(self, channel, cc, val):
        self._write([0xB0 | (channel & 0xF), cc & 0x7F, val& 0x7F])

    def pc(self, channel, pgm):
        self._write([0xC0 | (channel & 0xF), pgm & 0x7F])

    def roland_sysex(self, data):
        self._send_sysex([0xF0, 0x41, 0x10, 0x42, 0x12] + data + [128 - (sum(data) & 0x7F), 0xF7])

    def poll(self):
        _msg = self.midiin.get_message()
        while _msg:
            message, deltatime = _msg
            _msg = self.midiin.get_message()
            self.input_callback(message)

    def input_callback(self, msg):
        pass


    def setRegistration(self, name):
        #print("Set registration:", name)
        prgs = name.split('+')
        if len(prgs) == 2:
            channels = [1, 3]
        elif len(prgs) == 3:
            channels = [1, 3, 4]
        else:
            channels = [1]
        for i in range(len(prgs)):
            self.setProgram(channels[i], prgs[i])

class MidiBoxGPWrapper():
    def __init__(self, gp):
        self.midiin = rtmidi.MidiIn(name = "GigPanel")
        self.midiout = rtmidi.MidiOut(name = "GigPanel")
        self.midiin.open_virtual_port("MB Input")
        self.midiout.open_virtual_port("MB Output")
        self.midiin.ignore_types(False, False, False)

        self.gp = gp

        self.timer = QTimer(w)
        self.timer.timeout.connect(self.poll)
        self.timer.start(50)

    def poll(self):
        _msg = self.midiin.get_message()
        while _msg:
            message, deltatime = _msg
            _msg = self.midiin.get_message()
            self.input_callback(message)

    def input_callback(self, msg):
        if msg[1] == 0x01:
            btn = msg[2]
            if self.gp.ext_input_cb:
                self.gp.ext_input_cb[-1](btn)

