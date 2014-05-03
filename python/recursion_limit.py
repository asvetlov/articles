import sys
sys.setrecursionlimit(10)

def g(i):
    if i == 0:
        return
    elif i == 5:
        try:
            print('Ex', i)
            g(i - 1)
        except RuntimeError:
            print '!!!!!!!!!!!!!!!!!!!!!!!!1'
            process_exception()
            return
    print('Ex', i)
    g(i - 1)

def process_exception():
    print('Exception caught')
    g(100)

def f(i):
    print(i)
    try:
        f(i + 1)
    except RuntimeError:
        # recursion limit
        process_exception()


f(0)
