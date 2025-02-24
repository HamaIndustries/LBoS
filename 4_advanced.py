import random
from collections import deque
from threading import Semaphore as Sem
from time import sleep
from functools import reduce

from conc import thread, Synchronizer, lock, semaphores, Gate

def out(label, msg, *a, **kw):
    print(f"{label}: {msg}", *a, **kw, flush=True)

"""
6.1 The search-insert-delete problem

Given a singly linked list, we have threads consisting of searchers, inserters
and deleters. Searchers examine the list and can execute concurrently.
Inserters add to the end of the list in a mutex fashion, but any insert
can be concurrent with searches.
"""
def p6_1():
    n_search = 7
    n_insert = 3
    n_delete = 2

    gate = Gate()

    @thread()
    def searcher(lbl: str):
        while True:
            sleep(random.random() * 0.3)
            gate.enter()
            out(lbl, "search")
            gate.exit()
        
    @thread()
    def inserter(lbl: str):
        while True:
            sleep(random.random() * 0.5)
            gate.enter()
            out(lbl, "insert")
            gate.exit()

    @thread()
    def deleter(lbl: str):
        while True:
            sleep(3 + random.random() * 2)
            out(lbl, "locking for deletion")
            gate.close()
            out(lbl, "deleting...")
            sleep(1)
            out(lbl, "deleted.")
            gate.open()

    for i in range(n_search):
        searcher(f"[srch {i}]").start()
    for i in range(n_insert):
        inserter(f"[inst {i}]").start()
    for i in range(n_delete):
        deleter(f"[dlte {i}]").start()

"""
7.3 The room party problem
"""

def p7_3():
    party = 50 # number of people constituting a party
    n = 200 # number of students
    rooms = [0] * 5
    parties = list(semaphores(*[1 for _ in range(len(rooms))]))

    def state():
        r = []
        for i in range(len(rooms)):
            with lock(i):
                r.append(rooms[i])
        return " ".join(f"[{i}]" for i in r)

    @thread()
    def student(lbl: str):
        in_room = None
        while True:
            sleep(random.random() * 0.2)
            if in_room is not None: 
                with lock(in_room):
                    population = rooms[in_room]
                # linger in rooms with more people
                sleep(random.random() * (population)**2 / party)
                with lock(in_room):
                    rooms[in_room] -= 1
                    in_room = None
            else:
                # look for a room that's not locked by dean
                while not parties[target := random.randint(0, len(rooms)-1)].acquire(blocking=False):
                    pass
                with lock(target):
                    parties[target].release()
                    in_room = target
                    rooms[target] += 1
    
    @thread()
    def dean(lbl: str):
        waiting = None
        while True:
            sleep(0.5)
            out(lbl, f"start: {state()}")
            if waiting is not None:
                with lock(waiting):
                    if rooms[waiting] == 0:
                        out(lbl, f"broke up party in {waiting+1}")
                        parties[waiting].release()
                        waiting = None
                    else:
                        out(lbl, f"waiting on {waiting+1} to empty")
            else:
                target = random.randint(0, len(rooms)-1)
                with lock(target):
                    if rooms[target] == 0:
                        out(lbl, f"search {target+1}")
                    elif rooms[target] < party:
                        out(lbl, f"failed to enter {target+1}")
                    else:
                        out(lbl, f"breaking up party in room {target+1}")
                        waiting = target
                        parties[target].acquire()
            out(lbl, f"end: {state()}")
            
    for i in range(n):
        student(f"[student {i}]").start()
    
    dean("[dean]").start()
    
"""
7.4 The Senate Bus Problem

Passengers queue up at a bus stop. When a bus arrives, all
passengers waiting up to the bus' capacity board, with passengers
who arrive while the bus is here must wait for the next one.

Instead of solving this problem for a single stop, I made a cycle of stops
where passengers choose a random stop n to get off at stop n+1, and busses
that cycle through this route. This solution uses a layered turnstile approach,
where the lock used for incrementing the number of people at the stop is repurposed
for locking the stop against new people arriving. Inside this lock, a
turnstile is set up to allow riders up to the capacity of the bus. Riders
synchronize with the bus that they are getting on, and the bus confirms the
final list of riders going to the next stop. 

No global data is shared between threads other than the synchronization objects.
"""

def p7_4():
    n = 20
    busses = 2
    capacity = 5
    stops = [0] * 6
    turnstile = [Sem(0) for _ in range(len(stops))]
    boarding = [(Synchronizer(), Sem(0)) for _ in range(len(stops))]

    @thread()
    def passenger(lbl: str):
        stop = random.randrange(len(stops))
        while(True):
            sleep(1 + random.random() * 2)
            out(lbl, f"arrived at {stop}")
            with lock(stop):
                stops[stop] += 1
            out(lbl, f"waiting to board at {stop}")
            turnstile[stop].acquire()
            bus = boarding[stop][0].syncA(lbl) # start boarding
            out(lbl, f"boarded {bus} at {stop}")
            boarding[stop][1].release() # confirm boarded
            stop = random.randrange(len(stops))

    @thread()
    def bus(lbl: str):
        stop = random.randrange(len(stops))
        passengers = []
        while True:
            sleep(1 + random.random())
            
            with lock(stop):
                out(lbl, f"arrived at {stop}")
                if stops[stop] > 0:
                    out(lbl, f"now boarding at {stop}")
                    to_board = min(stops[stop], capacity)
                    stops[stop] -= to_board
                    turnstile[stop].release(to_board)
                    # wait for all passengers to get on
                    for _ in range(to_board):
                        passengers.append(boarding[stop][0].syncB(lbl))
                    for _ in range(to_board):
                        boarding[stop][1].acquire()
                    out(lbl, f"leaving {stop} with {len(passengers)} passengers: {' '.join(passengers)}")
                else:
                    out(lbl, f"leaving {stop} with no passengers")
            stop = (stop + 1) % len(stops)
            passengers = []

    for i in range(busses):
        bus(f"[bus {i}]").start()
    
    for i in range(n):
        passenger(f"[pass {i}]").start()


