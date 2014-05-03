#from __future__ import absolute_import
from zope.interface import implements
from import_sample.interface import ICalc

#import pdb;pdb.set_trace()

from .helper import do_calc

class Calc(ICalc):

    def bill(self, data):
        return do_calc(data)

calc = Calc()
