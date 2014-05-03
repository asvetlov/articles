Title: Текстовое представление чисел с плавающей запятой в Питоне
Labels: python, repr, float

В ходе довольно жаркой дискуссии был затронут 
один интересный вопрос: преобразование `float` в `str`.

Коротко о сути проблемы:
------------------------

На Питоне 2.6 число `4.31` выглядит как `4.3099999999999996`:

    Python 2.6.6 (r266:84292, Sep 15 2010, 16:22:56) 
    [GCC 4.4.5] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> 4.31
    4.3099999999999996
    >>> 

Питон 2.7 (и 3.1) работает несколько иначе:

    Python 2.7.0+ (r27:82500, Sep 15 2010, 18:14:55) 
    [GCC 4.4.5] on linux2
    Type "help", "copyright", "credits" or "license" for more information.
    >>> 4.31
    4.31
    >>> 

Это баг или изменение записи `float` чисел?

Ни то ни другое.

Во первых, это _одно и то же число_:

    >>> 4.31 == 4.3099999999999996
    True
    >>> 

Во вторых, _битовые записи обоих чисел совпадают_.

Т.е. это имеенно то же самое число, 
а не результат какого-то хитрого поведения операции сравнения:

    >>> import struct
    >>> a = struct.pack('d', 4.31)
    >>> b = struct.pack('d', 4.3099999999999996)
    >>> a == b
    True
    >>> 
    
Можно приести еще несколько примеров, 
доказывающих идентичность - но это излишне.

Так что же поменялось?
------------------------

Изменилась реализация метода `__repr__`, 
т.е. преобразование `float` в строку `str`.

Это отражено в [баг трекере Питона](http://bugs.python.org/issue1580) 
и [списке изменений](http://docs.python.org/py3k/whatsnew/3.1.html).

Видимо, текст по приведенным ссылкам недостаточно хорошо описывает суть
проделанной работы. 

Попытаюсь пересказать на русском и более развернуто.
---------------------------------------------------

Имеем дробь `4.31`. 
В float она хранится в виде `<знак>1.<мантисса> * pow(2, <экспонента>)`


Знак и экспонента сейчас не важны. 
Мантисса - дробная часть числа, записанная по основанию два.

Оригинальная запись была `"4.31"`, дробная часть пишется по основанию `10`.

Когда переводим из десятичного основания в двоичное - получаем бесконечную дробь. 
Примерно как натуральная дробь `1/3` в переводе 
на десятичное основание - тоже бесконечная.

В float мантисса записывается "пока хватает места", 
а (возможно, бесконечный) остаток выбрасывается.

Если записывать `1/3` с точностью до `3` знаков, получим `0.333`. 

В `float` пятьдесят три (считая со старшей неявной единицей) двоичных разряда. 

Я не хочу приводить эту длинную простыню ноликов и единичек, 
достаточно представить что она есть.

Теперь нужно обратно перевести float в строку в десятичном представлении.
-------------------------------------------------------------------------

Двоичное число стало конечным. 

Но из-за отсечения не поместившихся бит оно 
не точно соответствует десятичному числу, 
из которого конструировалось.

Python 2.6- (и Python 3.0) делали это так: 
преобразовывали "как есть" и получали длинный "хвост" - `4.3099999999999996`

В Python 3.1 (а после и в Python 2.7) алгоритм поменяли. 
Это длинная простыня `format_float_short` в `./Python/pystrtod.c`

Работает она так: 

У нас есть мантисса `<b1 b2 b3 b4 b5>` - на самом деле 52 бита.

Переводим ее в десятичную форму: `<d1 d2>`. 
Перевод остановился на `b3`, например 
- потому что `b4` и `b5` не дают десятичного числа, нужны еще биты. 

Последняя десятичная цифра `d3` - неполная, 
потому что входной поток бит закончился раньше, 
чем мы получили их достаточное количество.

Добавляем в этот поток все возможные комбинации, 
необходимые для завершения построения `d3`.

Выбираем из всех возможных `d3` такую цифру, 
чтобы результирующее число имело минимальную запись.
Чем больше выходит десятичных ноликов в конце, тем лучше.

Вуаля, получили минимальное десятичное представление 
двоичного числа.

Легко заметить, чем отличается старый алгоритм от нового.
Старый добавлял нулевые биты для построения `d3`, в то время как 
новый подбирает их по более умному принципу.

Заключение
----------

Внимание, это - не округление в математическом смысле слова. 

Алгоритм подбирает такой остаток, 
не поместившийся в мантиссу из-за конечного ее размера, 
чтобы результат можно было записать минимальным количеством цифр.

Точность при этом не теряется 
- десятичное число "длиннее" в двоичном виде, 
чем мантисса в float и при этом совпадает с ней на первых 52 битах.

Получилось всё еще довольно сложно и запутанно - 
но этот вопрос крайне нелегко объясняется "на пальцах".

Вот документ, с которого всё начиналось: 
[FP-Printing-PLDI96.pdf](http://www.cs.indiana.edu/~burger/FP-Printing-PLDI96.pdf)

Довольно много математики.


*Довеском предлагаю ознакомится с замечательными статьями по работе чисел
с плавающей запятой*.

- [Что нужно знать про арифметику с плавающей запятой](http://habrahabr.ru/blogs/cpp/112953/)

- [Откуда берутся NaNы?](http://habrahabr.ru/blogs/cpp/116300/)