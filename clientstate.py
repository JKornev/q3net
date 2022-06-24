import threading
import random
import collections
import defines
import packets
import shlex
import utils
import q3huff

class userinfo(collections.OrderedDict): 
    def serialize(self):
        output = "\""
        for key, value in self.items():
            output += "\\{}\\{}".format(key, value)
        output += "\""
        return output

    def deserialize(self, text):
        self.clear()
        chunks = text.strip("\"").split('\\')
        if not chunks[0]:
            it = iter(chunks[1:])
        else:
            it = iter(chunks)
        for key in it:
            self.update( {key : next(it)} )

class _gamestate_base:
    def __init__(self, host, port) -> None:
        self._state         = defines.connstate_t.CA_DISCONNECTED
        self._server_host   = host
        self._server_port   = port
        self._userinfo      = self.__default_userinfo()
        self._qport         = random.randint(0, 0xFFFF)
        self._reset_state()

    def _reset_state(self):
        self._challenge         = 0 # proto 71
        self._message_seq       = 0 # clc.serverMessageSequence
        self._command_seq       = 0 # clc.serverCommandSequence
        self._outgoing_seq      = 1 # chan->outgoingSequence
        self._server_id         = 0 # used
        self._server_time       = 0 # ???
        self._reliable_ack      = 0 # clc.reliableAcknowledge
        self._reliable_seq      = 0 # clc.reliableSequence
        self._pure              = False
        self._pure_ack          = False
        self._checksum_feed     = 0
        self._reliable_commands = ["" for x in range(defines.MAX_RELIABLE_COMMANDS)]
        self._server_commands   = ["" for x in range(defines.MAX_RELIABLE_COMMANDS)]
        self._config_strings    = collections.OrderedDict()
        self._mode              = 'baseq3'

    def __default_userinfo(self):
        ui = userinfo()
        ui['client']         = 'Q3 1.32b'
        ui['name']           = 'UnnamedPlayer'
        ui['model']          = 'sarge'
        ui['headmodel']      = 'sarge'
        ui['team_model']     = 'james'
        ui['team_headmodel'] = 'james'
        ui['handicap']       = 100
        ui['teamtask']       = 0
        ui['sex']            = 'male'
        ui['color1']         = 1
        ui['color2']         = 2
        ui['rate']           = 25000
        ui['snaps']          = 40
        ui['cl_maxpackets']  = 125
        ui['cl_timeNudge']   = 0
        ui['cl_anonymous']   = 0
        return ui

class gamestate(_gamestate_base):
    def __init__(self, host, port) -> None:
        self._lock = threading.RLock()
        super().__init__(host, port)

    @property
    def conn_state(self):
        with self._lock:
            return self._state

    @property
    def challenge(self):
        with self._lock:
            return self._challenge

    @property
    def message_seq(self):
        with self._lock:
            return self._message_seq
    
    @property
    def command_seq(self):
        with self._lock:
            return self._command_seq
    
    @property
    def server_id(self):
        with self._lock:
            return self._server_id

    @property
    def server_time(self):
        with self._lock:
            return self._server_time

    @property
    def userinfo(self):
        with self._lock:
            return self._userinfo

    @property
    def reliable_ack(self):
        with self._lock:
            return self._reliable_ack

    @property
    def reliable_seq(self):
        with self._lock:
            return self._reliable_seq

    @property
    def checksum_feed(self):
        with self._lock:
            return self._checksum_feed

    @property
    def server_host(self):
        with self._lock:
            return self._server_host

    @property
    def server_port(self):
        with self._lock:
            return self._server_port

    @property
    def qport(self):
        with self._lock:
            return self._qport

    @property
    def mode(self):
        with self._lock:
            return self._mode
    
    def config_string(self, inx):
        with self._lock:
            if inx in self._config_strings:
                return self._config_strings[inx]
            return None

    def is_connected(self) -> bool:
        with self._lock:
            return self._state.value >= defines.connstate_t.CA_CONNECTED.value

    def queue_command(self, command: str) -> int:
        with self._lock:
            assert(64 > self._reliable_seq - self._reliable_ack)
            self._reliable_seq += 1
            inx = self._reliable_seq % 64
            self._reliable_commands[inx] = command
            return self._reliable_seq

class events_handler:
    def __init__(self) -> None:
        pass

    def event_connected(self, gamestate: gamestate, host: str, port: int, srv_id: int):
        pass # stub

    def event_disconnected(self, gamestate: gamestate, reason: str):
        pass # stub

    def event_packet(self, gamestate: gamestate, packet: packets.server_packet):
        pass # stub

    def event_command(self, gamestate: gamestate, seq: int, cmd: str):
        pass # stub

    def event_configstring(self, gamestate: gamestate, inx: int, txt: str):
        pass # stub

