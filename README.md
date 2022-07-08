# q3net
Python library, emulator for Quake 3 connection

**Live demo**: [@qv3k_bot](https://t.me/qv3k_bot) - q3 client with telegram bot interface

### Requires
- Python 3.5+
- q3huff2 (this is a clone of q3huff library, source has a memory leak)

### Features
- Stable quake3 connection (vanilla, osp, e+, a bit of cpma)
- Connected and connection-less communication with a server, master-server and auth-server
- Protocols 68 and 71
- Supports sv_pure 1
- Supports proxy connection (qwfwd)
- Connection profile customization
- Other stuff

### Installation
You are able to download library from PyPi repo
```python
python -m pip install q3net
```
Now just include it to your project
```python
import q3net
```
Also you are able to copy q3net to your project manualy, just create a library dir `<your_project>/q3net` and copy q3net to it. Or you can use git submodules
```
cd <your project>\libs
mkdir q3net
git clone q3net
...
```

### How to
First lets try to query information from the server without a connection
```python
import q3net
# query server info and status
connection = q3net.connection("localhost", 27960)
print(connection.request(q3net.get_info_request()).data)
print(connection.request(q3net.get_status_request()).data)
connection.terminate()
```

Now let's open a simple connection
```python
import q3net
# open connection to localhost server
connection = q3net.connection("localhost", 27960)
if connection.connect():
    # welcome other players
    connection.send("say hi")
    connection.disconnect()
# gracefully destroy connection
connection.terminate()
```
Keep in mind when you create a `q3net.connection` object it internally creates a seporated worker thread. Therefore to avoid app freezes you need to terminate each `q3net.connection` object by calling method `q3net.connection.terminate()` in the end.

Other more detailed examples you can find in `\examples` folder
