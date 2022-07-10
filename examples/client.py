# ==================================
#  Example - client.py 
#  Command line client

import q3net
import sys

class handler(q3net.events_handler):
    def event_connected(self, gamestate, host, port, srv_id):
        print(f"Connected to {host}:{port} id:{srv_id}")

    def event_disconnected(self, gamestate, reason):
        print(f"Disconnected, reason : {reason}")

    def event_command(self, gamestate, seq, cmd):
        print(f"Command {seq} : {cmd}")

    def event_configstring(self, gamestate, inx, txt):
        print(f"ConfigString {inx} : {txt}")

def client():
    if len(sys.argv) != 3:
        print("Usage: client.py <address> <port>")
        return

    connection = None
    try:
        host = sys.argv[1]
        port = int(sys.argv[2])
        # Open a connection
        connection = q3net.connection(host, port, handler= handler())
        connection.connect()
        
        while True:
            cmd = input(">")
            if cmd == "exit":
                break

            # Send a whole input to a server
            # commands might be:
            #  say hi
            #  players
            #  from
            #  ...
            connection.send(cmd)

        # Destroy a connection with a server
        connection.disconnect()
    except Exception as excp:
        print(f"Error: {excp}")

    # Terminate connection object
    if connection:
        connection.terminate()

if __name__ == '__main__':
    client()
