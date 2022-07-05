import time
import q3net

ui = q3net.userinfo()
ui['client']         = 'Q3 1.32e'
ui['name']           = 'UnnamedPlayer'
ui['model']          = 'uriel/default'
ui['headmodel']      = 'uriel/default'
ui['team_model']     = 'uriel/default'
ui['team_headmodel'] = 'uriel/default'
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
ui['cg_predictItems'] = 1
ui['cl_guid']        = 'E7EBA5761D35155FFAC7BF13AA67DB41'
ui['cg_scorePlums']  = 0
ui['cg_smoothClients'] = 1
#ui['osp_client']     = 1008
#ui['osp_client'] = 20190331 #CPMA
#\xp_client\2300
#\xp_colors\5???5
#\xp_name\ExcessivePlayer
ui['teamoverlay']    = 1

#NOTE:
# CPMA server has authorization packets:
# RECV: psohtua 7115109
# SEND(9): htuatneilc 20343831371584843516760

class handler(q3net.events_handler):

    def event_connected(self, gamestate, host, port, srv_id):
        print(f"Connected to {host}:{port} id:{srv_id}")

    def event_disconnected(self, gamestate, reason):
        print(f"Disconnected, reason : {reason}")

    #def event_packet(self, gamestate, packet):
    #    print(f"Packet {packet.data}")

    def event_command(self, gamestate, seq, cmd):
        print(f"Command {seq} : {cmd}")

    def event_configstring(self, gamestate, inx, txt):
        print(f"ConfigString {inx} : {txt}")
        pass

def client():
    # connect issue with
    # 45.173.130.54:27960 baseq3 pure
    #
    #connection = q3net.connection("localhost", 27960, protocol= q3net.protocol_q3v71, handler=handler())
    #connection = q3net.connection("167.71.55.62", 27960, handler=handler()) #CPMA pure
    #connection = q3net.connection("89.221.217.148", 27980, handler=handler()) #e+
    #connection = q3net.connection("73.150.221.251", 27960, handler=handler()) #E+ pure
    connection = q3net.connection("sbct.ru", 27960, protocol= q3net.protocol_q3v71, handler=handler())
    connection.connect(userinfo= ui)

    while True:
        cmd = input(">")
        if cmd == "exit":
            break
        connection.send(cmd)

    connection.disconnect()
    print("bye")
    connection.terminate()

def main():
    print("master.quake3arena.com")
    connection = q3net.connection("master.quake3arena.com", 27950, handler=handler)
    assert( connection.request(q3net.getservers_request()) != None )
    time.sleep(2)
    connection.terminate()

    print("master.ioquake3.org")
    connection = q3net.connection("master.ioquake3.org", 27950, handler=handler)
    assert( connection.request(q3net.getservers_request()) != None )
    time.sleep(1)
    connection.terminate()

    print("master.maverickservers.com")
    connection = q3net.connection("master.maverickservers.com", 27950, handler=handler)
    assert( connection.request(q3net.getservers_request()) != None )
    time.sleep(1)
    connection.terminate()
            
if __name__ == '__main__':
    client()
    exit()

    

