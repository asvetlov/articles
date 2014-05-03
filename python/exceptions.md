Title: Исключения в Питоне
Labels: python, exception, python3, file system

Поговорим об исключениях.

*Всё нижеизложенное относится к Python 3.3, хотя отчасти справедливо и
для более ранних версий.*

Для чего они применяются, наверное, все и так прекрасно знают: для
передачи сообщений об ошибках внутри программы.

Рассмотрим простейший пример: открытие файла. Если всё нормально —
`open(filename, 'r')` возвращает объект этого самого файла, с которым
можно делать всякие полезные вещи: читать из него данные и т.д.

Если файл не может быть открыт — выбрасывается исключение:

    try:
        f = open(filename, 'r')
        try:
            print(f.read())
        finally:
            f.close()
    except OSError as ex:
        print("Cannot process file", filename, ": Error is", ex)

Открываем файл и печатаем его содержимое.

Обратите внимание: файл нужно не только открыть но и закрыть после
использования. Исключение может выбросить `open` (например, если файла
нет на диске или нет прав на его чтение).

Если файл открыт — читаем его через `f.read()`. Этот вызов тоже может
выбросить исключение, но файл закрывать всё равно нужно.  Поэтому
необходим блок `finally`: `f.close()` должен быть вызван даже если
`f.read()` сломался. В этом месте удобней было бы воспользоваться
конструкцией `with` но мы же сейчас говорим об исключениях а не о
контекстных менеджерах, верно?

Исключения из обоих мест попадут в `except OSError`, где можно будет
что-то сделать с ошибкой.

*Питон делает явный выбор в пользу исключений перед возвратом кода
 ошибки в своём ядре и стандартной библиотеке. Прикладному
 программисту стоит придерживаться этих же правил.*

Введение закончено.  Теперь сконцентрируемся  на том что  происходит в
`except`.

## Типы исключений ##

Все исключения составляют иерархию с простым наследованием. Вот
простой небольшой кусочек от довольно обширного набора исключений ядра
Питона:

    BaseException
     +-- SystemExit
     +-- KeyboardInterrupt
     +-- GeneratorExit
     +-- Exception
          +-- StopIteration
          +-- AssertionError
          +-- AttributeError
          +-- BufferError

Самый базовый класс — `BaseException`. Он и его простые потомки
(`SystemExit`, `KeyboardInterrupt`, `GeneratorExit`) не предназначены
для перехвата обыкновенным программистом — только Питон и редкие
библиотеки должны работать с этими типами. Нарушение правила ведет,
например, к тому что программу невозможно корректно завершить — что
совсем не хорошо.

Также не нужно перехватывать все исключения:

    try:
        ...
    except:
        ...

работает как

    try:
        ...
    except BaseException:
        ...

Всё, что может быть нужно программисту — это `Exception` и
унаследованные от него классы.

Вообще-то лучше ловить как можно более конкретные классы исключений.
Например, в случае с файлом это `OSError` или даже может быть
`FileNotFoundError`. Таким образом мы не перехватим `AttributeError`
или `ValueError`, которые в этом примере означали бы ошибку или
опечатку программиста.

