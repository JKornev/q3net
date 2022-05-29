import time
import q3net

def client():
    connection = q3net.connection("localhost", 27960)
    assert( connection.send_command(q3net.get_status_request())  != None )
    assert( connection.send_command(q3net.get_info_request())    != None )

    connection.connect()

    while True:
        line = input(">")
        if line == "exit":
            break
        connection.send_command(q3net.custom_request(line))

    connection.disconnect()
    print("buy")
    time.sleep(5)
    connection.terminate()

if __name__ == '__main__':
    #client()
    ui = q3net.userinfo()
    ui['client']         = 'Q3 1.32b'
    ui['name']           = 'UnnamedPlayerA'
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

    c = q3net.connection("localhost", 27960, uinfo=ui)
    time.sleep(1)
    c.terminate()
    
    pass
    #print(ui.serialize())
    #ui.deserialize(ui.serialize())
    #print(ui)

