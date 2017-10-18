class Trigger:
    def __init__(self):
        self.signals = []

    def add(self, signal):
        self.signals.append(signal)

    def __iter__(self):
        return iter(self.signals)
