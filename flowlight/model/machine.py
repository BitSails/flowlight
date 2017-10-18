from contextlib import contextmanager
from flowlight.core.setting import Setting
from flowlight.model.node import Node
from flowlight.core.command import Command
from flowlight.core.connection import Connection
from flowlight.utils.remote import RemoteWorkerMixin


def _need_connection(func):
    def wrapper(machine, *args, **kwargs):
        if not machine.connection:
            raise Exception('Connection is not set')
        return func(machine, *args, **kwargs)

    return wrapper


class Machine(Node, RemoteWorkerMixin):
    """remote Machine.

    Usage::

        >>> m = Machine('127.0.0.1')
        >>> m.name = 'local'
        >>> m.enable_connection(password='root')
        >>> isinstance(m.run('echo 1;'), Response)
        True
    """
    def __init__(self, host, port=Setting.DEFAULT_SSH_PORT, name=None, connect=False, **kwargs):
        Node.__init__(self, name)
        self.host = host
        self.port = port
        self.connection = None
        if connect is True:
            self.enable_connection(connect=True, **kwargs)

    @_need_connection
    def run(self, cmd, **kwargs):
        command = Command(cmd, **kwargs)
        response = self.connection.exec_command(command)
        return response

    @_need_connection
    async def run_async(self, cmd, **kwargs):
        command = Command(cmd, **kwargs)
        response = await self.connection.exec_async_command(command)
        return response

    def enable_connection(self, **kwargs):
        if not self.connection:
            self.connection = Connection(machine=self, host=self.host, port=self.port, **kwargs)

    @_need_connection
    @contextmanager
    def jump_to(self, host, port=Setting.DEFAULT_SSH_PORT, username='root', password=None, **connect_args):
        connection = self.connection
        transport = connection.client.get_transport()
        remote_machine = Machine(host=host, port=port)
        channel = transport.open_channel("direct-tcpip", dest_addr=remote_machine.getaddr(), src_addr=self.getaddr())
        remote_machine.enable_connection(username=username, password=password, sock=channel, **connect_args)
        yield remote_machine
        remote_machine.connection.close()
        del remote_machine

    def put(self, *args, **kwargs):
        with self.connection.sftp as sftp:
            sftp.put(*args, **kwargs)

    def get(self, *args, **kwargs):
        with self.connection.sftp as sftp:
            sftp.get(*args, **kwargs)

    def getaddr(self):
        return self.host, self.port

    __str__ = lambda self: self.host

    def __repr__(self):
        return '<Machine host={}>'.format(self.host)