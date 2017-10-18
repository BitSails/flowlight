import getpass
import os
import socket
import subprocess
import paramiko
import asyncio
from io import BytesIO

from flowlight.core.setting import Setting
from flowlight.core.command import Command
from flowlight.core.response import Response


class Connection:
    """A SSH Channel connection to remote machines.

    :param machine: the `Machine` owns this connection.
    :param host: the remote host string.
    :param port: the remote port.
    :param username: loggin user's name.
    :param password: loggin user's password.
    :param pkey: private key to use for authentication.
    :param timeout: timeout seconds for the connection.
    :param auto_add_host_policy: auto add host key when no keys were found.
    :param lazy: whether to build the connection when initializing.
    :param sock: an open socket or socket-like objectto use for communication to the target host
    """

    def __init__(self, machine, host='127.0.0.1', port=None, username='root',
                 password=None, pkey='~/.ssh/id_rsa', timeout=5, auto_add_host_policy=True, connect=False,
                 sock=None, **kwargs):
        self._machine = machine
        self.client = paramiko.SSHClient()
        self.client.load_system_host_keys()
        self.hostname = host
        self.host = socket.gethostbyname(host)
        self.port = port or Setting.DEFAULT_SSH_PORT
        self.username = username
        self.password = password
        self.timeout = timeout
        self.is_local = False
        self.sock = sock
        pkey = os.path.abspath(os.path.expanduser(pkey))
        if os.path.exists(pkey):
            self.pkey = paramiko.RSAKey.from_private_key_file(pkey)
        else:
            self.pkey = None
        self._connect_args = kwargs
        self.is_connected = False
        if auto_add_host_policy:
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if connect:
            self.build_connect()

    def build_connect(self):
        if self.host == '127.0.0.1' and self.sock is None:
            self._exec_command = self.exec_local_command
            self.is_local = True
        else:
            use_pass = self.password is not None
            try:
                self.client.connect(self.host, self.port, self.username, self.password,
                                    pkey=self.pkey, timeout=self.timeout, sock=self.sock, **self._connect_args)
            except paramiko.ssh_exception.AuthenticationException as e:
                if not use_pass:
                    passwd = getpass.getpass("{}@{}'s password: ".format(self.username, self.host))
                    self.password = passwd
                    return self.build_connect()
                else:
                    raise e
        self.is_connected = True

    def close(self):
        self.client.close()
        self.is_connected = False
        self._machine.connection = None

    def exec_local_command(self, command: Command):
        p = subprocess.Popen(command.cmd, shell=True,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT,
                             bufsize=command.bufsize,
                             env=command.env
                             )
        response = Response(self._machine, p.stdout, p.stderr)
        return response

    def exec_remote_command(self, command: Command):
        stdin, stdout, stderr = self.client.exec_command(
            command.cmd,
            bufsize=command.bufsize,
            timeout=command.timeout,
            environment=command.env
        )
        response = Response(self._machine, stdout, stderr)
        return response

    def ensure_connect(func):
        def wrapper(self, *args, **kwargs):
            if not self.is_connected:
                self.build_connect()
            return func(self, *args, **kwargs)

        return wrapper

    @ensure_connect
    def exec_command(self, command: Command):
        return self._exec_command(command)

    @ensure_connect
    async def exec_async_command(self, command: Command):
        status = True

        async def _read(chan):
            future = asyncio.Future()
            loop = asyncio.get_event_loop()

            if self.is_local:
                def on_read():
                    chunk = chan.read()
                    future.set_result(chunk)
            else:
                def on_read():
                    if chan.recv_stderr_ready():
                        status = False
                        chunk = chan.recv_stderr(len(chan.in_stderr_buffer))
                    else:
                        chunk = chan.recv(len(chan.in_buffer))
                    future.set_result(chunk)

            loop.add_reader(chan.fileno(), on_read)

            chunk = await future
            loop.remove_reader(chan.fileno())
            return chunk

        async def _read_all(chan):
            chunks = []
            chunk = await _read(chan)
            while chunk:
                chunks.append(chunk)
                chunk = await _read(chan)
            return b''.join(chunks)

        if self.is_local:
            p = subprocess.Popen(command.cmd, shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT,
                                 bufsize=command.bufsize,
                                 env=command.env
                                 )
            chan = p.stdout
        else:
            transport = self.client.get_transport()
            chan = transport.open_session()
            chan.setblocking(0)
            chan.exec_command(command.cmd)

        data = await _read_all(chan)
        if status is True:
            response = Response(self._machine, BytesIO(data), BytesIO())
        else:
            response = Response(self._machine, BytesIO(), BytesIO(data))
        return response

    @property
    def sftp(self):
        try:
            with self as ssh:
                transport = ssh.get_transport()
                sftp = paramiko.SFTPClient.from_transport(transport)
                return sftp
        except:
            raise Exception('failed to establish sftp')

    @ensure_connect  # `with` statement for connection check
    def __enter__(self):
        return self.client

    def __exit__(self, type, value, traceback):
        pass

    _exec_command = exec_remote_command

    __del__ = close
