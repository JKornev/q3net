from re import A
import socket
import threading
import random
import q3huff
import enum
import copy
import defines
import clientstate
import protocol

# ========================
#   External aliases

userinfo = clientstate.userinfo

gamestate = clientstate.gamestate

events_handler = clientstate.events_handler

protocol_q3v68 = protocol.q3v68

protocol_q3v71 = protocol.q3v71

# ========================
#   UPD core

class _udp_packet:
    def __init__(self, response):
        self.data = response[0]
        self.host = response[1][0]
        self.port = response[1][1]

class _udp_transport:
    def __init__(self, host: str, port: int, timeout: float) -> None:
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._socket.connect((host, port))
        self._socket.settimeout(timeout)
        
    def send(self, data : bytes):
        self._socket.send(data)

    def recv(self, size) -> _udp_packet:
        return _udp_packet( self._socket.recvfrom(size) )

# ========================
#   Quake3 NET core

class connection:
    def __init__(self, host, port, protocol = protocol_q3v68,
                 handler = events_handler, uinfo: userinfo = None):
        # Network
        self._host = host
        self._port = port
        self._transport = _udp_transport(host, port, 0.1)
        # Protocol
        self._gs_evaluator = clientstate.evaluator(handler, uinfo)
        self._protocol = protocol(self._gs_evaluator)

    def __del__(self):
        pass

 