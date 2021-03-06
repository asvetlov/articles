Питон: импорт и модули - часть 2.
=================================

Первая часть - [здесь](http://asvetlov.blogspot.com/2010/05/blog-post.html).

Откуда грузятся модули?

Простой ответ - из `sys.path` - будет лишь отчасти верным.

Полный список должен содержать:

* `__import__`
* `sys.modules`
* `sys.path`
* `.pth` файлы
* `sys.meta_path`
* `sys.path_hooks`
* `sys.path_import_cache`

Давайте рассмотрим все по порядку.

`__import__`
------------

Любая форма импорта, а их с точки зрения CPython три:

    import a.b
    from a.b import c
    from a.b import *

сводится к вызову функции `__import__(name:str, globals:dict={}, locals:dict={}, form_list:list=[], level:int=-1) -> types.ModuleType`

* `name` - имя модуля. С точками внутри, если нужно.
* `globals` - глобальное пространство имен блока, который загружает модуль.
О пространствах имен я здесь рассказывать не буду - тема для отдельной большой статьи.
Упомяну лишь, что его можно получить через вызов `globals()`
* `locals` - локальное пространство имен, `locals()`. При импорте не используется.
* `from_list` - список имен, которые нужно получить из импортируемого модуля.
* `level` - уровень вложенности. Используется для относительного импорта.

Честно говоря, эта функция весьма запутана и ее использование довольно нетривиально.
По ней можно отследить развитие механизма импорта в Питоне - модули, имена из модулей,
относительный импорт.
При разном наборе параметров она дает различный результат. Не люблю.

Описывать подробно все не хочу - читайте
[стандартную документацию](http://docs.python.org/py3k/library/functions.html#__import__).

Замечу, немного забегая вперед - начиная с Python 3.1 появился замечательный
пакет importlib, в котором есть удобная `importlib.import_module`.

`__import__` реализован в `Python/import.c` - довольно большой файл.

Что он делает?

* блокировки потоков.
* работа с модулями
* поддержка пакетов
* импорт модулей, написанных на Питоне
* поддержка C Extensions
* работа с кешем питоновских модулей (`.pyc` файлы)
* встроенные (`builtins`) и замороженные (`frozen`) модули.
Последние могут быть интересны для разработчиков систем, в которые Питон
вшит внутрь (python embedding)
* расширения (import hooks)
* платформозависимый код - на linux все выглядит немного иначе, чем на Windows.
А в import.c еще есть код, специфичный для MacOS и OS/2.

Следует упомянуть еще один стандартный модуль - `imp`.
Он содержит набор низкоуровневых функций, необходимых для работы импорта.
Я не буду давать его полное описание - но в дальнейшем упомяну ряд интересных функций.

_При изучении внутренней реализации следует всегда помнить, что импорт развивался
долго и трудно. Нововведения обязаны были поддерживать обратную совместимость
с уже имеющимся кодом. Текущая картина представляет результат этого компромисса._

_При этом часть заложенных возможностей все еще не реализована - особенно
это касается расширений, которые хоть и стали стандартным механизмом начиная
с Python 2.3, все еще выглядят как сторонняя надстройка.
Когда-нибудь весь импорт будет построен на расширениях (Python 3.3?)_

_Как бы то ни было, в изложении я буду описывать текущее состояние дел,
показывая где нужно "идеальную картинку", к которой все рано или поздно придет._

_Я буду в основном говорить о модулях, написанных на Питоне `.py` файлах,
если отдельно не будет упомянуто.
C Extensions - отдельная очень интересная тема,
о которой можно писать очень долго._

_Преамбула закончена. Приступим к детальному рассмотрению._

Блокировка
----------

Импорт модуля изменяет глобальные переменные (в первую очередь `sys.modules`.
Чтобы избежать возможные накладки, получающиеся при параллельной загрузке модулей
из разных потоков, используется блокировка.

В модуле `imp` для этого существуют три функции:

* `imp.acquire_lock()` - взять блокировку
* `imp.release_lock()` - отдать ее
* `imp.lock_held()` - проверить, взята ли?

Это выглядит так: первым делом `__import__` берет блокировку, затем загружает модуль.

Модулей может быть несколько: помните - `import a.b.c` превращается в

    import a
    import a.b
    import a.b.c

Т.е. при загрузке модуля из пакета сначала загружаются модули верхних уровней.
При этом каждый модуль может содержать другие импорты, которые будут выполнены.

Строго говоря, этот процесс выглядит так:

* создать модуль
* создать код для этого модуля (преобразовать питоновский текст в байт-код)
* выполнить этот байт-код в глобальном пространстве имен модуля.
Подробности - в следующих статьях этой серии.

После загрузки модуля блокировка снимается.

Мне никогда не приходилось работать с функциями блокировки напрямую.
Импорт сам делает все, что нужно, но знать о блокировках необходимо.

Обычно модули импортируются как `first level statemets` в начале вашего
файла.

Но инструкцию импорта можно писать и внутри функции.

    def f():
        from twisted.internet import reacor
        reactor.callLater(0, lambda: None)

Это делается для отложенной
загрузки. Например, для того чтобы разорвать циклическую зависимость модулей.
Или, как в случае с twisted, работать с реактором только после того, как был
выбран его тип (select, poll, epoll и т.д.)

И все выглядит прекрасно, если ваши функции с import statement внутри работают в
одном потоке - лучше всего в главном.

В случае многопоточной программы, интенсивно использующей свои блокировки,
можно все подвесить - так называемый _dead lock_.
Я встречал такую ситуацию в моей практике пару раз.
Мультипоточность не является темой данной серии статей.
Если вы пишите такую программу, то должны знать о взаимных блокировках.
Пожалуйста, учитывайте при разработке еще и блокировку импорта.

_Памятка: импорт уже загруженного модуля быстрый.
Но не мгновенный - Питон возьмет блокировку проделает несколько операций,
прежде чем вернуть уже загруженный модуль._



`sys.module`s{str: types.ModuleType}
------------

Словарь уже загруженных в Питон модулей.

Давайте глянем на него подробней.

    >>> import pprint, sys
    >>> pprint.pprint(sys.modules)
    {
    ...
     'StringIO': <module 'StringIO' from '/usr/lib/python2.6/StringIO.pyc'>,
     'UserDict': <module 'UserDict' from '/usr/lib/python2.6/UserDict.pyc'>,
     '_ctypes': <module '_ctypes' from '/usr/lib/python2.6/lib-dynload/_ctypes.so'>,
     '__builtin__': <module '__builtin__' (built-in)>,
     '__main__': <module '__main__' from '/usr/bin/bpython'>,
     'ctypes': <module 'ctypes' from '/usr/lib/python2.6/ctypes/__init__.pyc'>,
     'ctypes._endian': <module 'ctypes._endian' from '/usr/lib/python2.6/ctypes/_endian.pyc'>,
     'encodings': <module 'encodings' from '/usr/lib/python2.6/encodings/__init__.pyc'>,
     'encodings.aliases': <module 'encodings.aliases' from '/usr/lib/python2.6/encodings/aliases.pyc'>,
     'encodings.utf_8': <module 'encodings.utf_8' from '/usr/lib/python2.6/encodings/utf_8.pyc'>,
     'sys': <module 'sys' (built-in)>,
     'zipimport': <module 'zipimport' (built-in)>,
    ...
    }

Конечно, я пожалел читателя и нещадно порезал ту бесконечность,
которую питон должен загрузить перед началом своей работы.

Итак, что мы видим.

* builtins - встроенные модули, у которых отсутствует имя файла:
    * `__builtin__`
    * обязательный `__main__` (это ваш файл, с которым вы запустили python)
    * `sys` - много вкусного
    * `zipimport` - для загрузки модулей, хранящихся в zip архивах
* C Extensions - расширения, написанные на языке С и не только
    * `_ctypes`, указывающий на `_ctypes.so`
* модули верхнего уровня `StringIO` и `UserDict`
* пакеты `ctypes` и `encodings` с вложенными модулями


_Импорт складывает загруженные модули в `sys.modules`._

_Еще раз подчеркну: если модуль уже там лежит - он быстро возвращается (но блокировка все равно берется)._


Импорт: абсолютный, относительный и непонятный
---------------------------------------------

Технически есть два вида: абсолютный и относительный.

* При абсолютном следует указывать имя модуля начиная с самого верха:
`import a.b.c`
* Потом появился относительный (2.5+):

    from . import c

Наверное, уже все успели с ним познакомится.
На самом деле очень удобно: точка означает папку, в которой лежит
импортирующий модуль. Две точки подряд - прыжок на уровень выше.

Именно для этого появился последний параметр `level` в `__import__`:
он показывает, на сколько уровней вверх нужно заглянуть, чтобы загрузить `name`.

К сожалению, и тут не все гладко. В старых (до 2.5) питонах относительный импортов
не было. Поэтому при `import os` питон сначала пытался загрузить `os.py` в той папке,
где находился вызывающий модуль.
Если файла не нашлось (а чаще всего так и бывает),
то питон будет искать модуль по абсолютному пути.
А чтобы не обращаться к файловой системе опять (время дорого) - в `sys.modules`
вставится заглушка:

    >>> pprint.pprint(sys.modules)
    {
     ...
     'encodings': <module 'encodings' from '/usr/lib/python2.6/encodings/__init__.pyc'>,
     'encodings.__builtin__': None,
     'encodings.aliases': <module 'encodings.aliases' from '/usr/lib/python2.6/encodings/aliases.pyc'>,
     'encodings.codecs': None,
     'encodings.utf_8': <module 'encodings.utf_8' from '/usr/lib/python2.6/encodings/utf_8.pyc'>,
     ...
    }

Обратите внимание: `encodings.__builtin__` и `encodings.codecs` указывают на `None`.
Это значит, что питон будет при следующей попытке искать `__builtin__` и `codecs`
по абсолютному пути.

Добавлю, что начиная с 2.7+ "компромиссный" способ невозможен. Пишите либо полный путь,
либо указывайте его явно с точки. И это замечательно!

sys.path:[str]
--------------

Начиная разговор о том, где Питон находит новые модули, невозможно пропустить
`sys.path`. Все с него начинается и часто им же и заканчивается.

`sys.path` представляет собой список файловых путей, в которых лежат модули.

    >>> import sys
    >>> import pprint
    >>> pprint.pprint(sys.path)
    [
     '.',
     '/usr/local/lib/python2.6/dist-packages/distribute-0.6.10-py2.6.egg',
     '/home/andrew/projects/reaction',
     '/usr/local/lib/python2.6/dist-packages/rpyc-3.0.7-py2.6.egg',
     '/usr/lib/python2.6',
     '/usr/lib/python2.6/plat-linux2',
     '/usr/lib/python2.6/lib-tk',
     '/usr/lib/python2.6/lib-old',
     '/usr/lib/python2.6/lib-dynload',
     '/usr/lib/python2.6/dist-packages',
     '/usr/lib/python2.6/dist-packages/PIL',
     '/usr/local/lib/python2.6/dist-packages',
     ...
    ]

Как видим, сюда попадает прежде всего сам питон, установленные библиотеки и
мои собственные проекты.

Поиск модуля ведется с начала списка, и не случайно первой стоит точка (текущая
папка). _Модуль из текущей папки загрузится первым, перекрыв остальные_.

Поэтому не пытайтесь создавать свои модули с именами `pickle` или `urllib` -
они перекроют стандартные и вы получите странную ошибку при импорте.

`sys.path` можно изменять из питоновского кода, чтобы подключить ваши модули и
пакеты.

_Крайне не советую это делать - лучше писать `distutils` скрипт `setup.py`,
который установит вашу чудесную библиотеку в питон._

_Конечно, меня сразу же поправят - делать `distutils` неудобно.
Согласен, используйте `distribute`, `setuptools`, `paver`, `enstaller` -
что вам больше по душе._

_По этому поводу написано немало статей, а мы все же рассматриваем сейчас немного
другой вопрос. Последние два года Тарик Зиаде интенсивно занимается переписыванием
`distutils` с целью учесть все недостатки и создать по настоящему замечательную
штуку. Удачи ему._


Как бы то ни было, нужно понимать способ, которым наполняется `sys.path`.

В первую очередь питон добавляет текущую папку и стандартную библиотеку (папка Lib, если смотреть на питоновские исходники).

Затем следует импорт `site.py`.

`site.py`
---------

Предназначен для настройки Питона. Большая часть файла занимается добавлением
путей в `sys.path`. Не поленитесь, откройте его в текстовом редакторе и рассмотрите.
Это не больно.

Чтобы узнать, где он лежит - сделайте

    >>> import site
    >>> site.__file__
    '/usr/lib/python3.1/site.py'


На первый взгляд содержимое представляет дикую мешанину
из различных способов расширения. На второй взгляд - тоже. Что поделать - цена
обратной совместимости и отражение развития представлений об импорте.

При этом поставщики различных дистрибутивов могут немного подкручивать его содержимое.
Особенно этим славятся Debian и Ubuntu. Использую - но плАчу, как тот ёжик.

Позвольте мне остановится на "минимальном стандартном наборе", а все многочисленные
тонкости изучайте сами.

Итак, это в первую очередь `site-packages` - обычно папка внутри
стандартной библиотеки питона. Сюда устанавливаются сторонние библиотеки, которые
не поставляются вместе с питоном.

Начиная с Python 2.6 поддерживаются еще и локальные пользовательские папки:
`~/.local/lib/python2.6/site-packages` или `%APPDATA%/Python/Python26/site-packages`
для Windows.

Для детального изучения читайте
[PEP 370: Per-user site-packages Directory](http://www.python.org/dev/peps/pep-0370/)
и внимательно изучайте ваш `site.py`.
Дело в том, что для новых версий схема может быть иной -
`~/.local/lib/python.3.1/site-packages`. Различия, впрочем, невелики.

Более интересны так называемые `.pth` файлы,
которые могут содержаться в `site-packages`.

Дело в том, что сторонние пакеты могут иметь разную структуру.

Например,

* `dpkt-1.6`
    * `AUTHORS`
    * `CHANGES`
    * `README`
    * `dpkt`
        * `__init__.py`
        * `dpkt.py`
        * `dhcp.py`
    * `examples`
        * `example-1.py`
    * `tests`
        * `test-perf.py`
    * `setup.py`

Для `import dpkt` нужна папка dpkt-1.6, в которой уже есть
пакет `dpkt` с `__init__.py` внутри.
Поддерживать два дерева каталогов "для разработки" и "для питона" неудобно.

Поэтому можно положить в `site-packages` файл `dpkt.pth`, содержащий путь к папке,
внутри которой будет питоновский пакет `dpkt`.

`site.py` пройдется по всем `.pth` файлам и обработает их.

Обработка в данном случае заключается в следующем:

* все строки, начинающиеся с `#` - комментарии
* строка, начинающаяся с `import` должна быть исполнена.
После точки с запятой, отделяющих новую команду - можно писать любой код.
Грязный хак, облегчающий жизнь в некоторых ситуациях
* все прочие строки добавляются в `sys.path`

Обратите внимание - путь может указывать куда угодно, в том числе и на вашу папку,
в которой вы держите рабочие проекты.

_Подчеркну, еще раз, что создавать самому `.pth` файлы - моветон._

_Делайте правильные `setup.py`, используйте `distribute`,
регистрируйте разрабатываемые вами библиотеки через `python setup.py develop`.
Еще лучше применяйте при этом `virtualenv`._

_Я рассказал о `.pth` файлах только в рамках общего обзора импорта модулей._

Последним шагом `site.py` делает `import sitecustomize`.
`sitecustomize.py` обычно кладут в ту же папку, где расположен запускаемый
питоновский скрипт. Это позволяет настроить интерпретатор перед запуском кода этого
скрипта (подкрутить тот же `sys.path` к примеру).

_Никогда так не делайте. При правильной организации проекта такой трюк не нужен.
Зато я видел много проблем у тех, кто пытался использовать `sitecustomize`.
Не хочу подробно на них останавливаться - и так много негативных посылов в этой части.
Будут просьбы - расскажу все очень подробно на предметном материале._

Импорт и главный модуль.
------------------------

Не могу обойти вниманием `__main__.py`.
Так называется модуль, который вы непосредственно запускаете через
`python <script.py>`.

Также в конце этого модуля считается правилом хорошего тона писать

    if __name__ == '__main__'
        main()

чтобы вызвать функцию `main` только тогда, когда файл используется как скрипт.

На самом деле, конечно, можете писать и вызывать что угодно.

Смысл этого блока в том, чтобы делать вызов `main()` только тогда, когда мы
запускаем скрипт непосредственно (из командной строки, кликая по нему мышкой и т.д.)

Обычно это ведет к разбору аргументов командной строки и отработке программы
(выводу на консоль, созданию окошек GUI и прочее).

Если этот модуль был загружен из другого скрипта, то все эти побочные действия ни
к чему - нужно получить сам модуль и работать с его объектами (функциями,
переменными, классами).
В этом случае имя модуля будет другим (`__main__` указывает
на вызывающий скрипт).

Есть несколько способов запустить скрипт:

* указать его явно в командной строке. Тривиально.
* написать `python -m unittest .` (2.4+) - в данном случае запустить юниттесты
для нашей папки, в которой лежат тестовые сценарии.

Последний механизм подправляли в 2.5 и 2.6:

* [PEP 338: Executing modules as scripts](http://www.python.org/dev/peps/pep-0338/)
* [PEP 366: Main module explicit relative imports](http://www.python.org/dev/peps/pep-0366/)

Наиболее интересен последний PEP.
Дело в том, что 2.5 стал поддерживать относительные пути импорта
(которые начинаются с точки). Но `__main__` - модуль верхнего уровня.
"Выше" быть ничего не может а "рядом" лежат модули из стандартной библиотеки.

Поэтому в 2.6 ввели атрибут модуля `__package__`:

    if __name__ == "__main__" and __package__ is None:
        __package__ = "expected.package.name"

Теперь можно указать свой пакет, если модуль выполняется как скрипт.

Последняя малоизвестная часть относится к импорту из zip архивов
[PEP 273: Import Modules from Zip Archives](http://www.python.org/dev/peps/pep-0273/)

Если вы положите файл с именем `__main__.py` в такой архив, то можно запустить его
через `python <achive.zip>`.

Я еще раз призываю строить разработку основываясь на _библиотеках, пакетах и модулях_,
а не на _файлах, папках и архивах_. Разница довольно тонкая, но очень существенная.

Тем не менее могут быть случаи, системному администратору удобно использовать именно этот подход:

* его "скриптик" вырос и не помещается в один `.py` файл.
* тем не менее он еще не дорос до "большой библиотеки"
со всем полагающимся оформлением.

Заключение
----------

За рамками статьи остается
[PEP 382: Namespace Packages](http://www.python.org/dev/peps/pep-0382/)
и много интересных особенностей, относящихся к `sys.path`.

К сожалению эта тема настолько обширна и запутана,
что я просто не в силах рассказать обо всем сразу.

Следующая статья из серии будет посвящена беглому обзору того, как Питон обрабатывает
расширения импорта (знаменитый PEP 302).

И только потом я смогу перейти (наконец-то!!!) к собственно разговору о том, как
писать import hooks и зачем они могут быть нужны "простому программисту".

Продолжение - в [следующей части](http://asvetlov.blogspot.com/2010/05/3.html).
