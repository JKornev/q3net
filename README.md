# q3net
Python library, emulator for Quake 3 connection

**Live demo**: [@qv3k_bot](https://t.me/qv3k_bot) - q3 client with telegram bot interface

## Requirements
- Python 3.5+
- [q3huff2](https://pypi.org/project/q3huff2/) (clone of [q3huff](https://pypi.org/project/q3huff/) library with a [memory leak fix](https://github.com/JKornev/python-q3huff/commit/7d88c6ea90667273b32c0bfb4954f8d8826e693f))

## Features
- Stable quake3 connection (vanilla, osp, e+, a bit of cpma)
- Connected and connection-less communication with a server, master-server and auth-server
- Protocols 68 and 71
- Supports sv_pure 1
- Supports proxy connection ([qwfwd](https://github.com/QW-Group/qwfwd))
- Player customization
- Other stuff

## Installation
Q3net library is available in the PyPi repository
```python
python -m pip install q3net
```
Then just include it into your project
```python
import q3net
```
You can also copy q3net manualy to a project or add it as a git submodule
```
cd <your project>
git submodule add https://github.com/JKornev/q3net.git q3net
git add .
git commit -m "q3net included to a project"
python -m pip install q3huff2
```

## How to
Query information from the server without opening a full connection
```python
import q3net
# query server info and status
connection = q3net.connection("localhost", 27960)
print(connection.request(q3net.get_info_request()).data)
print(connection.request(q3net.get_status_request()).data)
connection.terminate()
```

Open a connection with a server
```python
import q3net
# open connection to localhost server
connection = q3net.connection("localhost", 27960)
connection.connect()
# welcome other players
connection.send("say hi")
connection.disconnect()
# gracefully destroy connection
connection.terminate()
```
Keep in mind when you create a `q3net.connection` object it internally creates a separated worker thread. Therefore to avoid app freezes you need to terminate each `q3net.connection` object by calling method `q3net.connection.terminate()` in the end.

Another example shows handling connection events
```python
import q3net, time

class handler(q3net.events_handler):
    def event_connected(self, gamestate, host, port, server_id):
        print(f"Connected to {host}:{port} id:{srv_id}")

    def event_disconnected(self, gamestate, reason):
        print(f"Disconnected, reason : {reason}")

    def event_packet(self, gamestate, packet):
        pass # frequent event, no need spam

    def event_command(self, gamestate, sequence, command):
        print(f"Command {sequence} : {command}")

    def event_configstring(self, gamestate, index, value):
        print(f"ConfigString {index} : {value}")

connection = q3net.connection("localhost", 27960, handler=handler())
connection.connect()
time.sleep(5.0) # give it work a bit
connection.disconnect()
connection.terminate()
```
`q3net.events_handler` class handles connection events from different thread (connection worker) therefore you have to worry about syncronization if you want to communicate with a main thread that opened a connection.

Other more detailed examples in [\examples](https://github.com/JKornev/q3net/tree/main/examples) folder:
- [client.py](https://github.com/JKornev/q3net/blob/main/examples/client.py) - simple command-line quake3 client
- [master_server.py](https://github.com/JKornev/q3net/blob/main/examples/master_server.py) - query information from quake3 master-server
- [proxy.py](https://github.com/JKornev/q3net/blob/main/examples/proxy.py) - an example of using QWFWD proxy
- [server_info.py](https://github.com/JKornev/q3net/blob/main/examples/server_info.py) - get server info using connection-less requests
