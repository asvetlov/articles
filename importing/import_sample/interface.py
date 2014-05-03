# -*- coding: utf-8 -*-

#from zope.interface import Interface
import abc

class ICalc(object):
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def bill(self, slices):
        """ Посчитать, сколько попугаев должен заплатить пользователь
        slices: количество скачанного трафика для каждого часа в сутках
        Возвращает decimal.Decimal - сумму.
        """
