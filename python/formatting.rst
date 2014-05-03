Title: Форматирование строк
Labels: python, string formatting

Речь идет об обычных строках, не касаясь шаблонных движков и прочих занятностей.

* Вы используете эту операцию по много раз на дню.
* Вы даже предпочитаете новый стиль форматирования, 
    использующий `.format` вместо `%`.
* Вы знаете о форматировании всё!

Я тоже так считал, пока один случай не заставил пересмотреть своё мнение.

Думаю, эти несколько рецептов по форматированию будут интересны и полезны.

Пристегнулись? От винта! Поехали!

## Конструктор

Приключения начинались довольно невинно. У меня появилось немало многострочных
переменных. Для их удобного задания очень хорошо подходит функция `textwrap.dedent`.
Она убирает *общие ведущие пробелы* из каждой строки текста:

    def test():
        # end first line with \ to avoid the empty line!
        s = '''\
        hello
          world
        '''
        print repr(s)          # prints '    hello\n      world\n    '
        print repr(dedent(s))  # prints 'hello\n  world\n'

Проблем две. Я часто забываю ставить обратный слеш в начале. 
И последний возврат каретки обычно тоже не нужен.

А ещё очень хочется, чтобы строки всегда были юникодом независимо от того, 
указал я это явно через `u'some string'` или нет. И временами требуется
сдвинуть весь текст на несколько пробелов вправо.


    class Template(unicode):
        def __new__(cls, pattern, **kwargs):
            strip = kwargs.get('strip', True)
            dedent = kwargs.get('dedent', strip)
            indent = kwargs.get('indent', 0)
            if dedent:
                pattern = _dedent(pattern)
            if strip:
                pattern = pattern.strip()
            if indent:
                prefix = ' ' * indent
                pattern = '\n'.join(prefix + line for line in pattern.splitlines())
            return super(Template, cls).__new__(cls, pattern)

        def __add__(self, other):
            return self.__class__(unicode(self) + other, strip=False)

        __iadd__ = __add__

Класс `Template` наследуется от `unicode` - значит все `Template` строки тоже
становятся юникодными. 

Необязательные настройки передаются как *keyword only arguments*:

* `strip` - включить обрезку основного параметра. По умолчанию установлена.
* `dedent` - включить удаление ведущих пробелов. 
    По умолчанию равна *актуальному* значению `strip`. Т.е. если пользователь
    обрезку явно выключил, то и ведущие пробелы *по умолчанию* удалять тоже не нужно.
* `indent` - количество пробелов, на которые нужно сдвинуть каждую строку
    получившегося текста вправо.

Заодно переопределим конкатенацию, чтобы возвращала объекты нашего класса. 
Зачем? Пригодится! Разумное поведение при конкатенации - не обрезать получившийся
результат.

## Аппетит приходит во время еды

В новой нотации задания шаблонов используется понятие *явного конвертера*.
Например, `"{0!r:>10}"` указывает, что для форматируемого значения нужно сначала
взять `repr`, а затем уже к результату применять выравнивание.

Необязательный *явный конвертер* задается одной буквой. По умолчанию их два:
`r` для `repr` и `s` для `str`. Остается еще так много незадействованных букв!

А у меня как раз сплошь и рядом используются несколько функций, которые вполне 
подошли бы на роль *конвертеров*. 
Например, `qname`, которая берет аргумент в кавычки тогда и только тогда, 
когда он еще не закавычен, но содержит внутри пробелы.

Или другие, форматирующие принятым в программе способом время и дату. И так далее.

Поведение стандартного форматирования можно расширить.

    class Formatter(string.Formatter):
        def convert_field(self, value, conversion):
            if 'q' == conversion:
                return qname(value)
            else:
                return super(Formatter, self).convert_field(value, conversion)

    _formatter = Formatter()

Создаём свой собственный форматировщик, умеющий обрабатывать *явное преобразование*
`q` -> `qname` в дополнение к стандартным.

Изменить стандартный системный форматировщик нельзя. Зато можно переопределить
метод `.format` для нашей строки:

    class Template(unicode):
        ...  

        def format(__self, *__args, **__kwargs):
            # use __self etc to don't clash with __kwargs keys
            return _formatter.vformat(__self, __args, __kwargs)

        def __format__(__self, *__args, **__kwargs):
            return __self.format(*__args, **__kwargs)

        def __call__(__self, *__args, **__kwargs):
            return __self.format(*__args, **__kwargs)


Присутствует небольшая хитрость: имена параметров начинаются с `__`.
Это сделано для того, чтобы можно было вызывать `.format(self='self value')`
без конфликта имён.

Заодно и переопределим `__call__`, чтобы вместо `Template('{0!q}').format('a b')`
можно было писать просто `Template('{0!q}')('a b')`. 
Результатом обоих вызовов будет `'"a b"'`.

Часто строчки с шаблонами такие длинные, а запись `.format` мешает уместится
в заветные 79 символов.

`__format__` нужен для того, чтобы заработало выражение вроде: 
`format(Template('{0!q}'), 'a b')`.

## И тут Остапа понесло

