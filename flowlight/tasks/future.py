import threading

from flowlight.tasks.state import TaskState


class TaskFuture:
    def __init__(self, task):
        self._task = task
        self.state = TaskState.init()
        self.data = None
        self.event = threading.Event()
        self._callbacks = []

    def ready(self):
        self.state.start()

    def set_result(self, result):
        self.state.finish()
        self.data = result
        for callback in self._callbacks:
            callback(result)
        self.event.set()

    def add_done_callback(self, callback):
        self._callbacks.append(callback)

    def get(self, wait=False):
        if not self.event.is_set() and wait is True:
            self.event.wait()
        return self.data

    def get_task(self):
        return self._task

    def __repr__(self):
        return '<TaskFuture state={} task={}>'.format(self.state, self.get_task().func.__name__)
