Title: Недостатки greenlets.
Labels: python, многопоточность, сети

В этом посте я хочу пройтись по *неочевидным* проблемам использования
**Greenlet** и основанных на нём библиотек *gevent* и *eventlet*.

Прежде всего нужно коротко рассказать, что такое вообще greenlet и
почему его используют.

## Greenlet

[greenlet](https://pypi.python.org/pypi/greenlet) — это библиотека для
создания *легковестных потоков с невытесняющей многозадачностью*.

Простой пример из документации:

    from greenlet import greenlet

    def test1():
        print 12
        gr2.switch()
        print 34

    def test2():
        print 56
        gr1.switch()
        print 78

    gr1 = greenlet(test1)
    gr2 = greenlet(test2)
    gr1.switch()
    print 'done'

Создаём два greenlet: `gr1` и `gr2`.
Переключаемся на `gr1`.
Печатаем *12*
Переключаемся на `gr2`.
Печатаем *56*.
Переключаемся снова на `gr1`. Выполнение продолжается со строки `gr2.switch()`.
Печатаем *34*.
`gr1` заканчивает работу, выходим в родительский greenlet и печатаем `'done'`.
Программа закончена, хоть `gr2` не выполнился до конца и не напечатал *78*.

Что мы видим? Greenlets очень похожи на обычные потоки, но в отличие
от последних переключение происходит явно в вызове
`.switch()`. Повторное переключение на уже запущенный greenlet
продолжает выполнение кода с того места, где этот самый greenlet
вызвал `.switch()`, добровольно передав управление какому-то другому
greenlet.

Схема понятная и простая. Конечно, существует ещё несколько
задокументированных полезных возможностей. В `.switch()` можно
передавать параметры, можно использовать `.throw()` для передачи
исключения. Всегда можно узнать какой greenlet выполняется прямо
сейчас. И так далее.

Для вводной части это несущественно.

Важно, что мы можем сделать миллион greenlet и быстро переключаться между ними.

На современных компьютерах такого количества одновременно действующих
потоков достичь невозможно. Если процесс запускает 10 потоков — это
нормально. 100 — тоже, пожалуй, терпимо. 1000 уже вызовет очень
заметное падение производительности а миллион просто вгонит
операционную систему в ступор. Да и не дадут вам создать миллион потоков.

Проблема в том, что переключение потока операционной системы довольно
затратная операция. Windows делает это быстрее, Unix медленней. Но всё
равно получается *слишком медленно* чтобы одновременно обрабатывать
пресловутые 10К (десять тысяч потоков).

Пока еще непонятно, как greenlets облегчает жизнь простого программиста.

## gevent и eventlet

рассмотрим такой код:

    import socket

    s = socket.socket()
    s.connect(('localhost', 6666))
    data = s.recv(1024)

Мы создаём синхронный socket, делаем `s.connect` (тоже синхронный, но
это не главная беда) и ждём `s.recv(1024)`. Опять-таки синхронно.

В этом месте наша программа затыкается пока другая сторона в этот
socket не напишет хоть что-нибудь.

Теперь тот же код с использованием gevent

    import gevent.socket

    s = gevent.socket.socket()
    s.connect(('localhost', 6666))
    data = s.recv(1024)

Вроде бы ничего не поменялось. Но если `s.recv` должен ждать, то
gevent переключится на другой greenlet. Когда данные будут готовы, наш
код опять получит управление.

Т.е. всё становится очень удобно: пишем в синхронном стиле, создаём
столько greenlet сколько нужно, а gevent сам переключается между
нашими зелёными потоками. Притормаживает их выполнение если нужно
ждать ввода-вывода и возобновляет когда I/O операция завершена. Дёшево
и сердито.

Но в любой системе, построенной на основе greenlet, есть несколько
ложек дёгтя. Давайте ими займёмся.

## stack slicing

## Обязательная синхронизация

Зелёные потоки создают иллюзию синхронного кода. Это здорово.

Но при этом, в отличие от twisted/tornado/tulip, нужно чётко
осознавать, что мы пишем мультипоточную программу.

Вроде бы greenlet предполагает явные места переключения потоков. На
самом деле это не совсем так.

Переключение может произойти в любом месте, совершенно неожиданно для
программиста.

Например, у нас есть функция, которая что-то считает и не делает
никакого ввода-вывода. Может ли в ней произойти переключение потоков?

На первый взгляд нет.

А теперь небольшое уточнение: эта функция пишет в лог, делая
стандартный `logging.info()`. Вести логи — это стандартная полезная
практика, верно?

Спустя какое-то время у логов добавляется новый `logging.Handler`,
который шлёт сообщения куда-то по сети. И этот наш обработчик
использует зелёные сокеты — просто чтобы работа не блокировалась на
передаче сообщений.

И рассматриваемая функция уже неявно вызывает переключение
потоков. Код не поменялся, просто изменилась система
логирования.

Чем чревато переключение потоков? Тем, что наш код обязан сразу
строится как многопоточный, с непременным применением блокировок для
доступа к разделяемым объектам и т.д.

gevent и eventlet имеют необходимые объекты синхронизации. У gevent
набор побогаче и напоминает стандартный: `Rlock`, `Semaphore`,
`Condition`. eventlet имеет лишь `Semaphore`.

Проблема в другом: многие ли программисты, применяющие зелёные потоки,
используют блокировки в своём коде? Или можно задать вопрос шире:
насколько велик процент тех, кто правильно умеет работать с потоками?

Как только речь заходит о многопоточном программировании, первое что
пишут: создавать такие программы сложно. Правильно синхронизировать
работу потоков и осуществлять одновременный доступ к общим ресурсам
нелегко. И это — чистая правда.

Зелёные потоки задачу не облегчают и требования по синхронизации не отменяют.

Более того, из-за более редких и полудетерминированных (по сравнению
со стандартными потоками) переключениях контекста «запас прочности» у
зелёных потоков выше. Другими словами на тестах всё работает
хорошо. На небольшой нагрузке тоже. И только тогда, когда в системе
появляется *много* параллельных задач, код сурово и необратимо ломается.

Т.е. ломается на production, а в тестовом окружении воспроизвести
ошибку нелегко.

## Нарушение стандартного способа исполнения кода в Python

Наконец, последняя мелочь. Код, исполняемый в зелёном потоке, работает
немного отлично от этого же кода, работающего в обычном контексте.

Пример:

    try:
        do_something()
    except Exception as ex:
        log(ex)
        raise

Если log(ex) вызывает переключение потока (например, передавая логи по
сети), то контекст исключения будет сброшен. В результате *raise*
выдаст ошибку, т.к. текущее исключение будет *None*.

Поправить дело очень просто:

    try:
        do_something()
    except Exception as ex:
        exc_type, exc_val, exc_tb = sys.exc_info()
        log(ex)
        raise exc_type, exc_val, exc_tb

Второй вариант работает с зелёными потоками, но ведь и первый тоже
вроде как был правильный!

Я не знаю, где ещё можно поймать неприятности. Но и показанного
достаточно для демонстрации простой мысли: *greenlet* и основанные на
этой технике библиотеки не являются «прозрачной» заменой обычным
потокам. Иногда код ведёт себя совершенно иначе.

## Завершение

После критики хотелось бы сказать несколько слов в защиту
*greenlet*.

Во первых и в главных эта штука очень быстрая.

Во вторых для небольшого проекта, разрабатываемого маленьким
коллективом, поддерживать код в рабочем состоянии довольно
несложно. Если исходники очень объёмны, странные баги лезут со всех
сторон. Компетенции разработчиков может не хватать, потому что ошибка
проявляется совершенно не в том коде который её совершил. Кому чинить
— непонятно. Никто не знает как чинить и, главное, где чинить.

В результате имеем «пороховую бочку»: пока всё работает, но небольшие
изменения в безобидном вроде бы коде могут всё необратимо сломать. И
выявить, что именно нарушило стабильную работу, может быть
нелегко. Ещё раз повторюсь: на тестах всё работает, а когда обнова
выкатывается на production — ломается.

Понять, какая из фич была причиной краха, очень часто бывает нелегко.

Для маленьких проектов таких проблем не существует, кода немного и он
легко обозрим.
