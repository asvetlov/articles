Title: Питон: времена, даты и временные зоны
Labels: python, datetime, time zone

В статье [Питон:
времена, даты и временные зоны](http://asvetlov.blogspot.com/2011/02/date-and-time.html) я рассказывал, что такое *абсолютное*
и *относительное* время в терминах Питона.

И упоминал, что сравнение *относительного* и *абсолютного* времени выбросит
исключение `TypeError`. В **Python 3.3** ситуация изменилась.

*Относительное* и *абсолютное* времена всё ещё нельзя сравнивать
*на упорядоченность* (больше или меньше). Сравнение *на эквивалентность*
никогда не срабатывает, при этом ошибки нет.

Пример:

    >>> from datetime import datetime, timezone
    >>> naive = datetime.now()
    >>> aware = datetime.now(timezone.utc)
    >>> naive < aware
    Traceback (most recent call last):
      ...
    TypeError: can't compare offset-naive and offset-aware datetimes
    >>> naive == aware
    False

Ещё раз подчеркиваю: *относительное* время **никогда** не равно *абсолютному*
вне зависимости от того, на какое время суток они указывают.

Подробности можно прочитать [в багтрекере](http://bugs.python.org/issue15006).
