import clientstate

# ========================
#   Packets

class packet_base:
    sequence = -1

class packet_unknown(packet_base):
    def __init__(self, packet) -> None:
        pass

# ========================
#   Parsers

class parser_base:
    _command = None

    def __init__(self, command = None) -> None:
        _command = command

    def equal(self, command):
        return command == self._command

    def parse(self, packet):
        raise NotImplementedError

class parser_unknown(parser_base):

    def equal(self, command):
        return True # any packet is unknown in the end of the check

    def parse(self, packet):
        self._data = packet

class parser_print(parser_base):
    def __init__(self) -> None:
        super().__init__("print")

    def parse(self, packet):
        tokens = packet.split('\n', 1)
        assert(len(tokens) == 2)
        return tokens[1].rstrip() #TODO: return print packet

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

        return (info, players) #TODO: return packet

class parse_info(parser_base):
    def __init__(self) -> None:
        super().__init__("infoResponse")

    def parse(self, packet):
        lines = packet.splitlines()
        assert(len(lines) == 2)
        return clientstate.userinfo().deserialize(lines[1]) #TODO: return packet

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

        return (challenge, clientChallenge, protocol) #TODO: return packet

class parse_connect(parser_base):
    def __init__(self) -> None:
        super().__init__("connectResponse")

    def parse(self, packet):
        raise NotImplementedError
