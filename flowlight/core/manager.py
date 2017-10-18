import atexit
import logging
import multiprocessing as mp
import os
import sys
import selectors
import signal
import weakref
from time import sleep

from flowlight.core.setting import Setting
from flowlight.constants import EVENT_CLOSE, EVENT_LOG
from flowlight.core.worker import WorkerProxy


__all__ = ['Manager']


class ManagerSetting:
    """for manager's custom settings.
    """
    def __init__(self):
        self.__settings = {}
        global_settings = Setting.__dict__
        for key in global_settings:
            # copy from global settings
            self[key] = global_settings[key]

    def __setitem__(self, key, value):
        self.__settings[key] = value

    def __getitem__(self, key):
        return self.__settings.get(key, None)


class ChildManager:
    def __init__(self, pid, parent_conn):
        self.pid = pid
        self.conn = parent_conn

    def close(self):
        self.conn.close()


class Manager:
    def __init__(self, addr,
        stdin='/dev/null',
        stdout='/dev/null',
        stderr='/dev/null',
        log_path='/dev/null',
        log_level=logging.DEBUG
    ):
        self._workers = {}
        self.host = addr[0]
        self.port = addr[1]
        self.selector = selectors.SelectSelector()
        self._stopped = False
        self.settings = ManagerSetting()

        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

        logger = logging.getLogger()
        handler = logging.StreamHandler(stream=open(log_path, 'a+'))
        formatter = logging.Formatter('[%(levelname)s] %(asctime)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(log_level)
        self.logger = logger
    
    def _del_pid(self):
        if os.path.exists(Setting.PID_FILE):
            os.remove(Setting.PID_FILE)

    def _initialize(self):
        atexit.register(self._del_pid)
        with open(Setting.PID_FILE, 'w') as pidfile:
            pidfile.write('{}'.format(os.getpid()))
    
    def _new_worker(self):
        parent_pipe, child_pipe = mp.Pipe()
        self.selector.register(parent_pipe, selectors.EVENT_READ, self._handle_event)
        pid = os.fork()
        if not pid:
            parent_pipe.close()
            worker = WorkerProxy(weakref.proxy(self), child_pipe)
            worker.run()
        else:
            self._workers[parent_pipe.fileno()] = ChildManager(pid, parent_pipe)
            child_pipe.close()
            return

    def _sighup_handler(self, frame, num):
        pass

    def _sigint_handler(self, frame, num):
        self._stopped = True

    def _sigterm_handler(self, frame, num):
        self._stopped = True

    def _create_signals(self):
        signal.signal(signal.SIGHUP, self._sighup_handler)
        signal.signal(signal.SIGINT, self._sigint_handler)
        signal.signal(signal.SIGTERM, self._sigterm_handler)

    def _create_workers(self):
        for i in range(self.settings['WORKER_NUM']):
            self._new_worker()

    def _handle_log(self, log):
        level, msg = log
        self.logger.log(level, msg)

    def _handle_event(self, key, mask):
        conn = key.fileobj
        event, msg = conn.recv()
        if event == EVENT_LOG:
            self._handle_log(msg)

    def _loop(self):
        selector = self.selector
        while not self._stopped:
            events = selector.select(0.5)
            if events:
                for key, mask in events:
                    callback = key.data
                    callback(key, mask)
            else:
                sleep(1)

    def _daemonize(self):
        pid = os.fork()
        if pid != 0:
            sys.exit(0)
        os.chdir('/')
        os.setsid()
        os.umask(0)
        pid = os.fork()
        if pid != 0:
            sys.exit(0)
        sys.stdout.flush()
        sys.stderr.flush()
        stdin = open(self.stdin, 'r')
        stdout = open(self.stdout, 'a+')
        stderr = open(self.stderr, 'a+')
        os.dup2(stdin.fileno(), sys.stdin.fileno())
        os.dup2(stdout.fileno(), sys.stdout.fileno())
        os.dup2(stderr.fileno(), sys.stderr.fileno())

    @classmethod
    def get_pid(cls):
        if not os.path.exists(Setting.PID_FILE):
            return None
        with open(Setting.PID_FILE) as pidfile:
            pid = pidfile.read()
            return int(pid)

    def run(self, daemon=False):
        if self.get_pid() is not None:
            print('Workers already running...')
            sys.exit(0)
        if daemon is True:
            self._daemonize()
        self._initialize()
        self._create_signals()
        self._create_workers()
        self._loop()
        self._free_workers()

    def shutdown(self):
        self._stopped = True

    def _free_workers(self):
        childs = list(self._workers.values())
        for child in childs:
            fd = child.conn.fileno()
            try:
                self.selector.unregister(child.conn)
            except:
                pass
            try:
                child.conn.send((EVENT_CLOSE, ''))
                child.close()
            except IOError:
                pass
            if fd in self._workers:
                del self._workers[fd]
            os.waitpid(child.pid, 0)
