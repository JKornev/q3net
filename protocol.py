import clientstate

class protocol_base:
    def __init__(self, evaluator: clientstate.evaluator) -> None:
        pass

    def handle_packet(self):
        raise NotImplementedError

    def client_frame(self):
        raise NotImplementedError

class q3v68(protocol_base):
    def __init__(self, evaluator: clientstate.evaluator) -> None:
        super().__init__(evaluator)

class q3v71(q3v68):
    def __init__(self, evaluator: clientstate.evaluator) -> None:
        super().__init__(evaluator)
