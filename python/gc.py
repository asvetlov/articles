class Node(object):
    parent = None
    cnt = 0

    def __init__(self, *children):
        self.__class__.cnt += 1
        self.children = list(children)
        for node in self.children:
            node.parent = self

    @classmethod
    def tree(cls, depth=1, numchildren=1):
        if depth == 0:
            return []
        return [cls(*cls.tree(depth-1, numchildren))
                for _ in range(numchildren)]

import gc
from time import time

def gc_cb(phase, info):
    if not info['collected'] and not info['uncollectable']:
        return
    print("{0}:\t{1[generation]}, {1[collected]}, {1[uncollectable]}".format(
        phase, info))


gc.callbacks.append(gc_cb)

gc.set_threshold(9330+100, 10, 100)


for n in range(20):
    for _ in range(n):
        # Совершенно случайные величины.
        Node.tree(depth=5, numchildren=6)
        #print(Node.cnt)
        Node.cnt = 0

    ## start = time()
    ## print('{1} objects collected for n={0} in {2:3.6} msec'.format(
    ##       n, gc.collect(), (time() - start) * 1000))
