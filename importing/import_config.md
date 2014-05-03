Title: Импорт конфигурационных файлов
Labels: python, import, config

Конфигурацию можно хранить в различном виде: `xml`, `yaml`, `ini` и так далее.

Один из способов - записывать ее в виде обычного питоновского файла,
при исполнении которого должен получиться объект со свойствами-параметрами.

Этот вариант имеет как достоинства, так и недостатки. Сейчас речь не о том.
Рассмотрим, как именно подгружается конфигурация на примере
[Flask](https://github.com/mitsuhiko/flask/blob/master/flask/config.py#L123).

    import imp

    d = imp.new_module('config')
    d.__file__ = filename
    try:
        execfile(filename, d.__dict__)
    except IOError, e:
        if silent and e.errno in (errno.ENOENT, errno.EISDIR):
            return False
        e.strerror = 'Unable to load configuration file (%s)' % e.strerror
        raise

Создается объект модуля с именем `'config'`, в нем прописывается путь
к файлу конфигурации `__file__` (каждый модуль лежащий в файловой системе
должен иметь этот атрибут - помогает при поиске неисправностей).

Затем следует вызов `execfile` в контексте модуля конфигурации. Между прочим,
`execfile` можно заменить на более длинную конструкцию:

    with open(filename) as f:
        source = f.read()
        code = compile(source, filename, 'exec')
        exec code in d.__dict__

Как видим, тоже ничего слишком сложного: читаем содержимое файла конфигурации,
компилируем его в режиме `'exec'` и запускаем на словаре нашего модуля.

Почти так же работает обычный импорт модуля.

Так почему же нельзя сделать

    d = imp.load_source('mod_name', filename)

сократив весь код до одной строки?

Дело в первую очередь в том, что конфигурация - это не модуль в полном смысле
этого слова. Хотя технически создается полноценный объект типа *"модуль"*
с именем `'config'`, этот модуль не регистрируется в общем словаре модулей
`sys.modules`.

Соответственно его нельзя получить написав import config

И, значит, конфигурация не будет путаться под ногами, закрывая собой
(возможно) честный модуль с таким же именем, лежащий в *python import path*.

Более того, конфигурация имеет смысл только для этого самого фреймворка Flask,
остальной код ее просто-напросто не должен видеть - что мы и получили.

Если хотите, модуль конфигурации - анонимный
(по аналогии с анонимными функциями).

Вызов же `load_source` работает немного иначе. Объект модуля будет создан
как:

    d = sys.modules.setdefault(mod_name, imp.new_module(mod_name))

Т.е. будет взят модуль с именем `mod_name` из `sys.modules`,
если не существует - будет создан новый модуль и опять же зарегистрирован
в общем каталоге. Обратите внимание, `load_source` работает еще и как
`reload`, если модуль с этим именем уже был загружен.

Таким образом, небольшая на первый взгляд разница в поведении может
привести к нежелательным *побочным эффектам*.

Flask написан очень грамотно, Armin Ronacher на такие грабли не наступает.
Чего и вам желаю.
