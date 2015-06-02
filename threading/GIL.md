Title: Загадочный GIL
Labels: python, gil, threads
slug: gil


Наверное, каждый питонист слышал про существование *Global Interpreter
Lock (GIL)*.  Обычно знание предмета исчерпывается фразой: *"Это - та
самая гадость, которая не позволяет запустить одновременно как минимум
два потока, задействовав все имеющиеся ядра современного процессора"*.

Высказывание отчасти верное, но совершенно неконструктивное и не
покрывающее всей многогранности рассматриваемого вопроса.

Позвольте мне пройтись по теме более подробно, рассмотрев вопросы
*GIL* и реализации Питоном многопоточности с разных сторон.

## Короткое определение

Прежде всего GIL — это блокировка, которая обязательно должна быть
взята перед любым обращением к Питону (а это не только исполнение
питоновского кода а еще и вызовы Python C API). Строго говоря,
единственные вызовы, доступные после запуска интерпретатора при
незахваченном GIL — это его захват. Нарушение правила ведет к
мгновенному аварийному завершению (лучший вариант) или отложенному
краху программы (куда более худший и труднее отлаживаемый сценарий).

## Многопоточный код на питоне

Это — самый простой уровень.  Имеем обычную программу, состоящую
исключительно из питоновских модулей (`.py` файлы) и не содержащую
*Python C Extensions*.  Пусть в ней работают два потока: главный и
запущенный нами.

    import threading
    import time

    running = True

    def f(delay):
        while running:
            time.sleep(delay)

    th = threading.Thread(target=f, args=(0.5,))
    th.start()

    for i in range(10):
        time.sleep(0.7)

    running = False

    th.join()

Многопоточная программа на С не должна как-то отдельно регистрировать
свои потоки — достаточно вызова API (pthread_create или CreateThread)
для запуска потока.  Интерпретатор питона для своей работы требует
ряда структур.  Давайте рассмотрим их подробнее.

## Структуры интерпретатора, обеспечивающие многопоточную работу

`PyInterpreterState` содержит глобальное состояние интерпретатора:
загруженные модули `modules`, указатель на первый (он же главный)
поток `tstate_head` и кучу других важных для внутренней кухни вещей.

    struct PyInterpreterState {
        PyInterpreterState *next;
        PyThreadState *tstate_head;

        PyObject *modules;
        PyObject *sysdict;
        PyObject *builtins;
        PyObject *modules_reloading;

        PyObject *codec_search_path;
        PyObject *codec_search_cache;
        PyObject *codec_error_registry;
    };

`PyThreadState` позволяет узнать, какой кадр стека (`frame`)
исполняется и какой номер у потока с точки зрения операционной
системы.  Остальные атрибуты сейчас не важны.

    struct PyThreadState {
        PyThreadState *next;
        PyInterpreterState *interp;

        PyFrameObject *frame;
        int recursion_depth;

        Py_tracefunc c_profilefunc;
        Py_tracefunc c_tracefunc;
        PyObject *c_profileobj;
        PyObject *c_traceobj;

        PyObject *exc_type;
        PyObject *exc_value;
        PyObject *exc_traceback;

        PyObject *dict;  /* Stores per-thread state */

        long thread_id;
    };

`PyFrameObject` — это объект кадра стека.  Питоновский объект, в
отличие от первых двух структур (на это указывает
`PyObject_VAR_HEAD`).  Имеет указатель на предыдущий кадр `f_back`,
исполняемый код `f_code` и последнюю выполненную в этом коде
инструкцию `f_lasti`, указатель на свой поток `f_tstate` и серию из
глобального, локального и встроенного пространства имен (`f_globals`,
`f_locals` и `f_builtins` соответственно).

    struct PyFrameObject {
        PyObject_VAR_HEAD
        PyFrameObject *f_back;	/* previous frame, or NULL */
        PyCodeObject *f_code;	/* code segment */
        PyObject *f_builtins;	/* builtin symbol table (PyDictObject) */
        PyObject *f_globals;	/* global symbol table (PyDictObject) */
        PyObject *f_locals;		/* local symbol table (any mapping) */

        PyThreadState *f_tstate;
        int f_lasti;		/* Last instruction if called */
    };

На самом деле членов в этих структурах поболее, и сами структуры
отличаются от версии к версии (особенно заметны отличия между 2.x и
3.x) — но сейчас это не важно.

