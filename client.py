import time
import q3net

class handler(q3net.events_handler):

    def event_connected(self, host, port, srv_id: int):
        print(f"Connected to {host}:{port} id:{srv_id}")

    def event_disconnected(self, reason: str):
        print(f"Disconnected to {reason}")

    def event_packet(self, packet):
        print(f"Packet {packet.data}")

    def event_command(self, seq: int, cmd: str):
        print(f"Command {seq} : {cmd}")

    def event_configstring(self, inx: int, txt: str):
        print(f"ConfigString {inx} : {txt}")

def client():
    connection = q3net.connection("localhost", 27960, handler=handler)
    assert( connection.request(q3net.get_status_request())  != None )
    assert( connection.request(q3net.get_info_request())    != None )

    connection.connect()

    while True:
        cmd = input(">")
        if cmd == "exit":
            break
        connection.send(cmd)

    connection.disconnect()
    print("buy")
    #time.sleep(5)
    connection.terminate()

if __name__ == '__main__':
    #client()
    
    ui = q3net.userinfo()
    ui['client']         = 'Q3 1.32b'
    ui['name']           = 'UnnamedPlayer'
    ui['model']          = 'sarge'
    ui['headmodel']      = 'sarge'
    ui['team_model']     = 'james'
    ui['team_headmodel'] = 'james'
    ui['handicap']       = 100
    ui['teamtask']       = 0
    ui['sex']            = 'male'
    ui['color1']         = 1
    ui['color2']         = 2
    ui['rate']           = 25000
    ui['snaps']          = 40
    ui['cl_maxpackets']  = 125
    ui['cl_timeNudge']   = 0
    ui['cl_anonymous']   = 0

    c = q3net.connection("q3.playground.ru", 27967, uinfo=ui, handler=handler)
    #time.sleep(1)
    c.send("getinfo")
    time.sleep(1)
    print( c.request(q3net.get_info_request()) )
    print( c.request(q3net.get_status_request()) )
    c.connect()
    time.sleep(5)
    for i in range(20):
        #time.sleep(1)
        #r = c.request(q3net.say_request(":)"))
        #print(f"say {r.data}")
        r = c.send("hi")
        print(f"say {r}")
        
    time.sleep(3.0)
    c.request(q3net.custom_request("players"))

    time.sleep(1.0)
    print("!!!! disconnecting")
    c.disconnect()
    print("!!!! terminating")
    c.terminate()
    print("!!!! done")
    #print(ui.serialize())
    #ui.deserialize(ui.serialize())
    #print(ui)
    

