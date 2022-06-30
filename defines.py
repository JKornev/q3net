import enum

NO_CONNECTION_SEQUENCE = -1

FRAGMENTED_PACKET = 1<<31

MAX_RELIABLE_COMMANDS = 64

class configstr_t(enum.Enum):
    CS_SERVERINFO       = 0	# an info string with all the serverinfo cvars
    CS_SYSTEMINFO       = 1 # an info string for server system to client system configuration (timescale, etc)
    CS_VOTE_TIME        = 8
    CS_VOTE_STRING      = 9
    CS_PLAYERS          = 544

class connstate_t(enum.Enum):
    #CA_UNINITIALIZED    = 0
    CA_DISCONNECTED     = 1 # not talking to a server
   #CA_AUTHORIZING      = 2 # not used any more, was checking cd key 
    CA_CONNECTING       = 3 # sending request packets to the server
    CA_CHALLENGING      = 4 # sending challenge packets to the server
    CA_CONNECTED        = 5 # netchan_t established, getting gamestate
   #CA_LOADING          = 6 # only during cgame initialization, never during main loop
    CA_PRIMED           = 7 # got gamestate, waiting for first frame
    CA_ACTIVE           = 8 # game views should be displayed
   #CA_CINEMATIC        = 9 # playing a cinematic or a static pic, not connected to a server

class svc_ops_e(enum.Enum):
	svc_bad             = 0
	svc_nop             = 1
	svc_gamestate       = 2
	svc_configstring    = 3	# [short] [string] only in gamestate messages
	svc_baseline        = 4	# only in gamestate messages
	svc_serverCommand   = 5	# [string] to be executed by client game module
	svc_download        = 6	# [short] size [size bytes]
	svc_snapshot        = 7
	svc_EOF             = 8
	# new commands, supported only by ioquake3 protocol but not legacy
	svc_voipSpeex       = 9  # not wrapped in USE_VOIP, so this value is reserved.
	svc_voipOpus        = 10      

class clc_ops_e(enum.Enum):
	clc_bad             = 0
	clc_nop             = 1
	clc_move            = 2 # [[usercmd_t]
	clc_moveNoDelta     = 3 # [[usercmd_t]
	clc_clientCommand   = 4 # [string] message
	clc_EOF             = 5
	# new commands, supported only by ioquake3 protocol but not legacy
	clc_voipSpeex       = 6 #not wrapped in USE_VOIP, so this value is reserved.
	clc_voipOpus        = 7

