# q3net
Python library that emulates a Quake 3 connection

#### Live demo
[@qv3k_bot](https://t.me/qv3k_bot) q3 client with telegram bot interface

## Features
- Stable quake3 connection (vanilla, osp, e+, a bit of cpma)
- Connected and connection-less communication with a server
- Protocols 68 and 71
- Supports sv_pure 1
- Supports proxy connection (qwfwd)
- Connection profile customization

etc

## Installation
You are ably to download library from PyPi repo
```python
python -m pip install q3net
```
Then just include it to your project
```python
import q3net

# open connection to localhost server
connection = q3net.connection("localhost", 27960)
if connection.connect():
    connection.send("say hi")
    connection.disconnect()

# gracefully destroy connection
connection.terminate()
```
Also you are able to copy a project and include a library manually and even include it using git submodules
