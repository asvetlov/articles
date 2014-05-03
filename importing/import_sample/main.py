# -*- coding: utf-8 -*-

import pkg_resources
from datetime import date
from import_sample.engine import install, for_date

mb = 1024

def main():
    # Установить import hook, указав путь к базе данных
    install(pkg_resources.resource_filename(__name__, 'db'))

    # тестовые данные, количество скачанного трафика для каждого часа в сутках
    d = [0, 0, 10*mb, 20*mb, 0, 0,
         0, 15*mb, 100*mb, 1500*mb, 700*mb, 0,
         0, 0, 0, 0, 0, 0,
         0, 70*mb, 120*mb, 0, 0, 0]

    assert len(d) == 24

    # получить калькулятор на 20 февраля 2010 года
    calc = for_date(date(2010, 2, 20))
    # посчитать, сколько попугаев должен заплатить пользователь
    amount = calc.bill(d)
    print '1111111111111111111', amount

    # то же самое - на 8 марта
    calc = for_date(date(2010, 3, 8))
    amount = calc.bill(d)
    print '22222222222222222222222', amount

if __name__ == '__main__':
    main()
