Unicode str, default is UTF-8

Function Annotations:

    def f(a: int, b: float) -> str:
        return "{}:{}".format(a, b)

Nonlocal:

    def f():
        a = 0
        def g():
            nonlocal a
            a += 1
        g()
        g()
        return a

Keyword only:

    def f(a, b=0, *, c, d='Smith'):
        pass

    f(1, c='Jonn', d='Doe')

Extended iterable unpacking:

    a, *rest, b = range(5)

Comprehensions:

    {key(k): value(k) for k in range(5)}

    {f(k) for k in range(5)}

    {1, 2, 3, 4, 5}

ABC and new `super()`:

    import abc

    class Base(metaclass=abc.ABCMeta):

        @abc.abstractmethod
        def f(self, a):
            """Comprehensive doc"""
            pass

    class A(Base):

        def f(self, a):
            super().f(a)
            pass


Exception chain:

    def f():
        try:
            1 / 0
        except Exception as ex:
            raise RuntimeError("Division by zero") from ex

    f()

----

    Traceback (most recent call last):
      File "<string>", line 3, in f
        1/0
    ZeroDivisionError: division by zero

    The above exception was the direct cause of the following exception:

    Traceback (most recent call last):
      File "<string>", line 7, in <module>
        f()
      File "<string>", line 5, in f
        raise RuntimeError("Division by zero") from ex
    RuntimeError: Division by zero


Unified int

Decimal

Packaging

importlib

yield from
