import logging
import selectors 
import socket
import struct
import os

from queue import Queue
from time import sleep
from threading import Thread

from flowlight.constants import EVENT_CLOSE, EVENT_LOG
from flowlight.tasks.future import TaskFuture
from flowlight.utils.remote import RemoteCallable, dumps, loads


__all__ = ['WorkerProxy']

STOP_SENTINEL = object()


class RequestStore:
    __slots__ = ['data', 'total_size', 'finish_callback']

    BUF_SIZE = 1024

    def __init__(self, finish_callback):
        self.data = b''
        self.total_size = 0
        self.finish_callback = finish_callback

    def __call__(self, key, mask):
        client_socket = key.fileobj
        data = client_socket.recv(self.BUF_SIZE)
        if not self.data:
            self.total_size = int(struct.unpack('>i', data[:4])[0])
            data = data[4:]
        self.data += data
        if len(self.data) == self.total_size:
            self.finish_callback(client_socket, self)

    def get_data(self):
        return self.data


class Worker:
    def __init__(self):
        self._task_list = Queue()
        self._running = True

    def add_task(self, task):
        future = TaskFuture(task)
        self._task_list.put(future)
        return future

    def run(self):
        pool = self._task_list
        while True:
            future = pool.get()
            if future is STOP_SENTINEL:
                break
            task = future.get_task()
            future.ready()
            result = task.callable(*task.args, **task.kwargs)
            future.set_result(result)

    def stop(self):
        """Discard all items and waiting for stop.
        """
        self._task_list.queue.clear()
        self._task_list.put(STOP_SENTINEL)

    def task_count(self):
        return self._task_list._qsize()


class WorkerProxy:
    def __init__(self, manager, child_conn):
        self.conn = child_conn
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        server_socket.bind((manager.host, manager.port))
        server_socket.listen()
        self.server_socket = server_socket
        self._stopped = False
        self.settings = manager.settings

        selector = selectors.DefaultSelector()
        selector.register(self.server_socket.fileno(), selectors.EVENT_READ, self._handle_connection)
        selector.register(self.conn, selectors.EVENT_READ, self._handle_signal)
        self.selector = selector

        self._request_pool = {}

        self._worker = Worker()
        self._worker_thread = Thread(target=self._worker.run)
        del manager

    def _run_worker(self):
        self._worker_thread.start()

    def run(self):
        self._run_worker()
        self._loop()
        self.server_socket.close()

    def stop(self):
        self._stopped = True

    def _loop(self):
        selector = self.selector
        while not self._stopped:
            events = selector.select()
            if not events:
                sleep(1)
            else:
                for key, mask in events:
                    callback = key.data
                    callback(key, mask)

    def _send_result_callback(self, client_socket):
        sock = client_socket
        def _send_action(result):
            nonlocal sock
            sock.sendall(dumps(result))
            sock.close()
            del sock
        return _send_action

    def _request_finish_callback(self, client_socket, client_request):
        task = loads(client_request.get_data())
        if not isinstance(task, RemoteCallable):
            raise Exception('Need a `RemoteCallable` instance')
        future = self._worker.add_task(task)
        future.add_done_callback(self._send_result_callback(client_socket))
        self.selector.unregister(client_socket)
        self._request_pool.pop(client_socket.fileno(), None)

    def _log(self, level, msg):
        self.conn.send((EVENT_LOG, (level, msg)))

    def _handle_connection(self, key, mask):
        client_socket, addr = self.server_socket.accept()
        client_host, client_port = client_socket.getpeername()
        if client_host in self.settings['BLACK_HOST_LIST'] or (
            client_host not in self.settings['WHITE_HOST_LIST'] and self.settings['WHITE_HOST_LIST']
        ):
            self._log(logging.WARN, 'drop connetion from <{}:{}>'.format(client_host, client_port))
            client_socket.close()
        else:
            self._log(logging.DEBUG, 'accept connetion from <{}:{}>'.format(client_host, client_port))
            client_socket.setblocking(False)
            request = RequestStore(self._request_finish_callback)
            self._request_pool[client_socket.fileno()] = request
            self.selector.register(client_socket, selectors.EVENT_READ, request)
            del request

    def _handle_signal(self, key, mask):
        conn = key.fileobj
        event, msg = conn.recv()
        if event == EVENT_CLOSE:
            self.selector.unregister(self.server_socket)
            self.selector.unregister(self.conn)
            self._worker.stop()
            self._worker_thread.join()
            self.stop()
            os._exit(0)
