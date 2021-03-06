Title: Абстрактные классы для коллекций
Labels: python, containers, abc

Пусть мы сделали какой-то класс для хранения набора данных. Например,
настроек вида *ключ -> значение*:

    class Settings:

        def __init__(self):
            self._data = {}

        def add_property(self, key, value):
            assert isinstance(key, str), key
            self._data[key] = value

        def get_property(self, key):
            assert isinstance(key, str), key
            return self._data[key]

И тут нам в голову приходит удачная идея, что было бы здорово вместо
вызова `settings.get_property('key')` использовать квадратные скобки как для
`dict`: `settings['key']`:

    def __getitem__(self, key):
        return self.get_property(key)

Что не так?

То, что наш класс стал отчасти походить на *readonly dict* (он же
*mapping*) -- но он не реализует весь предполагаемый *контракт*.

Так, я привык, что если класс похож на *readonly dict*, то он
позволяет узнать количество элементов в нём. Добавляем `__len__`:

    def __len__(self):
        return len(self._data)

Всё ещё не хорошо. Для *mapping* обычно можно итерироваться по
ключам. Добавление `__iter__` решает проблему:

    def __iter__(self):
        return iter(self._data)

Всё? Нет! Хочется ещё проверять на наличие ключа: `key in settings` --
`dict` ведь это позволяет!

Можем добавить метод `__contains__` -- а можем вспомнить, что есть
класс `collections.abc.Mapping`.

Это *абстрактный базовый класс*, задающий *контракт* для неизменяемого словаря.

*Описание того, что таке абстрактный базовый класс --
 [здесь](https://docs.python.org/3/library/abc.html)*

Просто наследуемся от `Mapping`:

    from containers.abc import Mapping

    class Settings(Mapping):

        # ...

В качестве бесплатного бонуса получам поддержку `.get()`, `.keys()`,
`.items()`, `.values()`, `__eq__` и `__ne__`.

Реализация этих методов не оптимальная с точки зрения
производительности, но она уже есть *из коробки*. К тому же всегда
можно добавть свой вариант, который будет работать быстрее стандартного
(если мы знаем как это сделать).

Если мы забудем реализовать какой-то критически важный метод -- при
создании экземпляра класса получим исключение:

    >>> settings = Settings()
    TypeError: Can't instantiate abstract class Settings with abstract methods __iter__

В *стандартной библиотеке* есть большой набор *абстрактных базовых классов*:

* ByteString
* Callable
* Container
* Hashable
* ItemsView
* Iterable
* Iterator
* KeysView
* Mapping
* MappingView
* MutableMapping
* MutableSequence
* MutableSet
* Sequence
* Set
* Sized
* ValuesView

Очень рекомендую изучить набор методов, реализуемых этими классами --
помогает понять систему типов собственно Питона.

При необходимаости можно (и нужно) написать свои.

А в заключение забавный пример.

В библиотеке `sqlalchemy` есть класс `RowProxy` для строки-кортежа,
получаемой в результате *SQL запроса*.

Класс выглядит как *mapping*: имеет длину, `.keys()`, `.items()`,
`.__contains__()` и все прочие нужные методы. Позволяет получать
значение как по позиционному номеру так и по названию колонки в базе
данных.

При этом он реализует *контракт* `Sequence` (как у `tuple`).

Т.е. `iter(row)` возвращает данные, а не названия колонок. И это
немного сбивает с толку: выглядит как утка, а крякает как поросёнок.

В оправдание `sqlalchemy` могу сказать, что `RowProxy` появился в
самой первой версии алхимии, еще до того как в Питон добавили
`collections.abc`. А потом что-то менять стало поздно.

Но сейчас при разработке собственных библиотек стоит придерживаться
устоявшихся стандартов и активно применять *абстрактные базовые классы
для коллекций*.