Важно понимать, что все три необходимых для исполнения структуры взаимно связаны
между собой и `PyThreadState_GET()` возвращает указатель на текущий работающий
поток:

![график связывания структур][gil_structs]

## GIL

Теперь пришло время показать, как именно работает GIL.  Тут есть одна
тонкость: в 3.2 его реализация довольно значительно изменилась. Для
начала рассмотрим «старый» GIL, используемый в Python 2.x и 3.0/3.1.

GIL переключается каждые 100 инструкций.  Под инструкцией здесь
понимается одна операция питоновского байткода.  Возьмем простую
функцию:

    def f(lst, val):
        return [i for i in lst if i != val]

Применим к ней дизассемблер:

    import dis
    dis.dis(f)
      2           0 BUILD_LIST               0
                  3 LOAD_FAST                0 (lst)
                  6 GET_ITER
            >>    7 FOR_ITER                24 (to 34)
                 10 STORE_FAST               2 (i)
                 13 LOAD_FAST                2 (i)
                 16 LOAD_FAST                1 (val)
                 19 COMPARE_OP               3 (!=)
                 22 POP_JUMP_IF_FALSE        7
                 25 LOAD_FAST                2 (i)
                 28 LIST_APPEND              2
                 31 JUMP_ABSOLUTE            7
            >>   34 RETURN_VALUE

Как видите, код превратился в последовательность этих самых
инструкций, исполняемых интерпретатором.  Скажу сразу: никакой внятной
документации по байт-коду нет, инструкции добавляются и изменяются от
версии к версии.  Интересующиеся должны читать файл `Python/ceval.c`
как первоисточник для понимания того, что какая инструкция делает.

Возвращаясь к GIL: он будет производить переключения между
инструкциями, на каждой сотой выполненной.

Сам GIL устроен как обычная не-рекурсивная блокировка.  Эта же
структура лежит в основе `threading.Lock`. Реализуется через событие
`CreateEvent` с бубенцами на `Windows` и семафор `sem_t` на Linux.

Давайте посмотрим на кусочек исходного кода функции
`PyEval_EvalFrameEx`, которая представляет собой цикл с очень объемным
`switch/case` внутри, исполняющим по одной инструкции за проход.

    PyObject *
    PyEval_EvalFrameEx(PyFrameObject *f, int throwflag)
    {
        PyThreadState *tstate = PyThreadState_GET();
        /* ... */
        for (;;) {
            /* ... */
            if (--_Py_Ticker < 0) {
                /* ... */
                _Py_Ticker = _Py_CheckInterval;
                if (interpreter_lock) {
                    /* Give another thread a chance */
                    if (PyThreadState_Swap(NULL) != tstate)
                        Py_FatalError("ceval: tstate mix-up");
                    PyThread_release_lock(interpreter_lock);

                    /* Other threads may run now */

                    PyThread_acquire_lock(interpreter_lock, 1);
                    if (PyThreadState_Swap(tstate) != NULL)
                        Py_FatalError("ceval: orphan tstate");
                    /* ... */
                }
            }
        /* instruction processing */
        }
    }

Как видите, все просто: имея захваченный GIL (а поток уже им владеет
перед вызовом `PyEval_EvalFrameEx`), каждый раз уменьшаем счетчик пока
не дойдем до нуля. `interpreter_lock` — это наш GIL, указатель на
объект блокировки.  Если он есть (а есть всегда, за исключением
специальных сборок питона с полностью отключенной многопоточностью),
то происходит так называемое «переключение GIL».

`PyThreadState_Swap` сбрасывает указатель на текущий исполняемый поток
(тот самый, который возвращается `PyThreadState_GET`) и освобождает
GIL.

Затем следующей строкой пытается захватить этот GIL снова.  Хитрость в
том, что если работает несколько потоков одновременно, то операционная
система сама будет определять, какой поток из ожидающих в
`PyThread_acquire_lock` получит эту блокировку (остальные будут ждать
следующего освобождения `interpreter_lock`).  Современные операционные
системы используют довольно замысловатые алгоритмы переключения
потоков.  Нам же нужно знать лишь то, что эти алгоритмы пытаются
распределить время «справедливо», дав каждому поработать.  Это
означает, что только что освободивший GIL поток скорее всего обратно
сразу же его не получит — а отдаст управление другому потоку и сам
встанет в ожидание `PyThread_acquire_lock`.

