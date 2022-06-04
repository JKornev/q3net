import threading
import random
import traceback
import clientstate
import protocol
import packets
import utils
import defines
import q3huff

# ========================
#   External aliases

userinfo = clientstate.userinfo

gamestate = clientstate.gamestate

events_handler = clientstate.events_handler

protocol_q3v68 = protocol.q3v68

protocol_q3v71 = protocol.q3v71

server_packet = packets.server_packet

# ========================
#   Quake3 requests

class command_request:
    def __init__(self, command : bytes, response = None, require_connection = False) -> None:
        self.req_command = command
        self.resp_command = response
        self.require_connection = require_connection

class get_info_request(command_request):
    def __init__(self):
        super().__init__(b"getinfo", "infoResponse")
 
class get_status_request(command_request):
    def __init__(self):
        super().__init__(b"getstatus", "statusResponse")

class challenge68_request(command_request):
    def __init__(self):
        super().__init__(b"getchallenge", "challengeResponse")

class challenge71_request(command_request):
    def __init__(self):
        self.challenge = random.randint(-2147483648, 2147483647)
        super().__init__(b"getchallenge " + str(self.challenge), "challengeResponse")

class connection_request(command_request):
    def __init__(self, userinfo):
        super().__init__(b"connect " + q3huff.compress(userinfo.serialize().encode()), "connectResponse")

# ========================
#   Quake3 NET core

class _worker:
    def __init__(self) -> None:
        self.__active = True
        self.__lock = threading.Lock()
        self.__worker = threading.Thread(target=self._worker_entrypoint)
        self.__worker.start()

    def __del__(self):
        self.terminate()

    def _terminate(self):
        self.__active = False
        self.__worker.join()

    @property
    def active(self) -> bool:
        with self.__lock:
            return self.__active

    def _worker_entrypoint(self):
        raise NotImplementedError

class _requestor:
    def __init__(self) -> None:
        self._event = threading.Event()
        self._mutex = threading.Lock() # syncronization implemented by outside mutex
        self._busy = False
        self._request = None
        self._response = None
        
    def push(self, request: command_request, sequence):
        if request.require_connection:
            if not sequence or sequence < 0:
                raise Exception("Invalid sequence request", sequence)

        # Become busy and reset event
        with self._mutex:
            if self._busy:
                raise Exception("Request already in a progress")
            self._busy = True
            self._sequence = sequence
            self._request = request
            self._response = None
            self._event.clear()

    def try_complete(self, response: packets.server_packet, gamestate):
        with self._mutex:
            if not self._busy:
                return

            if not self._request.require_connection and utils.connection_sequence(response.sequence):
                return

            if self._request.require_connection:
                if not utils.connection_sequence(response.sequence):
                    return
                
            if self._request.resp_command != response.command:
                return
                
            self._request = None
            self._response = response
            self._event.set()

    def wait(self, timeout):
        # Now lets wait for response
        if not self._event.wait(timeout = timeout):
            return None

        # Unlock busy state and return results
        with self._mutex:
            self._busy = False
            return self._response

class connection(_worker):
    __DISCONNECT_TIMEOUT = 5.0
    __REQUEST_TIMEOUT = 5.0

    def __init__(self, host, port, protocol = protocol_q3v68,
                 handler = events_handler, uinfo: userinfo = None, fps: int = 60):
        assert(1 <= fps <= 125)
        # FPS
        self._fps = fps
        self._frame_timeout = 1.0 / self._fps
        # Network
        self._host = host
        self._port = port
        self._transport = utils.udp_transport(host, port, self._frame_timeout)
        # Protocol
        self._gs_evaluator = clientstate.evaluator(handler, uinfo)
        self._protocol = protocol(self._gs_evaluator)
        # Request
        self._request_lock = threading.Lock()
        self._requestor = _requestor()
        # Open worker thread
        super().__init__()

    def connect(self, attempts=10):
        if self.gamestate.is_connected():
            raise Exception("Already connected")
        
        try:
            # Get challenge
            self._gs_evaluator.change_state(
                frm = defines.connstate_t.CA_DISCONNECTED, 
                to = defines.connstate_t.CA_CONNECTING
            )
            
            request = challenge68_request() #TODO: challenge depends on protocol
            for i in range(attempts):
                response = self.request(request)
                if response:
                     break
            if not response:
                raise Exception("Can't get a challenge")
            challenge = response.data[0]

            # Open connection            
            #TODO: verify protocol version
            userinfo = self.gamestate.userinfo
            userinfo["challenge"] = response.data[0]
            userinfo["qport"] = self._port
            userinfo["protocol"] = self._protocol.protocol
            response = self.request(connection_request(userinfo))
            if not response:
                raise Exception("Can't receive connection response")

            if response.data != challenge:
                raise Exception(f"Wrong challenge {challenge} != {response.data}")

        except Exception as exc:
            self._gs_evaluator.change_state(defines.connstate_t.CA_DISCONNECTED)
            raise exc

    def disconnect(self):
        raise NotImplementedError

    def terminate(self):
        self._terminate()

    def request(self, request: command_request) -> server_packet:
        with self._request_lock:
            if request.require_connection:
                seqence = self._protocol.queue_command(request.req_command)
            else:
                self._transport.send( utils.int_to_bytes(defines.NO_CONNECTION_SEQUENCE) + request.req_command)
                seqence = None # no sequence is needed
                
            self._requestor.push(request, seqence)

        return self._requestor.wait(self.__REQUEST_TIMEOUT)

    def send(self, command: str, force_connless = False):
        with self._request_lock:
            if self.gamestate.is_connected() and not force_connless:
                # Push reliable command if we are connected
                seqence = self._protocol.queue_command(command)
            else:
                # Send directly if it's a connection-less command
                self._transport.send( utils.int_to_bytes(defines.NO_CONNECTION_SEQUENCE) + command.encode() )

    @property
    def gamestate(self):
        return self._gs_evaluator.gamestate

    def _worker_entrypoint(self):
        # we need to drop connection if server doesn't send us packets too long
        timeout_counter = 0
        timeout_max = int(self.__DISCONNECT_TIMEOUT / self._frame_timeout)

        while self.active:
            
            try:
                raw = self._transport.recv(0x4000)
            except TimeoutError:
                timeout_counter += 1
                if self.gamestate.is_connected():
                    if timeout_counter > timeout_max:
                        #TODO: force gamestate to disconnect
                        break
                    
                    with self._request_lock:
                        self._transport.send( self._protocol.client_frame() )
                # go to a next frame
                continue
            
            # reset timeout counter because we got a packet from the server
            timeout_counter = 0

            with self._request_lock:
                try:
                    packet = self._protocol.handle_packet(raw.data)
                    if not packet: # defragmentation
                        continue
                except Exception:
                    print(traceback.print_exc())
                    continue
                
                # try to complete request if it exists
                self._requestor.try_complete(packet, self.gamestate)

                # send client state in the end of the frame
                if self.gamestate.is_connected():
                    self._transport.send( self._protocol.client_frame() )
