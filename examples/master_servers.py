# ==================================
#  Example - master_servers.py
#  Simple example how to query a servers information from the master server

import q3net
import time
from queue import Empty, Queue

class handler(q3net.events_handler):
    def __init__(self, host, port, queue) -> None:
        self._host = host
        self._port = port
        self._queue = queue

    def event_command(self, gamestate, sequence, command):
        # This callback should be called multiple times because getServers response
        # comes as part of multiple packets
        for server in command:
            self._queue.put(server)

def servers_list(master_host, master_port):
    queue = Queue() # The queue to process a response from a master server
    master = None
    try:
        # Open semi-connection with a master server
        master = q3net.connection(
            master_host, master_port, 
            handler= handler(master_host, master_port, queue)
        )

        # Ask a master server for a servers list
        master.request(q3net.get_servers_request())

        # For each server we received lets query and display a bit information
        while True:
            query = None
            try:
                # Dequeue server 
                server, port = queue.get_nowait()
                print(f"{server}:{port}")

                # An attempt to get a server status
                query = q3net.connection(server, port)
                status = query.request(q3net.get_status_request(), timeout= 1.0)
                if not status:
                    continue

                # Print server status
                info, players = status.data
                for k, v in info.items():
                    print(f"  {k:<15} : {v.strip()}")

                # Print players
                for score, ping, name in players:
                    print(f"    {score} {ping} {name.strip()}")

            except Empty:
                break # No more, there is no more servers
            finally:
                if query:
                    query.terminate()
        
    except Exception as excp:
        print(f"Error: {excp}")

    # Terminate connection object
    if master:
        master.terminate()

if __name__ == '__main__':
    servers_list("master.quake3arena.com", 27950)
    #servers_list("master.ioquake3.org", 27950)
    #servers_list("master.maverickservers.com", 27950)