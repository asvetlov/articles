Title: Запуск процессов в tulip
Labels: python, tulip

В последнее время я работаю над запуском процессов в tulip: [PEP 3156](http://www.python.org/dev/peps/pep-3156/) и [реализация на гуглокоде](https://code.google.com/p/tulip/)

## Состояние дел на сегодня

Базовые конструкции выглядят так:

Транспорт:

    class BaseTransport:
        """Base ABC for transports."""

        def get_extra_info(self, name, default=None):
            """Get optional transport information."""

        def close(self):
            """Closes the transport.

            Buffered data will be flushed asynchronously.  No more data
            will be received.  After all buffered data is flushed, the
            protocol's connection_lost() method will (eventually) called
            with None as its argument.
            """

    class SubprocessTransport(BaseTransport):

        def get_pid(self):
            """Get subprocess id."""

        def get_returncode(self):
            """Get subprocess returncode.

            See also
            http://docs.python.org/3/library/subprocess#subprocess.Popen.returncode
            """

        def get_pipe_transport(self, fd):
            """Get transport for pipe with number fd."""

        def send_signal(self, signal):
            """Send signal to subprocess.

            See also:
            http://docs.python.org/3/library/subprocess#subprocess.Popen.send_signal
            """

        def terminate(self):
            """Stop the subprocess.

            Alias for close() method.

            On Posix OSs the method sends SIGTERM to the subprocess.
            On Windows the Win32 API function TerminateProcess()
             is called to stop the subprocess.

            See also:
            http://docs.python.org/3/library/subprocess#subprocess.Popen.terminate
            """

        def kill(self):
            """Kill the subprocess.

            On Posix OSs the function sends SIGKILL to the subprocess.
            On Windows kill() is an alias for terminate().

            See also:
            http://docs.python.org/3/library/subprocess#subprocess.Popen.kill
            """

Протокол:

    class BaseProtocol:
        """ABC for base protocol class.

        Usually user implements protocols that derived from BaseProtocol
        like Protocol or ProcessProtocol.

        The only case when BaseProtocol should be implemented directly is
        write-only transport like write pipe
        """

        def connection_made(self, transport):
            """Called when a connection is made.

            The argument is the transport representing the pipe connection.
            To receive data, wait for data_received() calls.
            When the connection is closed, connection_lost() is called.
            """

        def connection_lost(self, exc):
            """Called when the connection is lost or closed.

            The argument is an exception object or None (the latter
            meaning a regular EOF is received or the connection was
            aborted or closed).
            """


    class SubprocessProtocol(BaseProtocol):
        """ABC representing a protocol for subprocess calls."""

        def pipe_data_received(self, fd, data):
            """Called when subprocess write a data into stdout/stderr pipes.

            fd is int file dascriptor.
            data is bytes object.
            """

        def pipe_connection_lost(self, fd, exc):
            """Called when a file descriptor associated with the child process is
            closed.

            fd is the int file descriptor that was closed.
            """

        def process_exited(self):
            """Called when subprocess has exited.
            """

Нужные методы в event loop:

    class AbstractEventLoop:
        """Abstract event loop."""

        def subprocess_shell(self, protocol_factory, cmd, *, stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             **kwargs):
        """Run cmd in shell"""

        def subprocess_exec(self, protocol_factory, *args, stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            **kwargs):
        """Subprocess *args"""

Т.е. интерфейс запуска процесса почти повторяет `subprocess.Popen` за
исключением того, что `subprocess.PIPE` теперь вариант по
умолчaнию. Заодно еще избавляемся от кошмара с правильным
использованием `shell=True` ([см. пост на эту
тему](http://asvetlov.blogspot.com/2011/03/subprocess.html)). Поддерживаются
только байтовые потоки, как и везде в `tulip`.

Оно уже в целом работает на Unix, код для Windows
[тоже готовится](https://code.google.com/p/tulip/issues/detail?id=54).

Делает всё что можно и нужно за исключением
[TTY](http://en.wikipedia.org/wiki/POSIX_terminal_interface). C
TTY ван Россум предложил пока не связываться, да и `subprocess` его не
поддерживает.

## Проблема

Рабочие транспорты и протоколы — это, конечно, классно. Вполне
подходящий *низкоуровневый* строительный блок.

Но простому программисту хочется иметь что-то более удобное и привычное.

Для `tulip` это должен быть код на основе `yield from`.

Проблема в том, что для процессов мы имеем не один поток ввода-вывода,
а три однонаправленных: `stdin`, `stdout` и `stderr`. А еще процесс
может сам решить закрыться, и это тоже нужно удобно обрабатывать.


## Просьба

Я пытался придумать что-то такое, но результат пока мне не нравится.

Может, кто сумеет посоветовать дельную конструкцию? Или указать на
готовую библиотеку, у которой можно поучиться?