Кстати, обратите внимание: `StopIteration` порожден от `Exception` а
`GeneratorExit` от `BaseException`. Подробности, почему сделано именно
так, можно найти в [PEP 342](http://www.python.org/dev/peps/pep-0342/).

## Цепочки исключений ##

Прочитав предыдущую главку все прониклись необходимостью указывать
правильный класс исключений и пообещали никогда не использовать
`BaseException`.

Идем дальше. Следующий пример:

    try:
        user = get_user_from_db(login)
    except DBError as ex:
        raise UserNotFoundError(login) from ex

Получаем пользователя из базы данных чтобы что-то потом с ним
сделать. `get_user_from_db` может выбросить ошибку базы данных. Для
нас это скорее всего означает что такого пользователя нет. Но для
логики приложения полезней наш собственный тип `UserNotFoundError` с
указанием логина проблемного пользователя, а не обезличенная ошибка БД
— что мы и выбрасываем в обработчике исключения.

Проблема в том, что программисту часто хотелось бы знать, а почему это
пользователь не найден. Например, чтобы сохранить в логах для
дальнейшего разбирательства.

Для таких целей служит конструкция `raise ... from ...`.

По [PEP 3134](http://www.python.org/dev/peps/pep-3134/) у объекта
исключения имеется несколько обязательных атрибутов.

В первую очередь это `__traceback__`, содержащий кусочек стека от
места возникновения исключения до места его обработки.

Затем — `__context__`. Если исключение было создано в ходе обработки
другого исключения (выброшено из `except` блока) — `__context__`
будет содержать то самое породившее исключение. Которое, в свою
очередь тоже может иметь установленный `__context__`. Этот атрибут
равен `None` если наше исключение — самое первое и не имеет
предшественников.

`__context__` устанавливается автоматически.

В отличие от контекста `__cause__` устанавливается только если
исключение было выброшено конструкцией `raise ... from ...` и равно
значению `from`.

Если исключение выбрасывалось простым `raise ...` то `__cause__` будет
равно `None` в то время как `__context__` всегда будет содержать
породившее исключение если оно существует.

Для вывода исключения со всей информацией служит набор функций из
модуля `traceback`, например `traceback.print_exc()`.

И тут тоже есть проблема: печатается либо явная цепочка если есть
установленный `__cause__` или неявная, тогда используется
`__context__`.

Иногда программисту может быть нужно отбросить породившие исключения
как не имеющие смысла при выводе `traceback`. Для этого появилась форма записи

    raise exc from None

[PEP 409](http://www.python.org/dev/peps/pep-0409/) и [PEP
415](http://www.python.org/dev/peps/pep-0415/) рассказывают как это
работает:

У исключения всегда есть атрибут `__supress_context__`. По умолчанию
он равен `False`.

Конструкция `raise ... from ...` записывает `from`
в `__cause__` и устанавливает `__supress_context__` в `True`.

Тогда семейство функций `traceback.print_exc()` печатают цепочку если
явно указан (не равен `None`) `__cause__` или есть `__context__` и при
этом `__supress_context__` равен `False`.

Изложение получилось несколько длинным, но сократить текст без потери
смысла у меня не вышло.

## Семейство OSError ##

Последняя проблема о которой хотелось бы рассказать — это типы
исключений порожденные вызовами операционной системы.

До Python 3.3 существовало много разных типов таких исключений:
`os.error`, `socket.error`, `IOError`, `WindowsError`, `select.error`
и т.д.

Это приводило к тому, что приходилось указывать несколько типов
обрабатываемых исключений одновременно:

    try:
        do_something()
    except (os.error, IOError) as ex:
        pass

Ситуация на самом деле была еще хуже: очень легко забыть указать еще
одно нужное исключение, которое может внезапно прилететь. Дело в том
что исключения операционной системы часто никак не проявляют себя при
разработке. На машине программиста всё работает отлично и он не
подозревает о возможных проблемах. Как только программа выходит в
production пользователь вдруг ловит что-то неожиданное и программа
аварийно завершается. Все опечалены.

Проблема решена в [PEP 3151](http://www.python.org/dev/peps/pep-3151/):
весь этот зоопарк теперь
является псевдонимами для OSError. Т.е. пишите `OSError` и не
ошибетесь (прочие имена оставлены для обратной совместимости и
облегчения портирования кода на новую версию).

Давайте рассмотрим ещё один аспект исключений, порожденных
операционной системой.

У `OSError` есть атрибут `errno`, который содержит код ошибки (список
всех возможных символьных констант для ошибок можно посмотреть в модуле
`errno`).

Открываем файл, получаем `OSError` в ответ. Раньше мы должны были
анализировать `ex.errno` чтобы понять, отчего произошла ошибка: может
файла нет на диске, а может нет прав на запись — это разные коды
ошибок (`ENOENT` если файла нет и `EACCES` или `EPERM` если нет прав).

Приходилось строить конструкцию вроде следующей:

    try:
        f = open(filename)
    except OSError as ex:
        if ex.errno == errno.ENOENT:
           handle_file_not_found(filename)
        elif ex.errno in (errno.EACCES, errno.EPERM):
           handle_no_perm(filename)
        else:
           raise  # обязательно выбрасывать не обработанные коды ошибки

Теперь иерархия расширилась. Привожу полный список наследников `OSError`:

    OSError
     +-- BlockingIOError
     +-- ChildProcessError
     +-- ConnectionError
     |    +-- BrokenPipeError
     |    +-- ConnectionAbortedError
     |    +-- ConnectionRefusedError
     |    +-- ConnectionResetError
     +-- FileExistsError
     +-- FileNotFoundError
     +-- InterruptedError
     +-- IsADirectoryError
     +-- NotADirectoryError
     +-- PermissionError
     +-- ProcessLookupError
     +-- TimeoutError

Наш пример можем переписать как:

    try:
        f = open(filename)
    except FileNotFound as ex:
        handle_file_not_found(filename)
    except PermissionError as ex:
        handle_no_perm(filename)

Гораздо проще и понятней, правда? И меньше мест, где программист может
ошибиться.

## Заключение ##

Переходите на Python 3.3, если можете. Он хороший и облегчает жизнь.

Новые плюшки в вопросе, касающемся исключений, я показал.

Если использовать новый питон не позволяют обстоятельства — пишите на
чём есть, но помните как правильно это делать.