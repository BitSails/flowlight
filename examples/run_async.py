from flowlight import Machine
import asyncio


async def async_task(machine):
    response = await machine.run_async("date;sleep 2;date;")
    print(response)
    return response

m = Machine('127.0.0.1', connect=True)
m2 = Machine('127.0.0.1', connect=True)

ev_loop = asyncio.get_event_loop()
ev_loop.run_until_complete(asyncio.gather(
    async_task(m), async_task(m2)
))
ev_loop.close()
