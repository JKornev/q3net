import socket

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
