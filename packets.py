import clientstate
import defines

# ========================
#   Common packet

class server_packet:
    def __init__(self, data = None, command = None, sequence = -1) -> None:
        self.sequence = sequence
        self.command = command
        self.data = data

class server_frame(server_packet):
    def __init__(self, sequence) -> None:
        super().__init__(sequence = sequence)
        self.baselines = []
        self.config_string = {}
        self.commands = []
        self.command_seq = 0
        self.snapshot = None
        self.checksum_feed = None

# ========================
#   Parsers

class parser_base:
    _command = None

    def __init__(self, command = None) -> None:
        self._command = command

    def equal(self, command):
        return command == self._command

    def parse(self, packet):
        raise NotImplementedError

class parser_unknown(parser_base):
    def equal(self, command):
        return True # any packet is unknown in the end of the check

    def parse(self, packet):
        return server_packet(packet, self._command) 

class parser_print(parser_base):
    def __init__(self) -> None:
        super().__init__("print")

    def parse(self, packet):
        tokens = packet.split('\n', 1)
        assert(len(tokens) == 2)
        return server_packet( tokens[1].rstrip(), self._command ) #TODO: return print packet

class parse_status(parser_base):
    def __init__(self) -> None:
        super().__init__("statusResponse")

    def parse(self, packet):
        lines = packet.splitlines()
        assert(len(lines) >= 2)

        info = clientstate.userinfo()
        info.deserialize(lines[1])

        players = []
        for i in range(2, len(lines)):
            fields = lines[i].split(maxsplit=2)
            assert(len(fields) == 3)
            players.append((int(fields[0]), int(fields[1]), fields[2].strip("\"")))

        return server_packet( (info, players), self._command)

class parse_info(parser_base):
    def __init__(self) -> None:
        super().__init__("infoResponse")

    def parse(self, packet):
        lines = packet.splitlines()
        assert(len(lines) == 2)
        ui = clientstate.userinfo()
        ui.deserialize(lines[1])
        return server_packet(ui, self._command) 

class parse_challenge(parser_base):
    def __init__(self) -> None:
        super().__init__("challengeResponse")

    def parse(self, packet):
        tokens = packet.split()

        count = len(tokens)
        assert(2 <= count <= 4)

        challenge = int(tokens[1])

        clientChallenge = 0
        if count >= 3:
            clientChallenge = int(tokens[2])

        protocol = 68 # default version
        if count >= 4:
            protocol = int(tokens[3])

        return server_packet( (challenge, clientChallenge, protocol), self._command )

class parse_connect(parser_base):
    def __init__(self) -> None:
        super().__init__("connectResponse")

    def parse(self, packet):
        tokens = packet.split()
        count = len(tokens)
        assert(count == 2)
        return server_packet(int(tokens[1]), self._command)

# ========================
#   Server frame parser

class parse_server_frame(parser_base):
    def __init__(self) -> None:
        super().__init__(None)

    def parse(self, sequence, packet):
        frame = server_frame(sequence)

        while True:
            cmd = packet.read_uchar()

            if cmd == defines.svc_ops_e.svc_nop.value:
                continue
            elif cmd == defines.svc_ops_e.svc_EOF.value or cmd == -1:
                break
            elif cmd == defines.svc_ops_e.svc_gamestate.value:
                gs = server_gamestate(packet)
                frame.config_string.update(gs.config_string)
                frame.baselines.extend(gs.baselines)
                self.checksum_feed = gs.checksum_feed
                if gs.sequence > frame.command_seq:
                    frame.command_seq = gs.sequence
            elif cmd == defines.svc_ops_e.svc_configstring.value:
                inx = packet.read_ushort()
                value = packet.read_bigstring()
                frame.config_string[inx] = value
            elif cmd == defines.svc_ops_e.svc_baseline.value:
                frame.baselines.append( entity_state(packet) )
            elif cmd == defines.svc_ops_e.svc_serverCommand.value:
                seq = packet.read_uint() # reliableAcknowledge
                txt = packet.read_string()
                frame.commands.append((seq, txt.strip()))
                if seq > frame.command_seq:
                    frame.command_seq = seq
            elif cmd == defines.svc_ops_e.svc_download.value:
                break
            elif cmd == defines.svc_ops_e.svc_snapshot.value:
                frame.snapshot = server_snapshot(packet)
            elif cmd == defines.svc_ops_e.svc_voipSpeex.value:
                assert(False)
                break
            elif cmd == defines.svc_ops_e.svc_voipOpus.value:
                assert(False)
                break
            else:
                assert(False)
                break
        
        return frame