Все работает, и схема получается надежная.  Но она имеет ряд
существенных недостатков:

* GIL переключается даже в однопоточной программе.  Формально
`interpreter_lock` создается не сразу при старте интерпретатора.  Но
импорт модуля `threading` или, к примеру, `sqlite3` создаст GIL даже
без создания второго потока.  На практике правильней считать, что GIL
есть всегда.
* Другими словами GIL переключается постоянно, независимо от того
требует ли другой поток переключения или они все заблокированы
ожиданием ввода-вывода или объектами синхронизации.
* Потоки «соревнуются» за захват GIL.  Планировщик операционной
системы — очень сложно устроенная штука.  Поток, интенсивно
использующий операции ввода-вывода, получает более высокий приоритет
чем чисто вычислительный поток.  Например, первый поток читает из
файла и складывает прочитанное в очередь.  Второй поток получает
данные из очереди и обрабатывает их.  Штука в том, что считывающий
поток, обладая высоким приоритетом, может класть новые данные в
очередь довольно долго, прежде чем обработчик получит возможность их
обрабатывать.  Да, первый поток регулярно освобождает GIL — но он тут
же получает его назад (приоритет выше).  Эта ситуация может быть
исправлена выбором правильного способа взаимодействия между потоками,
но решение зачастую неочевидно и, главное, проблема трудно
локализуется.
* И, наконец, главная причина.  Переключение происходит по количеству
выполненных инструкций.  Дело в том, что время выполнения инструкций
может сильно отличаться (сравните простое сложение и создание списка
на миллион элементов).

Для управления порогом переключения существуют функции:

* `sys.getcheckinterval()`
* `sys.setcheckinterval(count)`

В силу слабой связанности интервала переключения со временем
исполнения эти функции практически бесполезны.  По крайней мере я
никогда не видел их применения в реальном коде.

## Новый GIL

Он использует усовершенствованную схему, базирующуюся на
времени.  Кроме того, добавлен специальный механизм для предотвращения
повторного захвата GIL.

Снова выдержка из `PyEval_EvalFrameEx`, на этот раз Python 3.2.

    PyObject *
    PyEval_EvalFrameEx(PyFrameObject *f, int throwflag)
    {
        PyThreadState *tstate = PyThreadState_GET();
        /* ... */
        for (;;) {
            /* ... */
            if (_Py_atomic_load_relaxed(&eval_breaker)) {
                /* ... */
                if (_Py_atomic_load_relaxed(&gil_drop_request)) {
                    /* Give another thread a chance */
                    if (PyThreadState_Swap(NULL) != tstate)
                        Py_FatalError("ceval: tstate mix-up");
                    drop_gil(tstate);

                    /* Other threads may run now */

                    take_gil(tstate);
                    if (PyThreadState_Swap(tstate) != NULL)
                        Py_FatalError("ceval: orphan tstate");
                }
            }
        /* instruction processing */
        }
    }

Как видите, внешне почти ничего не изменилось. Ушел счетчик
`_Py_Ticker`, Появились две переменные: `eval_breaker` и
`gil_drop_request`.  Переключение произойдет, если обе установлены
(ненулевые).  Две переменные нужны потому, что один и тот же механизм
используется для штатного переключения GIL и для обработки сигналов
операционной системы.

`eval_breaker` указывает на необходимость переключения, а
`gil_drop_request` используется для штатной ситуации переключения
потоков.

`_Py_atomic_load_relaxed` — это просто макрос для атомарного чтения
переменной.

Вся магия скрыта внутри функций `drop_gil` и `take_gil`, работающих в
паре.

    static void drop_gil(PyThreadState *tstate)
    {
        if (!_Py_atomic_load_relaxed(&gil_locked))
            Py_FatalError("drop_gil: GIL is not locked");

        MUTEX_LOCK(gil_mutex);
        _Py_ANNOTATE_RWLOCK_RELEASED(&gil_locked, /*is_write=*/1);
        _Py_atomic_store_relaxed(&gil_locked, 0);
        COND_SIGNAL(gil_cond);
        MUTEX_UNLOCK(gil_mutex);

        if (_Py_atomic_load_relaxed(&gil_drop_request)) {
            MUTEX_LOCK(switch_mutex);
            /* Not switched yet => wait */
            RESET_GIL_DROP_REQUEST();
            COND_WAIT(switch_cond, switch_mutex);
            MUTEX_UNLOCK(switch_mutex);
        }
    }

