import defines
import threading

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

    def __init__(self, uinfo: userinfo = None) -> None:
        self._state         = defines.connstate_t.CA_UNINITIALIZED
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
    def __init__(self, handler: events_handler, uinfo: userinfo) -> None:
        super().__init__(uinfo)
        self._handler = handler()

    @property
    def gamestate(self) -> gamestate:
        return self

    def execute(self, packet):
        pass
    
