import socket
import q3huff
import defines

# ========================
#   Network

class udp_packet:
    def __init__(self, response):
        self.data = response[0]
        self.host = response[1][0]
        self.port = response[1][1]

class udp_transport:
    def __init__(self, host: str, port: int, timeout: float) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.connect((host, port))
        self._socket.settimeout(timeout)
        
    def send(self, data : bytes):
        self._socket.send(data)

    def recv(self, size) -> udp_packet:
        return udp_packet( self._socket.recvfrom(size) )

# ========================
#   Serialization

def int_to_bytes(value: int):
    return value.to_bytes(4, "little", signed=True)

class reader:
    def __init__(self, data) -> None:
        self._reader = q3huff.Reader(data)

    def compression(self, enable):
        self._reader.oob = not enable

    def read_int(self):
        return self._int(4, True)
    
    def read_uint(self):
        return self._int(4, False)

    def read_short(self):
        return self._int(2, True)
    
    def read_ushort(self):
        return self._int(2, False)

    def read_char(self):
        return self._int(1, True)
    
    def read_uchar(self):
        return self._int(1, False)

    def read_string(self):
        return self._reader.read_string()

    def read_bigstring(self):
        return self._reader.read_bigstring()
    
    def read_data(self, size):
        return self._reader.read_data(size)

    def read_bits(self, size):
        return self._reader.read_bits(size)

    def _int(self, size, signed):
        return int.from_bytes(self._reader.read_data(size), "little", signed=signed)
    
    def _read(self, size):
        #TODO: check reading out of buffer or delete it
        pass
 
# ========================
#   Misc

def connection_sequence(sequence : int) -> bool:
    return not (sequence == defines.NO_CONNECTION_SEQUENCE)
