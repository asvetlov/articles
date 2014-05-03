#!/home/andrew/projects/py3k/python

import threading
from concurrent import futures
from collections import defaultdict, namedtuple
from urllib.request import urlopen, URLError

State = namedtuple('State', 'addr ok fail')

class Pinger:
    def __init__(self, pool):
        self._pool = pool
        self._lock = threading.RLock()
        self._results = defaultdict(lambda: {'ok': 0, 'fail': 0})
        self._pendings = set()

    def result(self, addr=None):
        def _make_state(addr, res):
            return State(addr=addr, ok=res['ok'], fail=res['fail'])
        with self._lock:
            if addr is not None:
                result = self._results[addr]
                return _make_state(addr, self._results[addr])
            else:
                return {_make_state(addr, val)
                        for addr, val in self._results.items()}

    @property
    def pendings(self):
        with self._lock:
            return set(self._pendings)

    def ping(self, addr):
        with self._lock:
            future = self._pool.submit(self._ping, addr)
            self._pendings.add(future)
            future.add_done_callback(self._discard_pending)
            return future

    def _discard_pending(self, future):
        with self._lock:
            self._pendings.discard(future)

    def _ping(self, addr):
        try:
            ret = urlopen(addr)
            ret.read()
        except URLError:
            result = False
        else:
            result = True

        with self._lock:
            if result:
                self._results[addr]['ok'] += 1
            else:
                self._results[addr]['fail'] += 1

        return result

if __name__ == '__main__':
    from pprint import pprint

    with futures.ThreadPoolExecutor(max_workers=3) as pool:
        pinger = Pinger(pool)

        pinger.ping('http://google.com')
        pinger.ping('http://ya.ru')

        print("State for 'ya.ru'", pinger.result('http://ya.ru')) # 1

        future = pinger.ping('http://python.su/forum/index.php')
        print("Result for 'python.su'", future.result()) # 2

        pinger.ping('http://asvetlov.blogspot.com')

        futures.wait(pinger.pendings) # 3

        print("Total table")
        pprint(pinger.result()) # 4
