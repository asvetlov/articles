import asyncio

@asyncio.coroutine
def f():
    print("Before sleep")
    yield from asyncio.sleep(1)
    print("After sleep")

asyncio.get_event_loop().run_until_complete(f())
