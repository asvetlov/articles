
# -*- coding: utf-8 -*-

import datetime
import imp
import os
import re
import sys

from collections import defaultdict

def install(path):
    sys.meta_path.append(Finder(path))

def for_date(date):
    if isinstance(date, datetime.datetime):
        date = date.date()
    assert isinstance(date, datetime.date)
    name = '_calc_' + date.strftime('%Y%m%d')
    mod = __import__(name)
    calc = getattr(mod, 'calc')
    return calc

PATTERN = re.compile('(?P<name>.+)@(?P<start>\d{8}|_):(?P<end>\d{8}|_)\.py')

def str2date(s):
    assert len(s) == 8
    return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:]))

class Finder(object):
    def __init__(self, path):
        print '__init__', path
        if os.path.isfile(os.path.join(path, '.root')):
            self.path = path
            #self.files = os.listdir(self.path)
            self.files = defaultdict(list)
            self._scan()
        else:
            raise ImportError()
            d = {'path': path,
                 'module': self.__class__.__module__,
                 'class': self.__class__.__name__}
            raise ImportError(
                '%(path)r is not good package for %(module)s:%(class)s' % d)

    def _scan(self):
        for fname in os.listdir(self.path):
            if fname.endswith('.py'):
                match = PATTERN.match(fname)
                if match:
                    start = match.group('start')
                    start = datetime.date.min if start == '_' else str2date(start)
                    end = match.group('end')
                    end = datetime.date.max if end == '_' else str2date(end)
                    if end < start:
                        raise RuntimeError('Reversed date range for %r' % fname)
                    name = match.group('name')
                    ranges = self.files[name]
                    if not ranges:
                        ranges.append((start, end, fname))
                    else:
                        found = False
                        for pos, (s, e, f) in enumerate(ranges):
                            if end < s:
                                ranges.insert(pos, ((start, end, fname)))
                                found = True
                                break
                            elif e < start:
                                pass
                            else:
                                raise RuntimeError(
                                    'Overlapped files %r and %r' % (fname, f))
                        if not found:
                            if e < start:
                                ranges.append((start, end, fname))
                            else:
                                raise RuntimeError(
                                    'Overlapped files %r and %r' % (fname, f))
                #sep = fname.find('@')

    def find_module(self, fullname, path=None):
        if fullname.startswith('_calc_'):
            print 'find_module', fullname, path
            parts = fullname.split('.')
            top = parts[0]
            #if len(parts) > 1:
            #    for fname in self.files:
            #        if fname.startswith(
            #    if parts
            date_str = top[len('_calc_'):]
            date = str2date(date_str)
            if len(parts) > 1:
                mod_name = '.'.join(parts[1:])
                if mod_name not in self.files:
                    return None
            else:
                mod_name = '__init__'
            fname = self.find_file(date, mod_name)
            if fname is None:
                return None
            return Loader(self, date, top, mod_name, fname)
        
    def find_file(self, date, name):
        if name == '':
            name = '__init__'
        if name not in self.files:
            return None
        for start, end, fname in self.files[name]:
            if date >= start and date <= end:
                return fname
        return None
        


class Loader(object):
    def __init__(self, finder, date, prefix, mod_name, fname):
        self.finder = finder
        self.date = date
        self.prefix = prefix
        self.fname = fname
        self.mod_name = mod_name

    def load_module(self, fullname):
        print 'load_module', fullname
        parts = fullname.split('.')
        top = parts[0]
        date_str = top[len('_calc_'):]
        date = str2date(date_str)
        
        if len(parts) == 1:
            is_package = True
        else:
            is_package = False
        
        mod = sys.modules.setdefault(fullname, imp.new_module(fullname))
        mod.__file__ = "<calc.%s[%s]->%s>" % (fullname, self.date, self.finder.path)
        mod.__loader__ = self
        if is_package:
            mod.__path__ = [(self.finder.path, self.date)]
            
        with open(os.path.join(self.finder.path, self.fname)) as f:
            exec f.read() in mod.__dict__
        return mod

    def get_data(self, path):
        pass

    def is_package(self, fullname):
        pass

    def get_code(self, fullname):
        pass

    def get_source(self, fullname):
        pass
    
