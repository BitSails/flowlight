from flowlight.tasks.meta import TaskMeta
from flowlight.tasks.task import _Task
from flowlight.tasks.future import TaskFuture
from flowlight.tasks.state import TaskState


def task(func=None, *args, **kwargs):
    """Decorator function on task procedure which will be executed on machine cluster.

    :param func: the function to be decorated, act like a task.
            if no function specified, this will return a temporary class,
            which will instantiate a `_Task` object when it was called.
            otherwise, this will return a standard `_Task` object with
            parameters passed in.

    Usage::

        >>> deferred = task()
        >>> isinstance(deferred, _Task)
        False
        >>> t = deferred(lambda: None)
        >>> isinstance(t, _Task)
        True
        >>> t2 = task(lambda: None)
        >>> isinstance(t2, _Task)
        True

    """
    cls = _Task
    if func is None:
        class _Deffered:
            def __new__(_cls, func):
                return cls(func, *args, **kwargs)
        return _Deffered
    return cls(func, *args, **kwargs)
