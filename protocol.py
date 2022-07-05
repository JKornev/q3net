import clientstate
import packets
import utils
import defines

class _protocol_base:
    def __init__(self, version, evaluator: clientstate.evaluator) -> None:
        self._protocol_version = version
        self._evaluator = evaluator
        self._gamestate = evaluator.gamestate
        self._connection_less = [
            packets.parser_getservers(),
            packets.parser_print(),
            packets.parse_status(),
            packets.parse_info(),
            packets.parse_challenge(),
            packets.parse_connect(),
            packets.parser_unknown()
        ]
        self._defragmentator = _defragmentator()

    @property
    def protocol(self):
        return self._protocol_version

    def handle_packet(self, data):
        size = len(data)
        packet = utils.reader(data)
        packet.compression(False)
        sequence = packet.read_int()

        if utils.connection_sequence(sequence):
            if self._protocol_version == 71:
                checksum = utils.make_checksum(sequence& ~defines.FRAGMENTED_PACKET, self._gamestate.challenge) 
                if checksum != 0xFFFFFFFF & packet.read_int():
                    return None
                size = size - 4
                #TODO: validate checksum make_checksum
                #TODO: normalize size

            # 1. Defragmentation
            if (sequence & defines.FRAGMENTED_PACKET) != 0:
                # fragmented packet
                sequence &= (0xFFFFFFFF & ~(defines.FRAGMENTED_PACKET))
                packet, size = self._defragmentation(self._gamestate.challenge, sequence, packet)
                if not packet:
                    return None

            # 2. Deserialization
            output = self._handle_connected_packet(sequence, packet, size - 4)
        else:
            output = self._handle_connection_less_packet(packet)
        
        if not output:
             return packets.server_packet(data)

        # 3. Evaluation (gamestate)
        self._evaluator.execute(output)

        return output

    def queue_command(self, command: str) -> int:
        return self._evaluator.queue_command(command)

    def _defragmentation(self, challenge, sequence, packet) -> bool:
        if self._defragmentator.load_fragment(challenge, sequence, packet):
            return self._defragmentator.get_packet()
        return None, None

    def _handle_connection_less_packet(self, packet):
        txt = packet.read_string()
        command = txt.split(maxsplit=1)[0]

        for entry in self._connection_less:
            if entry.equal(command):
                return entry.parse(txt)

        return None

    def _handle_connected_packet(self, sequence, packet, size):
        if size < 4:
            return None

        if not self._gamestate.is_connected():
            return None
        
        if self._gamestate.message_seq + 1 > sequence:
             return None
        
        compat = self._protocol_version == 68
        raw = self._evaluator.decrypt_server_frame( sequence, packet, size, compat )
        if not raw:
            return None

        parser = packets.parse_server_frame()
        output = parser.parse(sequence, raw)
        return output

    def client_frame(self):
        #TODO: protocol 71
        return self._evaluator.generate_client_frame(self._protocol_version == 68)

class _defragmentator:
    _FRAGMENT_SIZE = 1300

    def __init__(self) -> None:
        self.sequence = 0
        self.packet = bytes()

    def load_fragment(self, challenge, sequence, packet) -> bool:
        if self.sequence > sequence:
            return False

        if self.sequence < sequence:
            self.sequence = sequence
            self.packet_size = 0
            self.packet = bytes()

        fragment_start = packet.read_short()
        fragment_length = packet.read_short()

        if len(self.packet) != fragment_start:
            return False

        self.packet += packet.read_data(fragment_length)
        return (fragment_length <  self._FRAGMENT_SIZE)

    def get_packet(self):
        data = utils.int_to_bytes(self.sequence) + self.packet
        packet =  utils.reader(data)
        packet.compression(False)
        packet.read_uint()
        return packet, len(data)

class q3v68(_protocol_base):
    def __init__(self, evaluator: clientstate.evaluator) -> None:
        super().__init__(68, evaluator)

class q3v71(_protocol_base):
    def __init__(self, evaluator: clientstate.evaluator) -> None:
        super().__init__(71, evaluator)
