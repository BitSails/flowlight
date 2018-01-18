class TaskState:
    PENDING = 'PENDING'
    STARTED = 'STARTED'
    FINISHED = 'FINISHED'

    def __init__(self, state):
        self._state = None
        self.state = state

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        if state not in (self.PENDING, self.STARTED, self.FINISHED):
            raise Exception('Illegal state')
        self._state = state

    @classmethod
    def init(cls):
        return cls(cls.PENDING)

    def start(self):
        self.state = self.STARTED

    def finish(self):
        self.state = self.FINISHED

    def __str__(self):
        return self.state

    def __repr__(self):
        return '<TaskState state={}>'.format(self.state)
