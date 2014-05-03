Title: aiozmq -- поддержка ZeroMQ сокетов в asyncio
Labels: python, networking, asyncio, python3, aiozmq

Наверное, уже все слышали про
[asyncio](https://docs.python.org/dev/library/asyncio.html) -- новую
стандартную библиотеку для асинхронного сетевого программирования.

Естественно, **asyncio** не умеет работать с **ZeroMQ** сокетами и
никогда не будет уметь.

На днях я выпустил первую версию библиотеки
[aiozmq](https://pypi.python.org/pypi/aiozmq), которая устраняет проблему.

**aiozmq** предоставляет *0MQ event loop* совместимый с **asyncio** и
высокоуровневые средства для организации *вызовов удалённых процедур
aka RPC*.

Если интересны подробности -- читайте
[документацию](http://aiozmq.readthedocs.org/en/0.1/), она довольно
большая и подробная (постарался).
