from datetime import date
import os
import unittest

from import_sample.engine import Finder, str2date

here = os.path.dirname(__file__)

class TestUtils(unittest.TestCase):
    def test_str2date(self):
        self.assertEquals(date(2010, 3, 9), str2date('20100309'))

    def test_str2date_invalid_str(self):
        self.assertRaises(ValueError, str2date, 'abcdefgh')

    def test_str2date_invalid_str2(self):
        self.assertRaises(AssertionError, str2date, '123')

class TestImporter(unittest.TestCase):
    def test_cannot_ctor_without_root_marker(self):
        self.assertRaises(ImportError, Finder, here)

    def test_good_ranges(self):
        finder = Finder(os.path.join(here, 'good_ranges'))
        expected = [(date.min, date(2010, 2, 28), 'a@_:20100228.py'),
                    (date(2010, 3, 1), date(2010, 3, 8), 'a@20100301:20100308.py'),
                    (date(2010, 3, 9), date.max, 'a@20100309:_.py')]
        self.assertEquals(expected, finder.files['a'])

    def test_bad_ranges(self):
        self.assertRaises(RuntimeError, Finder, os.path.join(here, 'bad_ranges'))


