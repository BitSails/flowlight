# flowlight
[![Build Status](https://travis-ci.org/tonnie17/flowlight.svg?branch=master)](https://travis-ci.org/tonnie17/flowlight)

a tool make remote operations easier

## Install

```
pip3 install git+git://github.com/tonnie17/flowlight.git@master
```

## RPC Worker Mode

lauch flowlight workers.

```
$flowlight worker start
```

or take it easy in your codes.

```python
manager = Manager(('127.0.0.1', 3600), log_path='./log')
manager.settings['WHITE_HOST_LIST'].add('127.0.0.1')
manager.run(daemon=False)
```

do some works on remote workers.

```python
from flowlight import Machine

def compute(*args, **kwargs):
    return sum(args)

m = Machine('127.0.0.1')
print (m.run_remote_callable(compute, 1, 2, 3))
# 6
```

stop workers.

```
$flowlight worker stop
```

show workers status

```
$flowlight worker status
```

## API Mode

```
$flowlight api
FlowLight API serve on 3601...
 Usage:: http://127.0.0.1:3601/<machines>/<command>
```

Run command via URL.

```
http -f GET "http://127.0.0.1:3601/127.0.0.1/whoami"
```

output:

```json
[
    {
        "host": "127.0.0.1",
        "result": "tonnie\n"
    }
]
```

multiple executions.

```
http -f GET "http://127.0.0.1:3601/host1,host2/ps aux|wc -l"
```

output:

```json
[
    {
        "host": "host1",
        "result": "     284\n"
    },
    {
        "host": "host2",
        "result": "     284\n"
    }
]
```

## Usage

Run task via ssh on remote machines.

```python
from flowlight import Cluster, Group, task

cluster = Cluster(['host1', Group(['host2', 'host3'])])
cluster.set_connection(password='password')

@task
def create_file(task, cluster):
    responses = cluster.run('''
    echo {value} > /tmp/test;
        '''.format(value=task.value)
    )
    task.value += 1

@create_file.on_start
def before_create_file(task):
    task.value = 1

@create_file.on_complete
def after_create_file(task):
    print(task.value)

@create_file.on_error
def error_when_create_file(exception):
    print(exception)
    import traceback
    traceback.print_exc()

cluster.run_task(create_file)
```

output:

```
2
```

Use `run_after` to set order of tasks.

```python
@task(run_after=create_file)
def show_file(meta, cluster):
    responses = cluster.run('''
        cat /tmp/test;            
    ''')
    for res in responses:
        print(res)

cluster.run_task(show_file)
```

Use trigger in multi-threading.

```python
import threading
from time import sleep
after = threading.Thread(target=lambda: cluster.run_task(show_file))
before = threading.Thread(target=lambda: cluster.run_task(create_file))
after.start()
print('sleep a while...')
sleep(2)
before.start()
before.join()
after.join()
```

output:

```
sleep a while...
2
1

1

1
```

Use `run_only` for task running pre-check.

```python
@task(run_only=lambda: 1 > 2)
def fail_task(self):
    print('condition is passed')

err, status = cluster.run_task(fail_task)
```

Async tasks supported.

```python
async def async_task(machine):
    response = await machine.run_async("ls")
    return response

m = Machine('host1', connect=True)
m2 = Machine('host2', connect=True)

ev_loop = asyncio.get_event_loop()
ev_loop.run_until_complete(asyncio.gather(
    async_task(m), async_task(m2)
))
ev_loop.close()
```

File upload & download

```python
m = Machine('host1', connect=True)
m.put('/tmp/remote_file', '/tmp/local_file') # upload
m.get('/tmp/local_file', '/tmp/remote_file') # download
```

Jump host

```python
js = Machine('47.88.174.112', port=22, connect=True)
with js.jump_to('127.0.0.1', 32768, password='root') as rs:
    print(rs.run('ifconfig'))
```
