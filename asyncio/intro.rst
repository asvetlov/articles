Title: Asyncio: введение
Labels: python, networking, asyncio, python3

С выходом Python 3.4 становится доступна новая стандартная библиотека
для асинхронного сетевого программирования
**[asyncio](http://docs.python.org/dev/library/asyncio.html)**. Версия
для Python 3.3 доступна на [google
code](https://code.google.com/p/tulip/) и
[PyPI](https://pypi.python.org/pypi/asyncio), существует также
[Trollius](https://bitbucket.org/enovance/trollius) (backport на
Python 2).

Это не только "еще одна сетевая библиотека" но и эталонный образец
стандарта **[PEP 3156](http://python.org/dev/peps/pep-3156/)**,
цель которого предоставить единую платформу для сторонних библиотек и
альтернативных реализаций.

Задача -- уйти от "зоопарка" **twisted**, **tornado**, **eventlet**,
**gevent** и длинного ряда менее распространенных решений и
пользоваться преимуществами общей базы, как произошло со стандартом на
работу с *реляционными базами данных* **[DBAPI
2.0](http://legacy.python.org/dev/peps/pep-0249/)**.

Задумка у ван Россума очень амбициозная: перейти со временем на
**PEP 3156** во всех сетевых стандартных библиотеках (HTTP, email, ftp и
т.д.), оставив возможность синхронного использования.

Начнем с простого примера HTTP клиента:

    import sys

    import asyncio


    @asyncio.coroutine
    def fetch():
        r, w = yield from asyncio.open_connection('python.org', 80)
        request = 'GET / HTTP/1.0\r\n\r\n'
        print('>', request, file=sys.stderr)
        w.write(request.encode('latin-1'))
        while True:
            line = yield from r.readline()
            line = line.decode('latin-1').rstrip()
            if not line:
                break
            print('<', line, file=sys.stderr)
        print(file=sys.stderr)
        body = yield from r.read()
        return body


    def main():
        loop = asyncio.get_event_loop()
        try:
            body = loop.run_until_complete(fetch())
        finally:
            loop.close()
        print(body.decode('latin-1'), end='')


    if __name__ == '__main__':
        main()


Код читает страничку с http://python.org и печатает её содержимое.

*Обратите внимание: общение идет на уровне ввода-вывода в сокеты и не
касается разбора HTTP headers. Примеры более высокоуровневых библиотек
можно увидеть
[здесь](https://code.google.com/p/tulip/wiki/ThirdParty).*

## Event loop ##

Вызов `asyncio.get_event_loop()` возвращает объект *обработки
сообщений*, он же *event loop*. Если вызов был впервые и мы в главном
потоке -- создаётся новый обработчик, иначе используется старый. Для
порождённых потоков *event loop* нужно создавать явно (в нашем
примере это не актуально).

По умолчанию будет выбран самый производительный вариант *event loop*:
*select*, *poll*, *epoll*, *kqueue*.

Затем нужно вручить циклу обработки сообщений работу:
`loop.run_until_complete(<coroutine>)`.
И, когда всё будет сделано, закрыть все использовавшиеся ресурсы:
`loop.close()`.

В случае *HTTP сервера* мы бы открыли серверный сокет на *0.0.0.0:80*
и запустили `loop.run_forever()`.  Остановить работающий *event loop*
*"изнутри"* можно вызовом `asyncio.get_event_loop().stop()`.

Пока принципиальных различий между *asyncio* и *twisted*-*tornado* не
видно, верно?

## Coroutines ##

Переходим к собственно *сетевой части*.

*Оговорюсь сразу: это самый верхний пользовательский уровень, под
 которым в библиотеке и стандарте скрыто несколько важных слоёв и
 абстракций.*

*По задумке у программиста-прикладника не должно возникать
 необходимости спускаться в "подвал", если только он не делает
 собственную библиотеку*.

Итак, у нас не просто функция `def fetch():`.

Это прежде всего
*генератор*, на что указывают конструкции `yield from` внутри тела
функции.

К тому же применен *декоратор* `asyncio.coroutine`:

    @asyncio.coroutine
    def fetch():
        # generator body

Честно сказать, в нашем примере этот декоратор ничего не делает.  Он
изначально появился в качестве простой метки, что *генератор* как бы
готов к использованию в *asyncio*. Потом зона ответственности
расширилась и самым главным оказалось то, что декоратор смог быть
очень полезным при отладке. *Debug-mode включается отдельно, потому
что замедляет работу библиотеки*.

Добираемся до тела функции-генератора.
Я повторюсь и ещё раз её покажу:

    @asyncio.coroutine
    def fetch():
        r, w = yield from asyncio.open_connection('python.org', 80)
        request = 'GET / HTTP/1.0\r\n\r\n'
        print('>', request, file=sys.stderr)
        w.write(request.encode('latin-1'))
        while True:
            line = yield from r.readline()
            line = line.decode('latin-1').rstrip()
            if not line:
                break
            print('<', line, file=sys.stderr)
        print(file=sys.stderr)
        body = yield from r.read()
        return body

`r, w = yield from asyncio.open_connection('python.org', 80)`

Создаётся сокет и открывается соединение на "python.org", восьмидесятый порт.

Это долгая операция. При плохом интернете занимает секунды.
Поэтому стоит конструкция `yield from`.

Как именно `yield from` работает в `asyncio` я намерен разобрать в
следующей статье.

Пока просто примите на веру: в этом месте наша *сопрограмма*
(извините, не видел более адекватного варианта перевода) отдаёт через
*event loop* своё процессорное время другим, которые уже получили
какие-то данные и готовы работать.

В моём примитивном наброске такого нет, но можете посмотреть на [более
сложный пример
кода](https://code.google.com/p/tulip/source/browse/examples/crawl.py)

М дальшк
