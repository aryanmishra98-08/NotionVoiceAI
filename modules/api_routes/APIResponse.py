class APIResponse:
    def __init__(self, output=None, message=""):
        self.data = output
        self.message = message
