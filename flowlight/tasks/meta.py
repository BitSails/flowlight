class TaskMeta(dict):
    """A dict-like storage data structure to collect task's information.

    :param task: the task that owns this meta object.

    Usage::

        >>> t = _Task(lambda: None)
        >>> isinstance(t.meta, TaskMeta)
        True
        >>> isinstance(t.meta, dict)
        True
        >>> 'task' in t.meta
        True
        >>> t.meta['a'] = 1
        >>> print(t.meta['a'])
        1
        >>> t.meta.b = 2
        >>> print(t.meta['b'])
        2

    """
    def __init__(self, task, **kwargs):
        self.task = task
        self.update(**kwargs)

    def __getattr__(self, name):
        return self.get(name, None)

    def __setattr__(self, name, value):
        self[name] = value