class server_snapshot:
    def __init__(self, packet):
        self.server_time = packet.read_int()

        self.delta_num  = packet.read_uchar()
        self.snap_flags = packet.read_uchar()
        self.area_bytes = packet.read_uchar()
        self.area_mask  = packet.read_data(self.area_bytes)

        # Player state
        self.player_state = player_state(packet)

        # Packet entities
        self.entities = []
        while True:
            entity = entity_state(packet)
            if entity.number == (1 << 10) - 1:
                break
            self.entities.append(entity)

class server_gamestate:
    config_string = {}
    baselines = []

    def __init__(self, packet) -> None:
        self.sequence = int.from_bytes(packet.read_data(4), "little")

        while True:
            cmd = packet.read_uchar()
            assert(
                cmd == defines.svc_ops_e.svc_EOF.value 
                or cmd == defines.svc_ops_e.svc_configstring.value 
                or cmd == defines.svc_ops_e.svc_baseline.value
            )
            if cmd == defines.svc_ops_e.svc_EOF.value:
                break
            elif cmd == defines.svc_ops_e.svc_configstring.value:
                inx = packet.read_ushort()
                value = packet.read_bigstring()
                self.config_string[inx] = value
            elif cmd == defines.svc_ops_e.svc_baseline.value:
                self.baselines.append( entity_state(packet) )

        self.client_num = packet.read_uint()
        self.checksum_feed = packet.read_uint()

class player_state_field:
    def __init__(self, bits, signed = False):
        self.value = None
        self.__bits = bits
        self.__signed = signed

    def load_value(self, packet):
        if self.__bits:
            self.value = packet.read_bits(self.__bits)
        else:
            big = packet.read_bits(1)
            if not big:
                self.value = packet.read_bits(13)
            else:
                self.value = packet.read_bits(32)

# ========================
#   Player state parser

