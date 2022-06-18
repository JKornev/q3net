import threading
import random
import traceback
import time
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
    def __init__(self, command, response = None, require_connection = False) -> None:
        self.req_command = command
        self.resp_command = response
        self.require_connection = require_connection

class getservers_request(command_request):
    def __init__(self, protocol = 68):
        super().__init__(b"getservers " + str(protocol).encode(), "getserversResponse")

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
        super().__init__(b"getchallenge " + str(self.challenge).encode(), "challengeResponse")

class connection_request(command_request):
    def __init__(self, userinfo):
        super().__init__(b"connect " + q3huff.compress(userinfo.serialize().encode()), "connectResponse")

class proxy_request(command_request):
    def __init__(self, userinfo):
        super().__init__(b"connect " + q3huff.compress(userinfo.serialize().encode()), "print") # print\n/reconnect ASAP!\n

class disconnect_request(command_request):
    def __init__(self):
        super().__init__("disconnect", None, require_connection=True)

class say_request(command_request):
    def __init__(self, message):
        #TODO: filter
        super().__init__(f"say \"{message}\"", None, require_connection=True)

class sayteam_request(command_request):
    def __init__(self, message):
        #TODO: filter
        super().__init__(f"say_team \"{message}\"", None, require_connection=True)

class custom_request(command_request):
    def __init__(self, message):
        #TODO: filter
        super().__init__(message, None, require_connection=True)

# ========================
#   Quake3 NET core

class _worker:
    def __init__(self) -> None:
        self.__active = True
        self.__lock = threading.Lock()
        self.__worker = threading.Thread(target=self._worker_entrypoint)
        self.__worker.start()

    def _terminate(self):
        with self.__lock:
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
                if self._sequence > gamestate.reliable_ack:
                    return
                    
            if self._request.resp_command != response.command:
                return
                
            self._request = None
            self._response = response
            self._busy = False
            self._event.set()

    def wait(self, timeout):
        # Now lets wait for response
        if not self._event.wait(timeout = timeout):
            with self._mutex:
                self._busy = False
            return None

        return self._response

class connection(_worker):
    __DISCONNECT_TIMEOUT = 5.0
    __REQUEST_TIMEOUT = 3.0

    def __init__(self, host, port, protocol = protocol_q3v68,
                 handler = events_handler, fps: int = 60):
        assert(1 <= fps <= 125)
        # FPS
        self._fps = fps
        self._frame_timeout = 1.0 / self._fps
        # Network
        self._host = host
        self._port = port
        self._transport = utils.udp_transport(host, self._port, self._frame_timeout)
        # Protocol
        self._gs_evaluator = clientstate.evaluator(handler, self._host, self._port)
        self._protocol = protocol(self._gs_evaluator)
        # Request
        self._request_lock = threading.Lock()
        self._requestor = _requestor()
        # Open worker thread
        super().__init__()

    def connect(self, userinfo: clientstate.userinfo = None, attempts = 10, proxy = None):
        if self.gamestate.is_connected():
            raise Exception("Already connected")
        
        try:
            # Get challenge
            self._gs_evaluator.change_state(
                frm = defines.connstate_t.CA_DISCONNECTED, 
                to = defines.connstate_t.CA_CONNECTING
            )

            #TODO: instead of such check a _protocol might generate request by its own
            if self._protocol.protocol == 71:
                request = challenge71_request()
            else:
                request = challenge68_request()

            for i in range(attempts):
                response = self.request(request, timeout = 1.0)
                if response:
                     break
            if not response:
                raise Exception("Can't get a challenge")
            challenge = response.data[0]

            # Open connection
            if userinfo:
                self._gs_evaluator.set_player_profile(userinfo)

            #TODO: verify protocol version
            userinfo = self.gamestate.userinfo
            userinfo["challenge"] = response.data[0]
            userinfo["protocol"] = self._protocol.protocol
            if not "qport" in userinfo.keys():
                userinfo["qport"] = self.gamestate.qport

            if proxy:
                # On proxy connection 
                userinfo["prx"] = proxy
                for i in range(attempts):
                    response = self.request(proxy_request(userinfo))
                    if response:
                        break
                if not response:
                    raise Exception("Can't receive connection response")

                self._gs_evaluator.change_state( to = defines.connstate_t.CA_DISCONNECTED )
                self.connect(userinfo= userinfo, attempts= attempts, proxy= None)
            else:
                # Normal connection
                response = self.request(connection_request(userinfo))
                if not response:
                    raise Exception("Can't receive connection response")

                if response.data and response.data != challenge:
                    raise Exception(f"Wrong challenge {challenge} != {response.data}")

        except Exception as exc:
            self._gs_evaluator.disconnect()
            raise exc

    def disconnect(self):
        if not self.request(disconnect_request()):
            self._gs_evaluator.disconnect()

    def terminate(self):
        super()._terminate()

    def request(self, request: command_request, timeout = __REQUEST_TIMEOUT) -> server_packet:
        with self._request_lock:
            if request.require_connection:
                seqence = self._protocol.queue_command(request.req_command)
            else:
                self._transport.send( utils.int_to_bytes(defines.NO_CONNECTION_SEQUENCE) + request.req_command)
                seqence = None # no sequence is needed
                
            self._requestor.push(request, seqence)

        return self._requestor.wait(timeout)

    def send(self, command: str, force_connless = False):
        with self._request_lock:
            if self.gamestate.is_connected() and not force_connless:
                # Push reliable command if we are connected
                seqence = self._protocol.queue_command(command)
            else:
                # Send directly if it's a connection-less command
                self._transport.send( utils.int_to_bytes(defines.NO_CONNECTION_SEQUENCE) + command.encode() )
                seqence = None
            return seqence

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
                        #TODO: notify somehow main thread
                        self._gs_evaluator.disconnect()
                        continue
                    
                    with self._request_lock:
                        self._transport.send( self._protocol.client_frame() )
                # go to a next frame
                continue
            except ConnectionError:
                self._gs_evaluator.disconnect()
                time.sleep(0.1)
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
                    
