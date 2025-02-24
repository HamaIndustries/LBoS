from threading import Semaphore as Sem
from conc import thread

"""
3.3 Rendezvous

Generalize the signal pattern bidirectionally:
for two threads A and B, perform actions x1 and x2 each
so that a1 performs before b2 and vice versa.
"""

def p3_3():
    a1ready = Sem(0)
    b1ready = Sem(0)

    @thread()
    def a():
        print("a1")
        a1ready.release()
        b1ready.acquire()
        print("a2")

    @thread()
    def b():
        print("b1")
        b1ready.release()
        a1ready.acquire()
        print("b2")


    aThread = a().start()
    bThread = b().start()

"""
3.6 Barrier

Ensure no thread goes into phase 2 until all have.
"""

def p3_6():
    n_instances = 20
    n_waiting = 0
    access = Sem(1)
    barrier = Sem(0)

    @thread()
    def instance(v: int):
        print(f"inst {v} phase 1")
        access.acquire()
        nonlocal n_waiting
        n_waiting = n_waiting + 1
        access.release()
        if (n_waiting < n_instances):
            barrier.acquire()
            barrier.release()
        else:
            barrier.release()
        print(f"inst {v} phase 2")

    for i in range(n_instances):
        instance(i).start()

"""
3.7 Reusable Barrier

Same as above, but perform an arbitrary number of phases
"""
def p3_7():
    n_instances = 6
    n_waiting = 0
    n_phases = 5
    access = Sem(1)
    phase_start = Sem(0)
    phase_end = Sem(1)

    @thread()
    def instance(v: int):
        nonlocal n_waiting
        for i in range(n_phases):
            # two-phase barrier, aka turnstile.
            # works like a river lock: the nth thread
            # locks the back barrier before opening the front.
            print(f"inst {v} phase {i+1}")
            access.acquire()
            n_waiting += 1
            if n_waiting == n_instances:
                n_waiting = 0
                phase_end.acquire()
                phase_start.release()
            access.release()

            phase_start.acquire()
            phase_start.release()

            access.acquire()
            n_waiting += 1
            if n_waiting == n_instances:
                n_waiting = 0
                phase_start.acquire()
                phase_end.release()
            access.release()

            phase_end.acquire()
            phase_end.release()

    for i in range(n_instances):
        instance(i).start()
