Title: asyncio и HTTP
Labels: python, networking, asyncio, python3, aiohttp, aiorest

[asyncio](https://docs.python.org/dev/library/asyncio.html) не умеет
работать с HTTP.

Так и было задумано.

**asyncio** никогда не станет веб-сервером. Он делался как именно
*event loop* для *tcp*, *ssl*, *unix sockets*, *pipes* и *subprocesses*.
Плюс *streaming API*.

Веб был сознательно выпилен и теперь то что было лежит в [aiohttp](
https://github.com/KeepSafe/aiohttp). Эта часть просто не дозрела до
включения в стандартную библиотеку.

Идея такая:

 * *WSGI* -- синхронный протокол, для asyncio не подходит.
 * Какой будет новый стандарт -- неясно никому.
 * Пусть для *asyncio* люди попытаются сделать свои *http* либы и время
   покажет у кого получилось лучше.
 * Тогда, возможно, и появится новый стандарт.

Что касается меня то я пытаюсь понять какой именно должен быть
**API** для **HTTP server**, что там **должно быть обязательно** и что нужно
**сознательно исключить**.

Сейчас делаем это [aiorest](https://github.com/aio-libs/aiorest)

Когда поймём, что получилось хорошо в *aiorest* -- займемся
перенесением удачных решений в *aiohttp*. Там *HTTP server*
слишком уж неудобный. А нужно что-то типа *tornado.web*, но более
симпатичное и приятное.