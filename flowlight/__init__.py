from .core import (
    Connection,
    Response,
    Manager,
    WorkerProxy,
    Command,
    Setting
)
from .model import (
    Machine,
    Group,
    Cluster
)
from .tasks import (
    TaskFuture,
    TaskMeta,
    TaskState,
    task
)
from .utils import (
    Signal,
    Trigger
)


import os
from flowlight.api import api_serve
from flowlight.core.setting import Setting


def worker(args):
    def start():
        manager = Manager(('127.0.0.1', Setting.PORT))
        manager.run(daemon=True)

    def stop():
        import signal
        pid = Manager.get_pid()
        if pid is not None:
            try:
                os.kill(int(pid), signal.SIGINT)
            except ProcessLookupError:
                pass

    def status():
        if os.path.exists(Setting.PID_FILE):
            try:
                os.kill(Manager.get_pid(), 0)
                print('running')
            except OSError:
                return False
            else:
                return True
        print('stopped')
        return False

    cmd = args.cmd
    if cmd == 'start':
        start()
    elif cmd == 'stop':
        stop()
    elif cmd == 'status':
        status()

def api(args):
    api_serve()

def enter():
    import argparse
    parser = argparse.ArgumentParser(description='Flowlight')
    subparsers = parser.add_subparsers(title='mode')

    worker_cmd = subparsers.add_parser('worker', help='worker mode', description='worker mode')
    worker_cmd.add_argument('cmd', help='start|stop|status')
    worker_cmd.set_defaults(func=worker)

    api_cmd = subparsers.add_parser('api', help='api mode', description='api mode')
    api_cmd.set_defaults(func=api)

    try:
        args = parser.parse_args()
        args.func(args)
    except (AttributeError, argparse.ArgumentError):
        parser.print_help()
