Title: Расширенное использование контекстных менеджеров
Labels: python, context manager

Контекстным менеджером называется класс, у которого есть методы
`__enter__` и `__exit__`. Подробности применения — в документации
(ссылка).

В качестве примера возьмем пример с блокираторами.

    class Lock:
        def __init__(self, locker):
            self.locker = locker

        def __enter__(self):
            self.locker.acquire()

        def __exit__(self, ecx_type, exc_val, exc_tb):
            self.locker.release()

    class A:
        def __init__(self):
            self.locker = ....

        def lock(self):
            return Lock(self.locker)

        def f(self):
            with self.lock():
                pass  # do something


Как видим, для создания нового контекстного менеджера нужно написать
отдельный класс.  Модуль `contextlib` позволяет использовать
упрощенный способ (ссылка). Второй вариант выглядит значительно короче:

    import contextlib

    class A:

        @contextlib.contextmanager
        def lock(self):
            self.locker.acquire()
            yield
            self.locker.release()



Это было краткое введение в предметную область.
