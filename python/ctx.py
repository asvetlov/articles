import contextlib
import functools

def context(gen, *ctxargs, **ctxkwargs):
    def gen(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            with gen(self, *ctxargs, **ctxkwargs):
                return func(self,* args, **kwargs)
        return wrapper
    return gen


class A:
    def __init__(self):
        print('init')

    @contextlib.contextmanager
    def l(self, arg):
        print('pre', arg)
        yield
        print('post', arg)

    def a(self):
        print('a.1')
        with self.l('arg1'):
            print('a.2')
        print('a.3')

    @context(l, 'arg2')
    def b(self):
        print('b')

if __name__ == '__main__':
    a = A()
    a.a()
    #import pdb;pdb.set_trace()
    a.b()