Наш герой теперь называется `gil_locked` — обычная целочисленная
переменная.  Используется блокировка `gil_mutex` в паре с условной
переменной `gil_cond` для синхронизации доступа к GIL.
`gil_drop_request` — запрос на переключение GIL, защищенный
`switch_mutex` и `switch_cond`.

В «отпускающей» стороне нет ничего сложного: прикрываясь `gil_mutex`
сбрасываем GIL (`gil_locked`) в нолик и сигналим об этом событии через
`gil_cond`.

Затем смотрим, это была просьба о переключении от другого потока или
наш поток сам попросил освободиться.  Дело в том, что Питон отпускает
GIL перед системными вызовами.  Чтение из файла, к примеру, может
занимать длительное время и совершенно не требует GIL — можно дать
шанс другим потокам поработать.

Если GIL освобождается не по внешнему запросу — работа
закончена.  Иначе нужно дождаться, пока попросивший не захватит
GIL. Таким образом форсируется переключение на другой поток.

    static void take_gil(PyThreadState *tstate)
    {
        MUTEX_LOCK(gil_mutex);

        while (_Py_atomic_load_relaxed(&gil_locked)) {
            int timed_out = 0;
            unsigned long saved_switchnum;

            saved_switchnum = gil_switch_number;
            COND_TIMED_WAIT(gil_cond, gil_mutex, INTERVAL, timed_out);
            /* If we timed out and no switch occurred in the meantime,
               it is time to ask the GIL-holding thread to drop it. */
            if (timed_out &&
                _Py_atomic_load_relaxed(&gil_locked) &&
                gil_switch_number == saved_switchnum) {
                SET_GIL_DROP_REQUEST();
            }
        }
        /* This mutex must be taken before modifying gil_last_holder. */
        MUTEX_LOCK(switch_mutex);
        /* We now hold the GIL */
        _Py_atomic_store_relaxed(&gil_locked, 1);
        ++gil_switch_number;
        _Py_ANNOTATE_RWLOCK_ACQUIRED(&gil_locked, /*is_write=*/1);

        COND_SIGNAL(switch_cond);
        MUTEX_UNLOCK(switch_mutex);

        if (_Py_atomic_load_relaxed(&gil_drop_request)) {
            RESET_GIL_DROP_REQUEST();
        }

        MUTEX_UNLOCK(gil_mutex);
    }

Захват GIL зеркально отражает его освобождение.  Сначала ждем, пока GIL
не освободится.  Если ждем долго (больше 5 мс по умолчанию) и при этом
не произошло переключения (не важно, на нас или какой другой поток) —
выставляем запрос на переключение.

Дождавшись наконец свободного GIL, захватываем его и сигналим
отдавшему потоку что передача состоялась.  Естественно, все обращения
защищены блокировками.

Что получилось в итоге:

* поток, владеющий GIL, не отдает его пока об этом не попросят.
* если уж отдал по просьбе, то подождет окончания переключения и не
будет сразу же пытаться захватить GIL назад.
* поток, у которого сразу не получилось захватить GIL, сначала выждет
5 мс и лишь потом пошлет запрос на переключение, принуждая текущего
владельца освободить ценный ресурс. Таким образом переключение
осуществляется не чаще чем раз в 5 мс, если только владелец не отдаст
GIL добровольно перед выполнением системного вызова.

Управление временем переключения — через `sys.getswitchinterval` и
`sys.setswitchinterval`. Обратите внимание: в python 3.2 остались
`sys.getcheckinterval` и `sys.setcheckinterval`, но они ни на что не
влияют.

## GIL и системные вызовы

Почти любое обращение к ядру операционной системы — довольно затратная
операция.  Более того, этот вызов может блокировать поток на
значительный промежуток времени.  Скажем, открытие файла может
потребовать нескольких обращений к диску, если только этот файл уже не
находится в файловом кэше.

GIL — один на всю программу. Слишком расточительно позволять потоку
ждать окончания системного вызова (или любой другой операции,
занимающей время и не требующей обращения к питоньим структурам),
когда другие потоки простаивают в ожидании своей очереди на
исполнение.

Поэтому перед вызовом такого долгоиграющего кода нужно отпустить GIL,
а потом сразу же его захватить обратно:

    Py_BEGIN_ALLOW_THREADS
    errno = 0;
    self->fd = open(name, flags, 0666);
    Py_END_ALLOW_THREADS

