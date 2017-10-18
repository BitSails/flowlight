class Response:
    """A wrapper of executed commands' result.

    :param target: the machine that runs the commands.
    :param stdin: standard input.
    :param stdout: standard output.
    :param stderr: standard error.

    Usage::

        >>> from io import BytesIO as bio
        >>> r = Response(Machine('127.0.0.1'), bio(b'stdout'), bio(b'stderr'))
        >>> print(r)
        stderr
        >>> r = Response(Machine('127.0.0.1'), bio(b'stdout'), bio(b''))
        >>> print(r)
        stdout

    """
    def __init__(self, target, stdout, stderr):
        self.target = target
        self.stdout = stdout.read() if stdout else stdout
        self.stderr = stderr.read() if stderr else stderr
        self.result = self.stderr if self.stderr else self.stdout

    def __str__(self):
        return self.result.decode()