class evaluator(gamestate):
    def __init__(self, handler: events_handler, host, port) -> None:
        super().__init__(host, port)
        self._handler = handler

    @property
    def gamestate(self) -> gamestate:
        return self 

    def execute(self, packet):
        # Notify about a new packet
        self._handler.event_packet(self, packet)

        if utils.connection_sequence(packet.sequence):
            self._execute_connected(packet)
        else:
            self._execute_connection_less(packet)

    def disconnect(self):
        self.change_state(defines.connstate_t.CA_DISCONNECTED)

    def change_state(self, to, frm = None):
        with self._lock:
            if frm and self._state != frm:
                raise Exception(f"Current state {self._state} != {frm}")

            if to == defines.connstate_t.CA_DISCONNECTED and self._state == defines.connstate_t.CA_ACTIVE:
                self._handler.event_disconnected(self, "manual")

            self._state = to

    def set_player_profile(self, userinfo):
        with self._lock:
            self._userinfo = userinfo

    def generate_client_frame(self):
        # No connection - no need send frame
        if not self.gamestate.is_connected():
            return None

        with self._lock:
            # 4	sequence number
            # 2	qport
            # 4	serverid
            # 4	acknowledged sequence number
            # 4	clc.serverCommandSequence
            # <optional reliable commands>
            # 1	clc_move or clc_moveNoDelta
            # 1	command count
            # <count * usercmds>

            server_id   = self._server_id
            sequence    = self._message_seq
            command_seq = self._command_seq

            writer = q3huff.Writer()
            writer.oob = False
            
            writer.write_long(server_id)    # serverid
            writer.write_long(sequence)     # messageAcknowledge - usermove encryption
            writer.write_long(command_seq)  # reliableAcknowledge - usermove\msg encryption

            # commands
            for i in range(self._reliable_ack + 1, self._reliable_seq + 1):
                inx = i % 64
                writer.write_byte(defines.clc_ops_e.clc_clientCommand.value)
                writer.write_long(i)
                writer.write_string(self._reliable_commands[inx])

            # usermove
            writer.write_byte(defines.clc_ops_e.clc_moveNoDelta.value)
            writer.write_byte(1) # cmd count
            if self._server_time == 0:
                writer.write_bits(1, 1) # time delta bit
                writer.write_bits(1, 8) # delta
            else:
                writer.write_bits(0, 1) # no time delta bit
                writer.write_long(self._server_time + 100)
            writer.write_bits(0, 1) # no changes

            writer.write_byte(defines.clc_ops_e.clc_EOF.value)

            packet = bytearray(b"" \
                + self._outgoing_seq.to_bytes(4, "little", signed=True) \
                + self._qport.to_bytes(2, "little", signed=False) \
                + writer.data)

            self.__encrypt_packet(server_id, sequence, command_seq, packet)

            self._outgoing_seq += 1

            return packet

    def decrypt_server_frame(self, sequence, packet, size):
        with self._lock:

            if self._message_seq + 1 > sequence:
                return None
            
            raw = self.__decrypt_packet( sequence, packet.read_data(size) )

            # Decode tail
            tail = utils.reader(raw)
            tail.compression(True)
            self._message_seq = sequence
            ack = tail.read_uint()
            self._reliable_ack = ack

            #Note: not sure why it works this way but the hack is implemented in an engine source
            if self._reliable_ack < self._reliable_seq - defines.MAX_RELIABLE_COMMANDS:
                self._reliable_ack = self._reliable_seq

            return tail
    
    def _execute_connection_less(self, packet):
        # Notify event handler
        if packet.data:
            self._handler.event_command(self, packet.sequence, packet.data)

        with self._lock:
            # Step 1: getting challenge
            if self._state == defines.connstate_t.CA_CONNECTING:
                if packet.command == "challengeResponse":
                    self._reset_state()
                    self._challenge = packet.data[0]
                    self._state = defines.connstate_t.CA_CHALLENGING

            # Step 2: connection approval
            if self._state == defines.connstate_t.CA_CHALLENGING:
                if packet.command == "connectResponse" and (not packet.data or self._challenge == packet.data):
                    self._state = defines.connstate_t.CA_CONNECTED


    def _execute_connected(self, packet):
        with self._lock:
            # No need handle connected packets without connection
            if self._state == defines.connstate_t.CA_DISCONNECTED:
                return

            # Step 3: connection established
            if self._state == defines.connstate_t.CA_CONNECTED:
                self._state = defines.connstate_t.CA_PRIMED

            # Load config string
            for inx, cfg in packet.config_string.items():
                self.__load_config_string(inx, cfg)

                if defines.configstr_t.CS_SYSTEMINFO.value == inx:
                    # Step 4: make connection completed on the first gamestate frame
                    if self._state == defines.connstate_t.CA_PRIMED:
                        self._state = defines.connstate_t.CA_ACTIVE
                        self._handler.event_connected(self, self._server_host, self._server_port, self._server_id)

            # Load commands
            prev = -1
            disconnect = False
            disconnect_reason = None
            for seq, txt in packet.commands:
                if seq > self._command_seq:
                    assert(prev == -1 or prev + 1 == seq)
                    self._handler.event_command(self, seq, txt)
                    self._server_commands[seq % 64] = txt
                    prev = seq

                    # Step 5: disconnect when server kicks us
                    if txt.startswith("disconnect"):
                        tokens = shlex.split(txt, posix= False)
                        if len(tokens) > 1:
                            disconnect_reason = tokens[1].strip('\"')
                        else:
                            disconnect_reason = "no reason"
                        disconnect = True
                    elif txt.startswith("cs "):
                        tokens = shlex.split(txt, posix= False)
                        if len(tokens) >= 3:
                            key = int(tokens[1])
                            value = tokens[2].strip('\"')
                            self.__load_config_string(key, value)

            if packet.command_seq > self._command_seq:
                 #assert(packet.command_seq == self.gamestate.command_seq + 1)
                 self._command_seq = packet.command_seq

            if packet.snapshot:
                self._server_time = packet.snapshot.server_time

            if packet.checksum_feed:
                self._checksum_feed = packet.checksum_feed
                if self._pure and not self._pure_ack:
                    self._pure_ack = True
                    self.queue_command(self.__get_pure_checksums_packet("osp"))
            
            if disconnect:
                self._handler.event_disconnected(self, disconnect_reason)
                self._state = defines.connstate_t.CA_DISCONNECTED

    def __load_config_string(self, index, value):
        if not value:
            if index in self._config_strings:
                self._handler.event_configstring(self, index, None)
                self._config_strings.pop(index)
            return

        if defines.configstr_t.CS_SYSTEMINFO.value == index:
            ui = userinfo()
            ui.deserialize(value)
            self._server_id = int(ui['sv_serverid'])
            if 'sv_pure' in ui.keys():
                self._pure = bool(int(ui['sv_pure']))
            if 'fs_game' in ui.keys():
                self._mode = ui['fs_game']

        self._handler.event_configstring(self, index, value)
        self._config_strings[index] = value

    def __encrypt_packet(self, server_id, sequence, command_seq, packet):
        CL_ENCODE_START = 18

        index = 0
        str = self._server_commands[command_seq % 64] + "\x00"
        key = (self._challenge ^ sequence ^ server_id) & 0xFF
        for i in range(CL_ENCODE_START, len(packet)):
            if index >= len(str) or str[index] == '\x00':
                index = 0

            str_key = int.from_bytes( str[index].encode(), "little", signed=False ) & 0xFF
            if str_key > 127 or str_key == 37: # 37 == '%', x > 127 - unprintable chars
                str_key = 46 # 46 == '.'

            key ^= (str_key << (i & 1)) & 0xFF
            packet[i] = (packet[i] ^ key)
            index += 1

    def __decrypt_packet(self, sequence, packet):
        CL_DECODE_START = 4

        tail = q3huff.Reader(packet)
        tail.oob = False
        reliable_ack = tail.read_long()

        index = 0
        str = self._reliable_commands[reliable_ack % 64] + "\x00"
        key = (self._challenge ^ sequence) & 0xFF

        for i in range(CL_DECODE_START, len(packet)):
            if index >= len(str) or str[index] == '\x00':
                index = 0
            
            str_key = int.from_bytes( str[index].encode(), "little", signed=False ) & 0xFF
            if str_key > 127 or str_key == 37: # 37 == '%', x > 127 - unprintable chars
                str_key = 46 # 46 == '.'
            
            key ^= (str_key << (i & 1)) & 0xFF
            packet[i] = (packet[i] ^ key)
            index += 1

        return packet

    def __get_pure_checksums_packet(self, mode):
        feed = self.gamestate.checksum_feed
        cgame = utils.calculate_checksum(mode, "cgame", feed)
        ui    = utils.calculate_checksum(mode, "ui", feed)
        return "cp {} {} {} @ {}".format( self.gamestate.server_id, cgame, ui, feed )
