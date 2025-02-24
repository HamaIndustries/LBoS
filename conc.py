from threading import Thread, Semaphore
from collections import deque
from typing import Hashable, Generator

class CustomThread(Thread):
    def start(self):
        super().start()
        return self

def thread(**kw):
    def wrap(f):
        def inner(*ai, **kwi):
            return CustomThread(target=lambda: f(*ai, **kwi), **kw)
        return inner
    return wrap

"""
Lightswitch class from classical problems chapter
"""
class Lightswitch :
    def __init__ (self ):
        self.counter = 0
        self.mutex = Semaphore(1)

    def lock (self, semaphore):
        self.mutex.acquire()
        self.counter += 1
        if self.counter == 1:
            semaphore.acquire()
        self.mutex.release()

    def unlock (self, semaphore):
        self.mutex.acquire()
        self.counter -= 1
        if self.counter == 0:
            semaphore.release()
        self.mutex.release()

"""
Similar to the Lightswitch class from the classical problems chapter,
but makes explicit the relationship between gatekeeper and gate visitors.
"""
class Gate:
    def __init__(self):
        self._switch = Lightswitch()
        self._count = 0
        self._mutex = Semaphore(1)
        self._control = Semaphore(1)

    def enter(self):
        self._mutex.acquire()
        if self._count == 0:
            self._control.acquire()
        self._count += 1
        self._mutex.release()

    def exit(self):
        self._mutex.acquire()
        self._count -= 1
        if self._count < 0:
            raise RuntimeError("exit called more times than allowed")
        if self._count == 0:
            self._control.release()
        self._mutex.release()
    
    """
    Prevents entry until open()'d, and blocks the calling thread
    until all entered threads have exited.
    """
    def close(self):
        self._mutex.acquire()

    def open(self):
        self._mutex.release()


class Synchronizer():
    def __init__(self):
        self.aPresent = False
        self.bPresent = False
        self.mutex = Semaphore(1)
        self.mutA = Semaphore(0)
        self.mutB = Semaphore(0)
        self.mutASend = Semaphore(0)
        self.mutBSend = Semaphore(0)
        self.aq = deque()
        self.bq = deque()
        self.sendA = None
        self.sendB = None

    def syncA(self, send=None):
        self.mutB.release()
        self.mutA.acquire()
        self.mutex.acquire()
        self.aq.append(send)
        self.mutex.release()
        self.mutBSend.release()
        self.mutASend.acquire()
        self.mutex.acquire()
        v = self.bq.popleft()
        self.mutex.release()
        return v
            
    def syncB(self, send=None):
        self.mutA.release()
        self.mutB.acquire()
        self.mutex.acquire()
        self.bq.append(send)
        self.mutex.release()
        self.mutASend.release()
        self.mutBSend.acquire()
        self.mutex.acquire()
        v = self.aq.popleft()
        self.mutex.release()
        return v
    

_lockLookup = {}

# Behaves like java's synchronized blocks, creating or
# obtaining a mutex given a hashable object key.
class lock:
    def __init__(self, key: Hashable):
        if key not in _lockLookup:
            _lockLookup[key] = Semaphore(1)
        self.sem = _lockLookup[key]

    def __enter__(self):
        self.sem.acquire()
    
    def __exit__(self, type, val, traceback):
        self.sem.release()

def semaphores(*sizes):
    return (Semaphore(s) for s in sizes)
