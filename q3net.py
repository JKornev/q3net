import threading
import queue
import time
import traceback
import clientstate
import protocol
import utils

# ========================
#   External aliases

userinfo = clientstate.userinfo

gamestate = clientstate.gamestate

events_handler = clientstate.events_handler

protocol_q3v68 = protocol.q3v68

protocol_q3v71 = protocol.q3v71

# ========================
#   Quake3 NET core

class worker:
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

class responses_queue:

    def push(self):
        pass

    def apply_response(self, response):
        pass

class connection(worker):

    __DISCONNECT_TIMEOUT = 5.0
    __MAX_RELIABLE_COMMANDS = 64

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
        self._lock = threading.Lock()
        self._queue = queue.Queue(maxsize = self.__MAX_RELIABLE_COMMANDS)
        # Open worker thread
        super().__init__()

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        raise NotImplementedError

    def terminate(self):
        self._terminate()

    def request(self, request):
        raise NotImplementedError

    def send(self, command):
        raise NotImplementedError

    @property
    def gamestate(self):
        return self._gs_evaluator.gamestate

    def _worker_entrypoint(self):
        
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
                    
                    with self._lock:
                        self._transport.send( self._protocol.client_frame() )

                # go to a next frame
                continue
            
            # reset timeout counter because we got a packet from the server
            timeout_counter = 0

            with self._lock:
                try:
                    packet = self._protocol.handle_packet(raw.data)
                    if not packet: # defragmentation
                        continue
                except Exception:
                    print(traceback.print_exc())
                    continue

                #TODO: apply response

                # send client state in the end of the frame
                self._transport.send( self._protocol.client_frame() )

                # with self._lock:
                #     reader = q3huff.Reader(packet.data)
                #     response = self.__protocol.handle_packet(reader, len(packet.data))

                #     if self.__request_active:
                #         if self.__request.sequence == -1:
                #             if response.command == self.__request.response:
                #                 self.__request_response = response
                #                 self.__request_active = False
                #                 self.__request_event.set()
                #         else:
                #             if self.__gamestate.reliable_ack >= self.__request.sequence:
                #                 self.__request_response = response
                #                 self.__request_active = False
                #                 self.__request_event.set()

            

 