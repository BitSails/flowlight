from flowlight import Machine


m = Machine('host1', connect=True)
m.put('/tmp/remote_file', '/tmp/local_file') # upload
m.get('/tmp/local_file', '/tmp/remote_file') # download
