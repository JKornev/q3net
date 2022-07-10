# ==================================
#  Example - server_info.py
#  Print a server information using connection-less packets

import q3net
import sys

def server_info():
    if len(sys.argv) != 3:
        print("Usage: server_info.py <address> <port>")
        return

    connection = None
    try:
        host = sys.argv[1]
        port = int(sys.argv[2])

        print(f"Server: {host}:{port}")
        
        # Create a connection object
        connection = q3net.connection(host, port)

        # Print server information
        info = connection.request(q3net.get_info_request())
        if info:
            print("\nInformation:")
            for key, value in info.data.items():
                print(f" {key:<15}: {value.strip()}")
        
        # Print server status & players
        status = connection.request(q3net.get_status_request())
        if status:
            print("\nStatus:")
            vars, players = status.data
            for key, value in vars.items():
                print(f" {key:<15}: {value.strip()}")

            if len(players):
                for score, ping, name in players:
                    print(f" {score:>3} {ping:>3} {name.strip()}")
        
    except Exception as excp:
        print(f"Error: {excp}")

    # Terminate connection object
    if connection:
        connection.terminate()

if __name__ == '__main__':
    server_info()
