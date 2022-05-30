import clientstate
import packets
import utils
    
class _protocol_base:
    CONNECTION_LESS = -1
    FRAGMENTED = 1<<31
    MAX_RELIABLE_COMMANDS = 64

    def __init__(self, version, evaluator: clientstate.evaluator) -> None:
        self._protocol_version = version
        self._evaluator = evaluator
        self._gamestate = evaluator.gamestate
        self._connection_less = [
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

        # 1. Defragmentation
        if sequence != self.CONNECTION_LESS and (sequence & self.FRAGMENTED) != 0:
            # fragmented packet
            sequence &= (0xFFFFFFFF & ~(self.FRAGMENTED))
            packet, size = self._defragmentation(self._gamestate.challenge, sequence, packet)
            if not packet:
                return None
        
        # 2. Deserialization
        if sequence == self.CONNECTION_LESS:
            output = self._handle_connection_less_packet(packet)
        else:
            output = self._handle_connected_packet(sequence, packet, size)
        
        if not output:
             return packets.packet_unknown(data)

        # # 3. Evaluation (gamestate)
        self._evaluator(output)

        return output

    def _defragmentation(self, challenge, sequence, packet) -> bool:
        if self.defragmentator.load_fragment(challenge, sequence, packet):
            return self.defragmentator.get_packet()
        return None, None

    def _handle_connection_less_packet(self, packet):
        txt = packet.read_string()
        command = txt.split(maxsplit=1)[0]

        for entry in self._connection_less:
            if entry.equal(command):
                return entry.parse(txt)

        return None

    def _handle_connected_packet(self, sequence, packet, size):
        # assert(size > 4)
        
        # if self.gamestate.sequence + 1 > sequence  : #> self.gamestate.sequence + 100
        #     #print("[proto] packet dropped, seq:%d != gs.seq:%d" % (sequence, self.gamestate.sequence))
        #     return None
        
        # #raw = self.__decrypt_packet( sequence, packet.read_data(size - 4) )
        # raw = self.__decrypt_packet( sequence, packet.read_data(size) )

        # # Decode tail
        # tail = q3huff.Reader(raw)
        # tail.oob = False
        # self.gamestate.sequence = sequence
        # ack = tail.read_long()
        # if ack != self.gamestate.reliable_ack:
        #     pass
        # self.gamestate.reliable_ack = ack

        # q3packet = packet_q3_frame()
        # q3packet.parse(tail)
        # return q3packet
        return None

    def client_frame(self):
        raise NotImplementedError

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
        packet =  utils.reader(self.sequence.to_bytes(4, "little", signed=True) + self.packet)
        packet.oob = True
        packet.read_long()
        return packet, len(self.packet) 

class q3v68(_protocol_base):
    def __init__(self, evaluator: clientstate.evaluator) -> None:
        super().__init__(68, evaluator)

class q3v71(q3v68):
    def __init__(self, evaluator: clientstate.evaluator) -> None:
        super().__init__(71, evaluator)
