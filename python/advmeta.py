from collections import OrderedDict


class Field:
    name = None

    def __init__(self, *, default=None):
        self.default = default

    def __get__(self, instance, owner):
        if instance is None:
            return self
        return instance.__dict__.get(self.name, self.default)

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value



class Namespace(OrderedDict):
    def __init__(self, bases):
        super().__init__()
        self.fields = OrderedDict()
        for base in reversed(bases):
            if issubclass(base, Model):
                self.fields.update(base.__fields__)
            for attrname in dir(base):
                if attrname in self.fields:
                    attr = getattr(base, attrname)
                    if not isinstance(attr, Field):
                        del self.fields[attrname]

    def __setitem__(self, key, value):
        if isinstance(value, Field):
            value.name = key
            self.fields[key] = value
        elif key in self.fields:
            del self.fields[key]
        super().__setitem__(key, value)

    def __delitem__(self, key):
        raise AttributeError("Deletion of attr `{}` is not allowed"
                             .format(key))


class Meta(type):
    registry = OrderedDict()

    @classmethod
    def __prepare__(cls, name, bases, *, register=True):
        return Namespace(bases)

    def __new__(cls, name, bases, dct, *, register=True):
        self = type.__new__(cls, name, bases, dct)
        self.__fields__ = dct.fields
        return self

    def __init__(self, name, bases, dct, *, register=True):
        super().__init__(name, bases, dct)
        if register:
            self.registry[name] = self


class Model(metaclass=Meta, register=False):
    fields = OrderedDict()


class A(Model):
    a = Field(default=1)
    b = Field(default=2)


class B(A):
    @property
    def b(self):
        return self.a + 777

class C(A):
    c = Field(default=3)

class D(B, C):
    pass

class E(B, C):
    b = Field(default=5)



assert ['a', 'b'] == list(A.__fields__)
assert ['a'] == list(B.__fields__)
assert ['a', 'b', 'c'] == list(C.__fields__)
assert ['a', 'c'] == list(D.__fields__)
assert ['a', 'c', 'b'] == list(E.__fields__)

a = A()
assert 1 == a.a, a.a
assert 2 == a.b, a.b
a.b = 333
assert 333 == a.b, a.b

b = B()
assert 778 == b.b, b.b
b.a = 333
assert 1110 == b.b, b.b

d = D()
assert 778 == d.b, d.b
d.a = 333
assert 1110 == d.b, d.b

e = E()
assert 5 == e.b, e.b
e.b = 333
assert 333 == e.b, e.b
