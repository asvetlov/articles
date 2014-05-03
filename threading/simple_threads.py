import random
import signal
import threading
import time

threads = []
hashes = []

running = True

def sig_handler(sig_num, frame):
    print('SIGNAL')
    global running
    running = False

m = threading.RLock()

def f(me):
    global threads
    while running:
        pass
    hashes.remove(me)

for i in range(1):
    h = random.random()
    hashes.append(h)
    th = threading.Thread(target=f, args=(h,))
    threads.append(th)
    th.start()

signal.signal(signal.SIGINT, sig_handler)

while hashes:
    time.sleep(1)

for th in threads:
    th.join()

