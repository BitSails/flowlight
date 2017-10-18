from flowlight.utils.signal import Signal
from flowlight.utils.trigger import Trigger
from flowlight.tasks.meta import TaskMeta

import threading


class _Task:
    """ A task wrapper on funciton.

    :param func: task function called by `Node` lately.
    :param run_after: run the task when `run_after` is finish stage.
    :param run_only: only run the task when `run_only` condition is True.
    """
    def __init__(self, func, run_after=None, run_only=None):
        self.func = func
        self.trigger = Trigger()

        self.on_start = Signal.func_signal(self.start)
        self.on_complete = Signal.func_signal(self.complete)
        self.on_error = Signal.func_signal(self.error)

        self.event = threading.Event()
        self.run_only = run_only
        self.run_after = run_after

        if run_after is not None and isinstance(run_after, _Task):
            run_after.trigger.add(Signal.func_signal(lambda: self.event.set()))

    def __call__(self, node, *args, **kwargs):
        self.meta = TaskMeta(self, run_after=self.run_after)
        if self.run_only is False or (callable(self.run_only) and self.run_only() is False):
            return Exception('Run condition check is failed.'), False
        if self.meta.run_after is not None and isinstance(self.meta.run_after, _Task):
            self.event.wait()
            self.event.clear()
        try:
            self.on_start.send(self.meta)
            result = self.func(self.meta, node, *args, **kwargs)
            self.on_complete.send(self.meta)
            return result, True
        except Exception as e:
            self.on_error.send(e)
            return e, False
        finally:
            for signal in self.trigger:
                signal.send()
 
    def start(self, *args):
        pass

    def complete(self, *args):
        pass

    def error(self, exception):
        import traceback
        traceback.print_exc()

    def __repr__(self):
        return '<Task func={}>'.format(self.func.__name__)
