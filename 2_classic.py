from threading import Semaphore as Sem
from time import sleep
import random
from conc import thread


"""
4.1 Producer-Consumer

Producers create things, Consumers consume things.
"""

def p4_1():
    q = []
    access = Sem(1)
    ready = Sem(0)
    work = 1
    w_max = 20
    n_prods = 7
    n_coms = 3
    done = False

    @thread()
    def producer(label: str):
        nonlocal done
        nonlocal work
        while True:
            sleep(0.2) # pretend to calculate something
            access.acquire()
            if work >= w_max:
                done = True
                ready.release()
                access.release()
                print(f"{label} done")
                return
            v = work
            work += 1
            q.append((label, v))
            ready.release()
            access.release()


    @thread()
    def consumer(label: str):
        def fact(i):
            return 1 if i <= 2 else fact(i-1) + fact(i-2)
        nonlocal done
        while True:
            ready.acquire()
            access.acquire()
            if done:
                ready.release()
                access.release()
                print(f"{label} done")
                return
            p, v = q.pop()
            access.release()
            result = fact(v)
            print(f"{label} got request {v} from {p}, answer: {result}")

    for i in range(n_coms):
        consumer(f"[con {i}]").start()
    
    for i in range(n_prods):
        producer(f"[prd {i}]").start()


"""
4.2 Reader-Writers

aka categorical mutex. any # of readers can access critical section,
or exactly one writer can have exclusive access.


"""

def p4_2():
    n_writers = 3
    n_readers = 10
    n_cycles = 10

    write_lock = Sem(1)
    read_lock = Sem(1)

    reading = 0
    data = "seahorse"

    @thread()
    def reader(label: str):
        nonlocal reading
        while True:
            sleep(random.random())
            # read_lock controls access to shared
            # information: reading variable and writing lock.
            # if the number of readers is nonzero, a fake writer
            # is signalled to be in the critical section until
            # the last reader leaves.
            read_lock.acquire()
            if n_cycles <= 0:
                read_lock.release()
                return
            if reading == 0:
                write_lock.acquire()
            reading += 1
            read_lock.release()

            print(f"{label}: read {data}")

            read_lock.acquire()
            reading -= 1
            if reading == 0:
                write_lock.release()
            read_lock.release()

    @thread()
    def writer(label: str):
        nonlocal data
        nonlocal n_cycles
        while True:
            sleep(1 + 3 * random.random())
            read_lock.acquire()
            if n_cycles <= 0:
                read_lock.release()
                return
            n_cycles -= 1
            write_lock.acquire()
            d = list(data)
            random.shuffle(d)
            d = "".join(d)
            data = d
            write_lock.release()
            read_lock.release()
            print(f"{label} wrote {str(d)}")

    for i in range(n_readers):
        reader(f"[reader {i}]").start()
    for i in range(n_writers):
        writer(f"[writer {i}]").start()


"""
4.3 No-Starve

Same as above, but guarantee that readers cannot
starve writers. We can do this by sequencing turnstiles
in such a fashion that every thread that needs to access
a critical section will do so before the next set of threads can.

We create a function turnstile(f) that guards the function passed to
it with a 2-layer turnstile. We use this to guard the acquisition of
the read_lock so that everyone is guaranteed a turn with it.
"""

def p4_3():
    n_writers = 3
    n_readers = 10
    n_cycles = 10

    write_lock = Sem(1)
    read_lock = Sem(1)

    reading = 0
    data = "seahorse"

    wait_lock = Sem(1)
    w1_lock = Sem(1)
    w2_lock = Sem(0)
    w1 = 0 # n threads in phase 1
    w2 = 0 # n threads in phase 2

    def turnstile(f):
        nonlocal w1
        nonlocal w2
        
        wait_lock.acquire()
        w1 += 1
        wait_lock.release()

        w1_lock.acquire()
        w2 += 1
        wait_lock.acquire()
        w1 -= 1
        if w1 == 0:
            wait_lock.release()
            w2_lock.release()
        else:
            wait_lock.release()
            w1_lock.release()

        w2_lock.acquire()
        w2 -= 1
        if f is not None:
            f = f()
        if w2 == 0:
            w1_lock.release()
        else:
            w2_lock.release()
        return f

    @thread()
    def reader(label: str):
        def read():
            nonlocal reading
            read_lock.acquire()
            if n_cycles <= 0:
                read_lock.release()
                return True
            if reading == 0:
                write_lock.acquire()
            reading += 1
            read_lock.release()

            print(f"{label}: read {data}")

            read_lock.acquire()
            reading -= 1
            if reading == 0:
                write_lock.release()
            read_lock.release()

        while True:
            sleep(random.random())
            if turnstile(read):
                return

    @thread()
    def writer(label: str):
        def write():
            nonlocal data
            nonlocal n_cycles
            read_lock.acquire()
            if n_cycles <= 0:
                read_lock.release()
                return True
            n_cycles -= 1
            write_lock.acquire()
            d = list(data)
            random.shuffle(d)
            d = "".join(d)
            data = d
            write_lock.release()
            read_lock.release()
            print(f"{label} wrote {str(d)}")

        while True:
            sleep(1 + 3 * random.random())
            if turnstile(write):
                return

    for i in range(n_readers):
        reader(f"[reader {i}]").start()
    for i in range(n_writers):
        writer(f"[writer {i}]").start()