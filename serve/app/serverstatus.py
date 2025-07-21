class ServerStatus:
    def __init__(self):
        self._status = "accept"

    @property
    def status(self):
        return self._status

    def pause(self):
        self._status = "reject"

    def resume(self):
        self._status = "accept"
