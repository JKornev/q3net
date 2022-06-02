import clientstate

# ========================
#   Common packet

class server_packet:
    def __init__(self, data, command = None, sequence = -1) -> None:
        self.sequence = sequence
        self.command = command
        self.data = data

# ========================
#   Parsers

class parser_base:
    _command = None

    def __init__(self, command = None) -> None:
        self._command = command

    def equal(self, command):
        return command == self._command

    def parse(self, packet):
        raise NotImplementedError

class parser_unknown(parser_base):
    def equal(self, command):
        return True # any packet is unknown in the end of the check

    def parse(self, packet):
        return server_packet(packet, self._command) 

class parser_print(parser_base):
    def __init__(self) -> None:
        super().__init__("print")

    def parse(self, packet):
        tokens = packet.split('\n', 1)
        assert(len(tokens) == 2)
        return server_packet( tokens[1].rstrip(), self._command )  #TODO: return print packet

class parse_status(parser_base):
    def __init__(self) -> None:
        super().__init__("statusResponse")

    def parse(self, packet):
        lines = packet.splitlines()
        assert(len(lines) >= 2)

        info = clientstate.userinfo()
        info.deserialize(lines[1])

        players = []
        for i in range(2, len(lines)):
            fields = lines[i].split(maxsplit=2)
            assert(len(fields) == 3)
            players.append((int(fields[0]), int(fields[1]), fields[2].strip("\"")))

        return server_packet( (info, players), self._command)

class parse_info(parser_base):
    def __init__(self) -> None:
        super().__init__("infoResponse")

    def parse(self, packet):
        lines = packet.splitlines()
        assert(len(lines) == 2)
        ui = clientstate.userinfo()
        ui.deserialize(lines[1])
        return server_packet(ui, self._command) 

class parse_challenge(parser_base):
    def __init__(self) -> None:
        super().__init__("challengeResponse")

    def parse(self, packet):
        tokens = packet.split()

        count = len(tokens)
        assert(2 <= count <= 4)

        challenge = int(tokens[1])

        clientChallenge = 0
        if count >= 3:
            clientChallenge = int(tokens[2])

        protocol = 68
        if count >= 4:
            protocol = int(tokens[3])

        return server_packet( (challenge, clientChallenge, protocol), self._command )

class parse_connect(parser_base):
    def __init__(self) -> None:
        super().__init__("connectResponse")

    def parse(self, packet):
        tokens = packet.split()
        count = len(tokens)
        assert(count == 2)
        return server_packet(int(tokens[1]), self._command)
