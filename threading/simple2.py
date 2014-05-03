import signal
import threading

threads = []

import signal

running = True

def sig_handler(sig_num, frame):
    print('SIGNAL')
    global running
    running = False

signal.signal(signal.SIGINT, sig_handler)

def f():
    while running:
        pass

for i in range(1):
    th = threading.Thread(target=f)
    threads.append(th)
    th.start()

for th in threads:
    th.join()

