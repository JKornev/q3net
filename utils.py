import socket
import hashlib
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

def uint_to_bytes(value: int):
    return value.to_bytes(4, "little", signed=False)

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

# ========================
#   Pure

pk3_checksum_table = {
    "baseq3" : {
        "cgame": (
            5,
            b"\xf0\x5b\x71\x29\x6d\x2e\x0f\x10\xa3\xd0\x5d\x9e\x72\xba\xf7\x1c"\
            b"\x59\x3c\x49\x41",
            "pak8.pk3"
        ),
        "ui":(
            5,
            b"\xf0\x5b\x71\x29\x6d\x2e\x0f\x10\xa3\xd0\x5d\x9e\x72\xba\xf7\x1c"\
            b"\x59\x3c\x49\x41",
            "pak8.pk3"
        )
    },
    "osp" : {
        "cgame": (
            1,
            b"\x4c\x5b\x2a\x31",
            "zz-osp-pak3.pk3"
        ),
        "ui":(
            95,
            b"\xcd\x4d\x56\x12\xc0\x79\x25\x72\x7d\xe9\x5f\x30\x54\xdc\x6e\x76"\
            b"\x67\x7f\x88\x9e\x46\x3b\xc6\xe2\xd3\xe2\x9a\x87\x42\x23\xb5\xdb"\
            b"\x24\xca\xda\x6b\x98\x37\xdb\xf8\x75\x76\x9f\xff\x41\xa4\x76\x3b"\
            b"\xe1\x51\xf9\x21\x43\x61\x94\x23\xd7\x51\x1e\x72\x0f\x56\xee\x00"\
            b"\x4d\x66\x47\xf2\x23\x4a\x62\xe4\x5a\xc4\x57\x08\x54\xef\x6d\xd0"\
            b"\x65\x94\xe3\xf5\x18\xa3\xda\xbd\x44\x71\xce\x94\xdc\xc2\x4f\xad"\
            b"\x66\x75\x53\xb2\x2d\xde\x7d\xbe\x55\xba\x57\x73\x40\x13\xd3\xd7"\
            b"\x5c\x9c\x49\x89\xde\xa1\xea\x87\x52\x4d\x3b\x11\x6a\xa6\x22\x05"\
            b"\x3d\xd6\x9f\x85\x18\xeb\x68\x3a\x8d\x56\xc7\xf4\x74\x45\x59\xda"\
            b"\x59\xdf\x25\x71\x75\x36\x6e\xfa\xe8\xc2\xb6\xcb\xd7\x77\x04\xe4"\
            b"\x9e\x37\xa1\xbe\x0c\x12\x8d\x24\xf6\x5a\xca\x54\xf1\x00\x5c\xc2"\
            b"\x61\x2e\x7a\x22\x2e\xf3\x8f\x81\xac\x2b\x71\xa4\x87\xf8\x36\xe6"\
            b"\x59\x2f\xbc\xcb\x9b\x67\x97\x19\x4b\x86\x4b\xc1\xc4\x0e\xba\x8a"\
            b"\x63\xe2\x30\x78\x97\xdc\x6f\x16\xff\xf1\x0b\xe0\xab\x00\x8d\x3b"\
            b"\x68\x0c\x5a\x2b\x65\xc1\xa3\x5d\x70\x11\x94\xc6\x59\x0b\x78\x48"\
            b"\xa1\x0b\xa7\x9d\xc4\x56\x87\xbb\xe1\xf7\x96\xf0\xa7\xbd\xa8\xde"\
            b"\x6e\x41\x2f\xd6\x3f\x41\x34\xfe\x8a\xb7\x18\xc6\x3b\x98\x8b\xf8"\
            b"\x26\x1e\x10\x69\xf7\x5c\xcc\x87\xed\x4a\xf4\x65\xc3\xb4\xf0\xf3"\
            b"\x2e\x87\x47\x83\x2c\x9d\x18\x5f\xed\x13\x5a\x20\x6d\xe7\xe6\xb2"\
            b"\x61\xa7\x86\x70\x22\xc6\xe3\xee\x89\x40\x86\x76\x7c\x78\x02\x5f"\
            b"\x8e\x78\x98\x9d\x0f\x69\x8f\xc8\x33\x9f\xcd\xd1\xf1\x1a\xe9\x5e"\
            b"\xd4\x87\x89\x3b\xfd\xd3\x54\xad\x67\x9c\x3f\x42\x5c\xd3\x15\x21"\
            b"\x1d\xf3\x84\xca\xb7\x94\x74\xfe\x29\x6e\xf0\xe1\x57\x93\x36\x6b"\
            b"\xb3\x53\x2c\x3b\xbd\xc7\x2d\x5a\x9e\x50\xbd\x60",
            "zz-osp-pak3.pk1"
        )
    },
}

def calculate_checksum(mode, vm, feed):
    try:
        table = pk3_checksum_table[mode][vm]
    except:
        table = pk3_checksum_table["baseq3"][vm]
    
    data = int_to_bytes(feed) + table[1]
    hash = bytes.fromhex( hashlib.new('md4', data).hexdigest() )
    
    return int.from_bytes(hash[0:4], "little", signed=True) \
         ^ int.from_bytes(hash[4:8], "little", signed=True) \
         ^ int.from_bytes(hash[8:12], "little", signed=True) \
         ^ int.from_bytes(hash[12:16], "little", signed=True)
