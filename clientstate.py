import threading
import defines
import utils
import q3huff

class userinfo(dict): 
    def serialize(self):
        output = "\""
        for key, value in self.items():
            output += "\\{}\\{}".format(key, value)
        output += "\""
        return output

    def deserialize(self, text):
        self.clear()
        chunks = text.strip("\"").split('\\')
        it = iter(chunks[1:])
        for key in it:
            self.update( {key : next(it)} )

class gamestate:
    _lock = threading.Lock()

    def __init__(self, host, port, uinfo: userinfo = None) -> None:
        self._state         = defines.connstate_t.CA_DISCONNECTED
        self._challenge     = 0 # proto 71
        self._message_seq   = 0 # clc.serverMessageSequence
        self._command_seq   = 0 # clc.serverCommandSequence
        self._server_id     = 0 # used
        self._server_time   = 0 # ???
        self._userinfo      = self.__default_userinfo() if not uinfo else uinfo
        self._reliable_ack  = 0 # clc.reliableAcknowledge
        self._reliable_seq  = 0 # clc.reliableSequence
        self._pure          = False
        self._checksum_feed = 0
        self._reliable_commands = ["" for x in range(defines.MAX_RELIABLE_COMMANDS)]
        self._server_commands   = ["" for x in range(defines.MAX_RELIABLE_COMMANDS)]
        self._server_host   = host
        self._server_port   = port

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

    def is_connected(self) -> bool:
        return self._state.value >= defines.connstate_t.CA_CONNECTED.value

class events_handler:

    def event_connected(self, srv_id: int):
        pass # stub

    def event_disconnected(self, reason: str):
        pass # stub

    def event_packet(self, packet):
        pass # stub

    def event_command(self, seq: int, cmd: str):
        pass # stub

    def event_configstring(self, inx: int, txt: str):
        pass # stub

class evaluator(gamestate):
    def __init__(self, handler: events_handler, uinfo: userinfo, host, port) -> None:
        super().__init__(host, port, uinfo)
        self._handler = handler()

    @property
    def gamestate(self) -> gamestate:
        return self

    def execute(self, packet):
        if utils.connection_sequence(packet.sequence):
            self._execute_connected(packet)
        else:
            self._execute_connection_less(packet)
    
    def queue_command(self, command: str) -> int:
        with self._lock:
            self._reliable_seq += 1
            inx = self._reliable_seq % 64
            self._reliable_commands[inx] = command
            return self._reliable_seq

    def change_state(self, to, frm = None):
        with self._lock:
            if frm and self._state != frm:
                raise Exception(f"Current state {self._state} != {frm}")
            self._state = to

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
            #TODO: check is the sequence is valid, we put the same sequence in the bottom
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

            packet = bytearray(b"" \
                + sequence.to_bytes(4, "little", signed=True) \
                + self._server_port.to_bytes(2, "little", signed=False) \
                + writer.data)

            self.__encrypt_packet(server_id, sequence, command_seq, packet)

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
            if ack != self._reliable_ack:
                pass#TODO: wtf?
            self._reliable_ack = ack

            return tail
    
    def _execute_connection_less(self, packet):
        # Notify event handler
        self._handler.event_command(packet.sequence, packet.data)

        with self._lock:
            # Step 1: getting challenge
            if self._state == defines.connstate_t.CA_CONNECTING:
                if packet.command == "challengeResponse":
                    self._challenge = packet.data[0]
                    self._state = defines.connstate_t.CA_CHALLENGING

            # Step 2: connection approval
            if self._state == defines.connstate_t.CA_CHALLENGING:
                if packet.command == "connectResponse" and self._challenge == packet.data:
                    self._state = defines.connstate_t.CA_CONNECTED

    def _execute_connected(self, packet):
        with self._lock:
            # Step 3: connection established
            if self._state == defines.connstate_t.CA_CONNECTED:
                self._state = defines.connstate_t.CA_PRIMED

            # Load config string
            cfgstr = packet.config_string
            if defines.configstr_t.CS_SYSTEMINFO.value in cfgstr:
                ui = userinfo()
                ui.deserialize( cfgstr[ defines.configstr_t.CS_SYSTEMINFO.value ] )
                self._server_id = int(ui['sv_serverid'])
                if 'sv_pure' in ui.keys():
                    self._pure = bool(int(ui['sv_pure']))
            
                # Step 4: make connection completed on the first gamestate frame
                if self._state == defines.connstate_t.CA_PRIMED:
                    self._state = defines.connstate_t.CA_ACTIVE
                    self._handler.event_connected(self._server_id)

            for inx, cfg in cfgstr.items():
                self._handler.event_configstring(inx, cfg)
            
            # Load commands
            prev = -1
            for seq, txt in packet.commands:
                if seq > self._command_seq:
                    assert(prev == -1 or prev + 1 == seq)
                    self._handler.event_command(seq, txt)
                    self._server_commands[seq % 64] = txt
                    prev = seq

            if packet.command_seq > self._command_seq:
                 #assert(packet.command_seq == self.gamestate.command_seq + 1)
                 self._command_seq = packet.command_seq

            if packet.snapshot:
                self._server_time = packet.snapshot.server_time

            if packet.checksum_feed:
                self._checksum_feed = packet.checksum_feed
                if self._pure:
                    #TODO: generate checksum
                    #self.queue_command("cp {} {} {} @ {}".format(
                    #    self.gamestate.server_id,
                    #    -680722472, #osp cgame checksum
                    #    -226345602, #osp cgame checksum
                    #    self.gamestate.checksum_feed
                    #))
                    pass

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

