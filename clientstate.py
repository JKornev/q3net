import threading
import defines
import utils

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
    
    def _execute_connection_less(self, packet):
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

            # Step 3: make connection completed on first gamestate frame
            if self._state == defines.connstate_t.CA_CONNECTED:
                self._state = defines.connstate_t.CA_ACTIVE

