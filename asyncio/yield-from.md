Title: Asyncio: yield from
Labels: python, networking, asyncio, python3

С выходом Python 3.4 становится доступна новая стандартная библиотека
для асинхронного сетевого программирования
[asyncio](http://docs.python.org/dev/library/asyncio.html). Версия для
Python 3.3 доступна на [google code](https://code.google.com/p/tulip/)
и [PyPI](https://pypi.python.org/pypi/asyncio), существует также
[Trollius](https://bitbucket.org/enovance/trollius) (backport на
Python 2).

Описать принципы работы в одной статье довольно тяжело, поэтому начну
с наиболее бросающегося в глаза нововведения -- использования
конструкции `yield from`.

Вот так это выглядит:

    import asyncio

    @asyncio.coroutine
    def coro():
        print("Before sleep")
        yield from asyncio.sleep(1)
        print("After sleep")

    asyncio.get_event_loop().run_until_complete(coro())

Создаем сопрограмму `coro` в которой делаем `yield from
asyncio.sleep(1)`.  Вызов `time.sleep(1)` блокировал бы вызывающий
поток на одну секунду.  `yeild from asyncio.sleep(1)` переключает
*цикл обработки сообщений* с выполнения `coro` на другую задачу,
которая дожидается своей очереди (в примере такой пока нет).