Макросы `Py_BEGIN_ALLOW_THREADS` и `Py_END_ALLOW_THREADS` делают всю
необходимую работу.

*Обратите внимание, вкладывать друг в друга эти макросы запрещено!*
Один раз разрешив потоки, нельзя разрешить их вторично.  Например,
такой код ошибочный:

    void f()
    {
        Py_BEGIN_ALLOW_THREADS
        /* do something */
        Py_END_ALLOW_THREADS
    }

    void g()
    {
        Py_BEGIN_ALLOW_THREADS
        f();
        Py_END_ALLOW_THREADS
    }

Если очень хочется, то внутри функции можно писать
`Py_BLOCK_THREADS`/`Py_UNBLOCK_THREADS` для временного получения GIL
назад.  Например, так:

    PyObject* g()
    {
        int ret;
        Py_BEGIN_ALLOW_THREADS
        ret = f();
        if (ret) {
            Py_BLOCK_THREADS
            PyErr_SetFromErrno(PyExc_IOerror);
			Py_UNBLOCK_THREADS
            return NULL;
        }
        Py_END_ALLOW_THREADS
    }

Во вложенной функции испрользовать `Py_BLOCK_THREADS` не получится —
эти макросы используют стандартные питоновские вызовы
`PyEval_SaveThread`/`PyEval_RestoreThread` с сохранением структуры
`PyThreadState` в локальной переменной `_save`.

Коротко говоря, следите за руками и одновременно изучайте исходники
Питона.  Они занятные — регулярно перечитываю перед сном.

## GIL и потоки

Вернемся опять к самому первому кусочку кода из этой статьи, который
создавал поток из Питона.  Питон — умный, он сам делает всю черновую
работу, необходимую для регистрации потока в своих внутренних
структурах.

Давайте посмотрим, как именно создается новый поток.

Вспомогательная структура:

    struct bootstate {
        PyInterpreterState *interp;
        PyObject *func;
        PyObject *args;
        PyObject *keyw;
        PyThreadState *tstate;
    };

Просто хранит функцию, которую нужно выполнить в новом потоке, и ее
параметры.  Состояние потока и интерпретатора тоже пригодится.

Код, запускающий поток:

    static PyObject *
    thread_PyThread_start_new_thread(PyObject *self, PyObject *fargs)
    {
        PyObject *func, *args, *keyw = NULL;
        struct bootstate *boot;
        long ident;

        boot = PyMem_NEW(struct bootstate, 1);
        if (boot == NULL)
            return PyErr_NoMemory();
        boot->interp = PyThreadState_GET()->interp;
        boot->func = func; boot->args = args; boot->keyw = keyw;
        boot->tstate = _PyThreadState_Prealloc(boot->interp);
        if (boot->tstate == NULL) {
            PyMem_DEL(boot);
            return PyErr_NoMemory();
        }
        Py_INCREF(func); Py_INCREF(args); Py_XINCREF(keyw);
        PyEval_InitThreads(); /* Start the interpreter's thread-awareness */
        ident = PyThread_start_new_thread(t_bootstrap, (void*) boot);
        if (ident == -1) {
            PyErr_SetString(ThreadError, "can't start new thread");
            Py_DECREF(func); Py_DECREF(args); Py_XDECREF(keyw);
            PyThreadState_Clear(boot->tstate);
            PyMem_DEL(boot);
            return NULL;
        }
        return PyLong_FromLong(ident);
    }

Ничего сложного: создаем `bootstate` и запускаем в новом потоке
функцию `t_bootstrap`, которая должна закончить регистрацию
`PyThreadState`. `PyThread_start_new_thread` — платформонезависимая
обертка для создания потока ядра.

