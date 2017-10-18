class Signal:
    def __init__(self, doc=None):
        self.doc = doc
        self._receivers = []

    def connect(self, func):
        self._receivers.append(func)

    def send(self, *args, **kwargs):
        for receiver in self._receivers:
            receiver(*args, **kwargs)

    def __call__(self, func):
        self.connect(func)

    @classmethod
    def func_signal(cls, func):
        signal = cls(None)
        signal.connect(func)
        return signal
