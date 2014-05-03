Title: Оценка производительности aiozmq
Labels: aiozmq, benchmark

Сделал "пузомерку" для сравнения производительности
[aiozmq](https://pypi.python.org/pypi/aiozmq) и *просто*
[pyzmq](https://pypi.python.org/pypi/pyzmq/).

*aiozmq* использует *pyzmq* в своих внутренностях и стало интересно
 узнать, какие тормоза добавляет связка *aiozmq* + *asyncio* по
 сравнению с "простыми zmq сокетами".

Тест делался для пары *DEALER*/*ROUTER* (*RPC*) в разных режимах.

Результаты запуска [измерителя
производительности](https://github.com/aio-libs/aiozmq/blob/master/benchmarks/simple.py):

    (aiozmq)andrew@tiktaalik2:~/projects/aiozmq (master)$ python benchmarks/simple.py -n 10000
    Run tests for 10*10000 iterations: ['aiozmq.rpc', 'core aiozmq', 'single thread raw zmq', 'single thread zmq with poller', 'zmq with threads']
    ..................................................

    Results for aiozmq.rpc
    RPS: 2469,   average: 0.405 ms

    Results for core aiozmq
    RPS: 5064,   average: 0.197 ms

    Results for single thread raw zmq
    RPS: 9895,   average: 0.101 ms

    Results for single thread zmq with poller
    RPS: 12574,  average: 0.080 ms

    Results for zmq with threads
    RPS: 9702,   average: 0.103 ms


*zmq* шустрее, естественно. Обработка **request-response** на *zmq* в
 одном потоке примерно вдвое быстрее той же работы, которую делает
 *aiozmq* на своих транспортах и протоколах, плюс еще *asyncio*
 добавляет тормозов.

Даже на нитях (threads) *zmq* уверенно побеждает. В этом заслуга
*libzmq*, которая создает свой внутренний thread для обработки send и
в результате для Питона send получается неблокирующим.

*aiozmq.rpc* добавляет тормозов по сравнению с *aiozmq.core* примерно
 в два раза. Я считаю это приемлемой платой за прозрачную
 упаковку/распаковку аргументов вызываемой функции, поиск обработчика
 на стороне сервера, проверку сигнатур для параметров, пробрасывания
 исключения назад вызывающей стороне.

Если всю эту необходимую работу сделать на *zmq* -- думаю, получится
не сильно быстрее.

## Результат

*aiozmq.core* дает примерно 5000 *requests per second*, что довольно неплохо.

*aiozmq.rpc* способен выжать примерно 2500 *rps*.

То есть если вас устраивает обработка запроса к *aiozmq.rpc* меньше
чем за одни *милисекунду* -- *aiozmq* вам подойдёт.

И, **самое главное**: если на стороне RPC сервера вы делаете запросы в
*redis, mongo, postgresql, mysql* или обращаетесь каким другим
*внешним для вашего процесса ресурсам* -- скорее всего тормоза будут
именно в этом месте.

## Почему это не очень важно

Да, я знаю что *redis* неимоверно быстр: показывает 70000+ *rps* на
простых запросах. Но скорее всего вам таких обращений потребуется
несколько, и делать вы их будете из питона используя библиотеку вроде
[asyncio-redis](https://github.com/jonathanslenders/asyncio-redis).

Которая добавляет немало приятных плюшек и расплачивается за это
**производительностью**.

Это не значит что за скорость не нужно бороться. Просто для меня
*aiozmq* показала ожидаемые и вполне неплохие результаты.  Самый
простой путь к ускорению лежит в оптимизации *asyncio* путём создания
*optional C Extensions* для *event loop* и *selector*. Возможно, я этим
займусь, или сделают другие Python Core Developers.  Как это произошло
с [модулем io](https://docs.python.org/dev/library/io.html) из стандартной
библиотеки: после того как его переписали на С в Python 3.2 получили
30% ускорение.