Для уточнения мелких деталей я просматривал 
[PEP 3101](http://python.org/dev/peps/pep-3101/), описывающий спецификацию 
на новомодный тип форматирования. 
И увидел там замечательную идею: форматирование с использованием *пространств имён*.

Идея очень простая. При определении значения *именованного* параметра сначала
ищем в явно заданных аргументах, 
а если не нашли - последовательно перебираем все переданные
в конструктор *форматировщика* *пространства имен* (простые словари).

    class NamespaceFormatter(Formatter):
        def __init__(self, *namespaces):
            self.namespaces = namespaces

        def get_value(self, key, args, kwargs):
            if isinstance(key, basestring):
                try:
                    return kwargs[key]
                except KeyError:
                    for namespace in self.namespaces:
                        try:
                            return namespace[key]
                        except KeyError:
                            pass
            return super(NamespaceFormatter, self).get_value(key, args, kwargs)

Разжевывать не буду, а приведу отрезок из теста:

        class A(object):
            def __init__(self, val):
                self.val = val

        ns1 = {'b': A(2)}
        ns2 = {'c': A(3)}
        fmt = NamespaceFormatter(ns1, ns2)
        ret = fmt.format("{a.val} {b.val} {c.val}", a=A(1))
        assert '1 2 3' == ret

Как видите, `b.val` берется из `ns1` а `c.val` - из `ns2`.

Хорошо, а какая польза от этих *пространств имен*?

Очень простая: в их качестве можно задавать стандартные `globals` и `locals`.

    global_name = 'global'

    def test_ns():
        local_name = 'local'
        fmt = NamespaceFormatter(locals(), globals())
        ret = fmt.format("{local_name} {global_name}")
        self.assertEqual('local global', ret)

Обратите внимание: в отличие от привычного порядка `locals` идёт первым.
Потому что имена в нём должны перекрывать имена в `globals`.

## Немного сахара

Почти хорошо. Только приходится довольно много писать. Автоматизируем поиск
*пространств имён*.

    def auto_format(spec, **spec_kwargs):
        template = Template(spec, **spec_kwargs)
        frame = sys._getframe(1)
        fmt = NamespaceFormatter(frame.f_locals, frame.f_globals)
        return fmt.format(template)

Берём *фрейм* вызвавшей функции, извлекаем оттуда заветные `globals` и `locals`.

Пример:

    def test_auto_format():
        local_name = 'local'
        self.assertEqual('local global',
                         auto_format("{local_name} {global_name}"))


И, наконец, позволим использовать короткие имена:

    T = Template
    NF = NamespaceFormatter
    a = auto_format

## Мы строили, строили, и наконец - построили!

Полный код (за исключением импортов и функции `qname`):

    class Formatter(string.Formatter):
        def convert_field(self, value, conversion):
            if 'Q' == conversion:
                if value is None:
                    return 'None'
                else:
                    return qname(value)

            if 'q' == conversion:
                return qname(value)

            return super(Formatter, self).convert_field(value, conversion)

    _formatter = Formatter()

    class Template(unicode):
        def __new__(cls, pattern, **kwargs):
            strip = kwargs.get('strip', True)
            dedent = kwargs.get('dedent', strip)
            indent = kwargs.get('indent', 0)
            if dedent:
                pattern = _dedent(pattern)
            if strip:
                pattern = pattern.strip()
            if indent:
                prefix = ' ' * indent
                pattern = '\n'.join(prefix + line for line in pattern.splitlines())
            return super(Template, cls).__new__(cls, pattern)

        def format(__self, *__args, **__kwargs):
            # use __self etc to don't clash with __kwargs keys
            return _formatter.vformat(__self, __args, __kwargs)

        def __format__(__self, *__args, **__kwargs):
            return __self.format(*__args, **__kwargs)

        def __call__(__self, *__args, **__kwargs):
            return __self.format(*__args, **__kwargs)

        def __add__(self, other):
            return self.__class__(unicode(self) + other, strip=False)

        __iadd__ = __add__

    class NamespaceFormatter(Formatter):
        def __init__(self, *namespaces):
            self.namespaces = namespaces

        def get_value(self, key, args, kwargs):
            if isinstance(key, basestring):
                try:
                    return kwargs[key]
                except KeyError:
                    for namespace in self.namespaces:
                        try:
                            return namespace[key]
                        except KeyError:
                            pass
            return super(NamespaceFormatter, self).get_value(key, args, kwargs)


    def auto_format(spec, **spec_kwargs):
        template = Template(spec, **spec_kwargs)
        frame = sys._getframe(1)
        fmt = NamespaceFormatter(frame.f_locals, frame.f_globals)
        return fmt.format(template)

    T = Template
    NF = NamespaceFormatter
    a = auto_format

Пример использования:

    def info_list(self, long, indent=4):
        changed = '*' if self.changed else ''
        ret = a("{changed}{self.name!q}")
        if long:
            ret += '\n' + a("""
                title: {self.title}
                link: {self.link}
                slug: {self.slug}
                labels: {self.labels_str}
                postid: {self.postid}
                localstamp: {self.local_stamp}
                """, indent=indent)
        return ret

Ещё один пример:

    USER_INFO = T("""\
        INFO User info:
            email: {email!Q}
            default blogid: {blogid!Q}
            Template:
                dir: {dir!Q}
                file: {file!Q}
        """)
    ret = USER_INFO(email=email, blogid=blogid, dir=dir, file=file)

## Итоги

Путём небольшого расширения стандартного механизма форматирования
удалось довольно значительно сократить необходимую для этой операции
запись и расширить возможности по обработке.

Жить стало легче, жить стало веселей!

*Всё вышесказанное тестировалось на Python 2.6, 
на "тройке" работает с одним изменением: следует везде заменить 
`unicode` и `basestring` на `str`*.
