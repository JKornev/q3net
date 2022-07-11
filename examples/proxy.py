# ==================================
#  Example - proxy.py
#  Connection over QWFWD proxy

import q3net
import time

# Lets use a handler just to have an output
class handler(q3net.events_handler):
    def event_connected(self, gamestate, host, port, srv_id):
        print(f"Connected to {host}:{port} id:{srv_id}")

    def event_disconnected(self, gamestate, reason):
        print(f"Disconnected, reason : {reason}")

    def event_command(self, gamestate, seq, cmd):
        print(f"Command {seq} : {cmd}")

def proxy_connection():
    connection = None
    try:
        server = "ffa.fpsclasico.de:27964"
        # You can take any random proxy from
        # https://www.quakeservers.net/quakeworld/servers/t=proxy/ 
        proxy_host, proxy_port = "dudoomers.com", 30000

        # Create a connection object and bind it with the proxy server
        connection = q3net.connection(proxy_host, proxy_port, handler= handler())

        # Connect to the server
        connection.connect(proxy= server)
        
        time.sleep(1.0) # Wait a sec to avoid losing next command
        connection.request(q3net.say_request("hi quake!"))

        # Destroy the connection
        connection.disconnect()
    except Exception as excp:
        print(f"Error: {excp}")

    # Terminate connection object
    if connection:
        connection.terminate()

if __name__ == '__main__':
    proxy_connection()