Сама запускаемая функция:

    static void
    t_bootstrap(void *boot_raw)
    {
        struct bootstate *boot = (struct bootstate *) boot_raw;
        PyThreadState *tstate;
        PyObject *res;

        tstate = boot->tstate;
        tstate->thread_id = PyThread_get_thread_ident();
        _PyThreadState_Init(tstate);
        PyEval_AcquireThread(tstate);
        nb_threads++;
        res = PyEval_CallObjectWithKeywords(
            boot->func, boot->args, boot->keyw);
        if (res == NULL) {
            if (PyErr_ExceptionMatches(PyExc_SystemExit))
                PyErr_Clear();
            else {
                PyObject *file;
                PySys_WriteStderr(
                    "Unhandled exception in thread started by ");
                file = PySys_GetObject("stderr");
                if (file != NULL && file != Py_None)
                    PyFile_WriteObject(boot->func, file, 0);
                else
                    PyObject_Print(boot->func, stderr, 0);
                PySys_WriteStderr("\n");
                PyErr_PrintEx(0);
            }
        }
        else
            Py_DECREF(res);
        Py_DECREF(boot->func); Py_DECREF(boot->args); Py_XDECREF(boot->keyw);
        PyMem_DEL(boot_raw);
        nb_threads--;
        PyThreadState_Clear(tstate);
        PyThreadState_DeleteCurrent();
        PyThread_exit_thread();
    }

Код длинный, но простой. Из запущенного потока можно узнать его номер
(идентификатор, используемый при обращениях к операционной
системе). Осталось закончить инициализацию `PyThreadState` и выполнить
запрашиваемую питоновскую функцию (`PyEval_CallObjectWithKeywords`).
После окончания работы нужно почистить за собой. Если было исключение
— записать его в `stderr` *(исключения из потока не пробрасываются
запустившему этот поток коду, остается только запись в поток ошибок)*.

Без приведенного пролога обращение к питону из нового потока приведет
к краху интерпретатора. Причем не сразу же, а когда потребуется
переключить GIL.  Обращение к глобальным структурам может разрушить
память.

Способ, используемый Питоном, рабочий. Но не самый подходящий для
стороннего кода, желающего запускать питон в произвольном потоке,
созданном без помощи Python API. Дело в том, что приведенные функции
используют закрытую часть API — функции, начинающиеся с подчеркивания.

Код можно было бы переписать, полностью перенеся создание
`PyThreadState` в `t_bootstrap` и сократив его до:

    PyThreadState *tstate = PyThreadState_New(boot->interp);
    PyEval_AcquireThread(tstate);

Вообще-то в наборе функций для работы с потоками и GIL наблюдается
некоторый разброд и шатание. Например, `PyEval_AcquireThread`
захватывает GIL. `PyEval_RestoreThread` делает практически то же самое
плюс специальную проверку на случай завершения интерпретатора (которая
в правильно написанной программе не нужна, порожденные потоки должны
получить сигнал о завершении раньше, чем произойдет завершение
питоновского кода в главном потоке). То же самое можно сказать про
пару `PyEval_ReleaseThread` и `PyEval_SaveThread` и так далее.

В оправдание сложившегося положения вещей можно сказать, что эта часть
API развивалась долго, постепенно переходя из закрытой в публичную и
документированную. Существующие сторонние модули чаще всего писались
по принципу "работает—и ладно", использование закрытого API авторов не
волновало (тем более что открытое API появлялось с некоторым
опозданием). На данный момент имеем множество библиотек, которые могут
поломаться, вздумай разработчики Питона разом отрубить все устаревшие
части API. Поэтому процесс удаления устаревшего кода занимает как
минимум 2-3 версии питона (что составляет около 4-5 лет) со строгими
предупреждениями и разъяснениями. И тем не менее всегда остаются
недовольные авторы, чей код «внезапно» перестал компилироваться.

## Временное получение GIL

Бывает так, что нужно выполнить питоновский вызов, не зная —
зарегистрирован ли поток или еще нет. Для этого существует пара `PyGILState_Ensure` и `PyGILState_Release`:

    PyGILState_STATE opaque = PyGILState_Ensure();
    /* do stuff */
    PyGILState_Release(opaque);

Между вызовами *ensure*/*release* можно делать всё, что угодно — GIL
захвачен, PyThreadState настроен. Можно, например, использовать
`Py_BEGIN_ALLOW_THREADS`/`Py_END_ALLOW_THREADS` и вообще вызывать
любой питоновский код. Более того, можно делать вложенные вызовы
`PyGILState_Ensure` — главное не забывать о необходимых
`PyGILState_Release`.

Нужно только всегда помнить об одной маленькой детали. Дело в том, что
при каждом вызове `PyGILState_Ensure` система смотрит, был ли
зарегистрирован `PyThreadState` для исполняемого потока. Если был — то
захват происходит быстро. Иначе нужно создать и зарегистрировать новый
`PyThreadState`. Для существующей структуры достаточно просто
увеличить счетчик использования. `PyGILState_Release` этот счетчик
уменьшает и, досчитав до нуля, удаляет зарегистрированный
`PyThreadState`. На удаление тоже нужно время. Потери относительно
небольшие, если только код не исполняется очень много раз. Иными
словами, вместо создания/удаления `PyThreadState` в цикле:

    void f() {
        int i;
        PyGILState_STATE state;
        for(i=0; i<100000; ++i) {
            /* do C block */
            state = PyGILState_Ensure();
            /* call python API */
            PyGLIState_Release(state);
        }
    }

