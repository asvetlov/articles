Title: Переполнение стека
Labels: python, stack overflow

На первый взгляд у Питона очень простая и прозрачная работа со стеком.
Каждый новый вложенный вызов функции (на самом деле исполнение *code
block*, но кому нужны эти детали) увеличивает внутренний счетчик,
каждый выход — уменьшает. Если счетчик доходит до 1000 (значение по
умолчанию) — выбрасывается `RuntimeError` с текстом *«maximin
recursion depth exceeded»*.

Допустимая глубина регулируется
`sys.getrecursionlimit` / `sys.setrecursionlimit`.


Очень простая и понятная схема, в которой тем не менее есть серьезная проблема.
Рассмотрим такой код:

    with zipfile.ZipFile('filename.zip', 'w') as f:
        f.writestr('file.txt', get_text_data())

Допустим, вызов `get_text_data` выбросил исключение. Тогда
`ZipFile.__exit__` должен закрыть архив, записав все нужные
структуры. Это — довольно большой кусок кода с многочисленными
вложенными вызовами.

А мы и так уже находимся у самого края, стек почти весь вышел. Скорее
всего в таком случае `ZipFile.__exit__` (который в свою очередь
вызывает `ZipFile.close` и т.д.) вместо нормального закрытия файла сам
вывалится с `RuntimeError` *«maximin recursion depth»*. Обработчик
ошибок сломался, породив новое исключение.

То же самое может произойти при использовании `try/finally` или
`try/except`.  В результате существующее поведение выглядит очень
странным. На самом деле нет безопасного способа делать что-либо при
переполнении стека — любое неловкое движение приведет к новому
переполнению. То, как поступает Питон (выбрасывание исключения)
абсолютно бесполезно и может только запутывать логику обработки
ошибок. Проще, наглядней и надежней было бы просто завершать
интерпретатор в аварийном режиме.

В python 3 ситауцию кардинально исправили. В случае переполнения стека
все так же выбрасывается RuntimeError. Но питон гарантирует
обработчикам (всему коду, который будет выполнен до выхода из *frame*,
поймавшего исключение) запас в 50 уровней стека — а это более чем
достаточно.

Глубина «добавочного стека» не регулируется. Это —
принципиально. Важно дать всем третьесторонним библиотекам возможность
нормально завершить свои дела. И при этом не важно, какие настройки
стека выставила использующая их программа.

Если обработчики не вложились в добавочные 50 вызовов — Питон аварийно
закрывается.

Новая схема не убирает все проблемы рекурсивного вызова, но достаточно
хороша для подавляющего большинства случаев.

Таким образом, теперь можно смело писать достаточно сложный код,
который будет работать даже если стек исчерпан.