Title: aiopg и SQLAlchemy
Labels: python, SQLAlchemy, asyncio, python3, postgresql

Выпустил новую версию [aiopg 0.2](http://aiopg.readthedocs.org) --
библиотеки для работы с PostgreSQL из
[asyncio](https://docs.python.org/dev/library/asyncio.html).

**aiopg** использует *асинхронные вызовы* и в этом похож на
*txpostgres* и *momoko* -- библиотеки для работы с *PostgreSQL* под
*twisted* и *tornado* соответственно.

В новой версии *aiopg* появилась опциональная поддержка SQLAlchemy Core Expressions.

Проще один раз показать.

Создаем описание структуры базы данных:

    import sqlalchemy as sa

    metadata = sa.MetaData()

    users = sa.Table('users', metadata,
                     sa.Column('id', sa.Integer, primary_key=True),
                     sa.Column('name', sa.String(255)),
                     sa.Column('birthday', sa.DateTime))

    emails = sa.Table('emails', metadata,
                      sa.Column('id', sa.Integer, primary_key=True),
                      sa.Column('user_id', None, sa.ForeignKey('users.id')),
                      sa.Column('email', sa.String(255), nullable=False),
                      sa.Column('private', sa.Boolean, nullable=False))

Как видите -- две таблицы, связанные отношением один-ко-многим. Для
тех, кто не знаком -- алхимия позволяет описать любую модель данных,
которая только может прийти в голову. Индексы, constraints,
пользовательские типы данных такие как array и hstore -- тоже.

Теперь нужно сделать *engine*:

    from aiopg.sa import create_engine
    
    engine = yield from create_engine(user='aiopg',
                                      database='aiopg',
                                      host='127.0.0.1',
                                      password='passwd')

*engine* содержит внутри *connection pool*.

Для работы с БД нужно получить connection и что-нибудь выполнить:

    with (yield from engine) as conn:
        uid = yield from conn.scalar(
            users.insert().values(name='Andrew', birthday=datetime(1978, 12, 9)))

Обратите внимание: диалект знает о `INSERT ... RETURNING` и позвращает
*primary key* для вставляемой записи.

Работа с транзакциями:

    with (yield from engine) as conn:
        tr = yield from conn.begin()

        # Do something

        yield from tr.commit()

Получение данных:

    with (yield from engine) as conn:
        res = yield from conn.execute(users.select())
        for row in res:
            print(res)

Сложный запрос:

    with (yield from engine) as conn:
        join = sa.join(emails, users, users.c.id == emails.c.user_id)
        query = (sa.select([users.c.name])
                 .select_from(join)
                 .where(emails.c.private == 0)
                 .group_by(users.c.name)
                 .having(sa.func.count(emails.c.private) > 0))

        print("Users with public emails:")
        ret = yield from conn.execute(query)
        for row in ret:
            print(row.name)

Вызов SQL функций:

    with (yield from engine) as conn:
        query = (sa.select([sa.func.avg(sa.func.age(users.c.birthday))])
                 .select_from(users))
        ave = (yield from conn.scalar(query))
        print("Average age of population is", ave,
              "or ~", int(ave.days / 365), "years")

`sa.func.avg` и `sa.func.age` выполняются на стороне SQL сервера.

Полный код примера
[здесь](https://github.com/aio-libs/aiopg/blob/master/examples/sa.py),
документация [здесь](http://aiopg.readthedocs.org).
