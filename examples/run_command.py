from flowlight import Machine

m = Machine('127.0.0.1', connect=True)
print (m.run('ls ~'))
