1. Attribute checks
   Call method X if it exists, call method Y otherwise (e.g. the
iterator protocol, which falls back to the sequence iterator if
__iter__ doesn't exist, but __getitem__ does, and the backwards
compatibility in the path entry finder protocol, which tries
find_loader first, then falls back to find_module)

2. Setting attributes to None
  Call method X if it is not None (e.g. the hash protocol, where we
added support for __hash__ = None to cope with the fact that object
instances are hashable, but instances of subclasses that override
__eq__ without also overriding __hash__ are not)

3. Implementing the method, but returning NotImplemented
  Call method if defined, treat a result of NotImplemented as if the
method did not exist at all. (e.g. the binary operator protocols)

4. Throwing a particular exception (typically NotImplementedError)
  Call method if defined, treat the designated exception as if the
method does not exist at all (e.g. optional methods in the IO stack)

To avoid people having to dig up the alternatives (all of which are
used in the core or standard library in various situations):
- the method/attribute may be missing entirely
- the method/attribute is always present, but may be None
- the method is always present, but returns NotImplemented by default
- the method is always present, but raises NotImplementedError by default



Duck Typing
=============

class A:
  def f(self):
    print('A.f')

class B:
  def f(self):
    print('B.f')

a = A(); b = B();
a.f()
b.f()

class Base:
  def f(self):
    return 1

class A(Base):
  def f(self):
    return 2


from collections import Set

class S(Set):
  def __init__(self, s):
    self.s = s

  def __contains__(self, i):
    return i in self.s

  def __iter__(self):
    return iter(self.s)

  def __len__(self):
    return len(self.s)

s1 = S({1, 2})
s2 = S({2, 3})
s3 = s1|s2


class A:
  def do(self):
    if hasattr(self, 'pre'):
      self.pre()
    pass  # do something

class B(A):
  def pre(self):
     pass  # do pre method

class A:
  def pre(self):
    raise NotImplementedError('implement pre method')

  def do(self):
    try:
      self.pre()
    except NotImplementedError:
      pass
    print('A.do')

class B(A):
  def pre(self):
     print('B.pre')


class A:
  def override(self):
    return NotImplemented

  def do(self):
    val = self.override()
    if val is not NotImplemented:
      return val
    else:
      return 'default'

class B:
  def override(self):
    return 'overriden'