лучше написать работающий практически так же, но более оптимальный по
скорости код:

    void f() {
        int i;
        PyGILState_STATE state, outer_state;
        outer_state = PyGILState_Ensure();
        Py_BEGIN_ALLOW_THREADS
        for(i=0; i<100000; ++i) {
            /* do C block */
            state = PyGILState_Ensure();
            /* call python API */
            PyGILState_Release(state);
        }
        Py_END_ALLOW_THREADS
        PyGILState_Release(outer_state);
    }

## Заключение

Я постарался как можно подробней описать, как работает GIL. Полностью
покрыть эту тему невозможно даже в большой статье. Поэтому, если
возникают вопросы — задавайте их или (что надежней и полезней) читайте
ответ в исходном коде Питона, он простой и понятный.

Несколько слов «на общие темы».

* GIL не уберут никогда. Или, по крайней мере, в ближайший десяток
  лет. Сейчас никаких работ на эту тему не ведется. Если некий гений
  предъявит работающую реализацию без GIL, ничего не ломающую и
  работающую не медленней, чем существующая версия — предложению будет
  открыт зеленый свет. Пока же «убрать GIL» проходит по части благих,
  но невыполнимых пожеланий.

* В Java и C# никакого GIL нет. Потому что у них иначе устроен garbage
  collector. Если хотите, он более прогрессивный. Переделать GC
  Питона, не сломав обратной совместимости со всеми существующими
  библиотеками, использующими Python C API — невозможно. Сообщество и
  так уже который год лихорадит в связи с переходом на Python
  3.x. Разработчики не желают выкатывать второе революционное
  изменение, не разобравшись с первым. Ждите Python 4.x (которого нет
  даже в планах) — до тех пор ничего не поменяется.

* Несмотря на то, что GIL позволяет работать только одному
  питоновскому потоку на запущенный процесс, существуют способы
  нагрузить все имеющиеся ядра процессора.

    * Во первых, если поток не делает вызовов Python C API — то GIL ему не
      нужен. Так можно держать много параллельно работающих
      потоков-числодробилок плюс несколько медленных питоновских потоков
      для управления всем хозяйством. Конечно, для этого нужно уметь
      писать Python C Extensions.
    * Второй способ еще лучше. Замените «поток» на «процесс». По
      настоящему высоконагруженная система в любом случае должна строится
      с учетом масштабируемости и высокой надежности. На эту тему можно
      говорить очень долго, но хорошая архитектура автоматически позволяет
      вам запускать несколько процессов на одной машине, которые общаются
      между собой через какую-либо систему сообщений. В качестве одного из
      приятных бонусов получается избавление от "проклятия GIL" — у
      каждого процесса он только один, но процессов много!


Надеюсь, прочитанное поможет вам понять, как GIL работает, какие у
него есть неочевидные особенности. И, главное — запомнить, как он не работает
никогда!

## GIL и обработка сигналов 

В дополнение к этой статье рекомендую
прочесть про [особенности обработки сигналов Питоном в posix
средах](http://asvetlov.blogspot.com/2011/07/signal.html).

## Ссылки:

* Замечательная статья от признанного специалиста по GIL [Дэвида Бизли (Dave
  Beazley)](http://www.dabeaz.com/python/NewGIL.pdf)
* Описание проблем с `PyGILState_Ensure` в блоге [Kristján Valur,
  ведущего специалиста по Питону в CCP Games (Eve
  Online)](http://blog.ccpgames.com/kristjan/2011/06/23/temporary-thread-state-overhead/)

[gil_structs]: https://lh6.googleusercontent.com/-kKFOmVCvEHQ/TgiH_dog7KI/AAAAAAAACT0/PQHp4-MkIPw/s640/gil_structs.png "Gil Structs"