class player_state(list):
    state = []
    stats = []
    persistant = []
    ammo = []
    powerups = []

    def __init__(self, packet):
        self.__load_struct_config()

        fields = packet.read_uchar()
        assert(fields < len(self))

        for i in range(fields):
            entry = self.__getitem__(i)
            
            loaded = packet.read_bits(1)
            if not loaded:
                continue
            
            entry.load_value(packet)
            self.state.append((i, packet))

        # player states 
        if not packet.read_bits(1):
            return

        if packet.read_bits(1): # stats
            bits = packet.read_bits(16)
            for i in range(16):
                if bits & (1<<i):
                    self.stats.append((i, packet.read_ushort()))

        if packet.read_bits(1): # persistant
            bits = packet.read_bits(16)
            for i in range(16):
                if bits & (1<<i):
                    self.persistant.append((i, packet.read_ushort()))

        if packet.read_bits(1): # ammo
            bits = packet.read_bits(16)
            for i in range(16):
                if bits & (1<<i):
                    self.ammo.append((i, packet.read_ushort()))

        if packet.read_bits(1): # powerups
            bits = packet.read_bits(16)
            for i in range(16):
                if bits & (1<<i):
                    self.powerups.append((i, packet.read_uint()))

    def __load_struct_config(self):
        self.append(player_state_field(32))
        self.append(player_state_field(0))
        self.append(player_state_field(0))
        self.append(player_state_field(8))
        self.append(player_state_field(0))
        self.append(player_state_field(0))
        self.append(player_state_field(0))
        self.append(player_state_field(0))
        self.append(player_state_field(16, True))
        self.append(player_state_field(0))
        self.append(player_state_field(0))
        self.append(player_state_field(8))
        self.append(player_state_field(16, True))
        self.append(player_state_field(16))
        self.append(player_state_field(8))
        self.append(player_state_field(4))
        self.append(player_state_field(8))
        self.append(player_state_field(8))
        self.append(player_state_field(8))
        self.append(player_state_field(16))
        self.append(player_state_field(10))
        self.append(player_state_field(4))
        self.append(player_state_field(16))
        self.append(player_state_field(10))
        self.append(player_state_field(16))
        self.append(player_state_field(16))
        self.append(player_state_field(16))
        self.append(player_state_field(8))
        self.append(player_state_field(8, True))
        self.append(player_state_field(8))
        self.append(player_state_field(8))
        self.append(player_state_field(8))
        self.append(player_state_field(8))
        self.append(player_state_field(8))
        self.append(player_state_field(8))
        self.append(player_state_field(16))
        self.append(player_state_field(16))
        self.append(player_state_field(12))
        self.append(player_state_field(8))
        self.append(player_state_field(8))
        self.append(player_state_field(8))
        self.append(player_state_field(5))
        self.append(player_state_field(0))
        self.append(player_state_field(0))
        self.append(player_state_field(0))
        self.append(player_state_field(0))
        self.append(player_state_field(10))
        self.append(player_state_field(16))

# ========================
#   Entity packet parser

class entity_state_field:
    def __init__(self, bits, signed = False):
        self.value = None
        self.__bits = bits
        self.__signed = signed

    def load_value(self, packet):
        if not packet.read_bits(1): # null check 
            self.value = 0
            return

        if self.__bits:
            self.value = packet.read_bits(self.__bits)
        else:
            big = packet.read_bits(1)
            if not big:
                self.value = packet.read_bits(13)
            else:
                self.value = packet.read_bits(32)

class entity_state(list):
    def __init__(self, packet):
        self.__load_struct_config()

        self.number = packet.read_bits(10)
        #assert( self.number <= (1 << 10) )

        if self.number == (1 << 10) - 1: #eof
            return

        if packet.read_bits(1): # remove bit
            return

        if not packet.read_bits(1): # delta bit
            return
        
        fields = packet.read_uchar()
        assert(fields <= len(self))

        for i in range(fields):
            entry = self.__getitem__(i)
            
            changed = packet.read_bits(1) # changed
            if not changed:
                continue
            
            entry.load_value(packet)

    def __load_struct_config(self):
        self.append(entity_state_field(32))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(10))
        self.append(entity_state_field(0))
        self.append(entity_state_field(8))
        self.append(entity_state_field(8))
        self.append(entity_state_field(8))
        self.append(entity_state_field(8))
        self.append(entity_state_field(10))
        self.append(entity_state_field(8))
        self.append(entity_state_field(19))
        self.append(entity_state_field(10))
        self.append(entity_state_field(8))
        self.append(entity_state_field(8))
        self.append(entity_state_field(0))
        self.append(entity_state_field(32))
        self.append(entity_state_field(8))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(24))
        self.append(entity_state_field(16))
        self.append(entity_state_field(8))
        self.append(entity_state_field(10))
        self.append(entity_state_field(8))
        self.append(entity_state_field(8))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(8))
        self.append(entity_state_field(0))
        self.append(entity_state_field(32))
        self.append(entity_state_field(32))
        self.append(entity_state_field(32))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(32))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(0))
        self.append(entity_state_field(32))
        self.append(entity_state_field(16))

# connectResponse
# infoResponse
# statusResponse
# echo
# keyAuthorize
# motd
# print
# getserversResponse
# getserversExtResponse