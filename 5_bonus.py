import random
from collections import deque
from threading import Semaphore as Sem
from time import sleep
from functools import reduce

from conc import thread, Synchronizer, lock, semaphores, Gate, Lightswitch


def out(label, msg, *a, **kw):
    print(f"{label}: {msg}", *a, **kw, flush=True)

"""
Bonus 1

At a high-profile art museum, in order to prevent theft,
there is a requirement that each room may have one door open at a time. 
- There are n rooms arranged in a line, with the first and second rooms joined
    by door 1, the second and third rooms by door 2, and so on. 
- A door will only open if the room ahead is empty.
- New rooms are added every year, so we must be able to anticipate operating an
    arbitrary number of rooms.
"""

"""
SOLUTION:

It would be unwieldy juggle interlocking mutexes by 
hand for a large number of rooms, nevermind arbitrary. Instead,
we can create a "cascading" synchronization structure that scales with
the number of rooms. We connect the lightswitches of the current room to
the door that enters the previous room, such that the previous room's door
cannot be opened as long as the exit has not been closed.

In addition, we can supply a transition function to perform actions
in between leaving the previous room and entering the next. We use this
to update the state of the museum in a mutually-exclusive way that respects
our system of transitions.
"""

class Cascade:
    def __init__(self, phases):
        self._phases = phases
        self._sems = [Sem(1) for _ in range(phases)]
        self._switches = [Lightswitch() for _ in range(phases)]

    def phase(self, phase: int, f=None):
        # lock phase we just exited
        if phase > 0:
            self._switches[phase-1].lock(self._sems[phase-1])

        # transition function, just before prior phase is unlocked    
        if f is not None: f()

        # unlock phase before last
        if phase > 1:
            self._switches[phase-2].unlock(self._sems[phase-2])
        
        # enter this phase
        self._sems[phase].acquire()
        self._sems[phase].release()


    def exit(self):
        self._switches[-2].unlock(self._sems[-2])

def pb_1():
    n_rooms = 7
    n_guests = 4
    n_waves = 5

    hall = Cascade(n_rooms)
    state_mutex = Sem(1)
    state = ["" for _ in range(n_rooms)]
    waves = [Sem(1), *(Sem(0) for _ in range(n_waves))]

    ready_count = [n_guests for _ in range(n_waves)]
    ready = [Sem(0) for _ in range(n_waves)]
    
    
    @thread()
    def guest(wave, num, phases: int):
        lbl = f'[{wave} {num}]'
        wave_num = wave
        wave = chr(ord('A')+w)

        def transition(i: int):
            state_mutex.acquire()
            if i > 0:
                state[i-1] = state[i-1].removesuffix(wave)
            if i < n_rooms:
                out(lbl, f"entered room {i}")
                state[i] = wave + state[i]
            else:
                out(lbl, f"exit")
            print(state)
            state_mutex.release()

        # ========================================    
        # For demonstration purposes, we coordinate guests
        # to visit in discrete waves to show how movement works.

        # Some guests who move quickly will jump ahead of others,
        # but you'll never see guests from different waves in the same room.

        # wait for this wave to be ready
        if wave_num > 0:
            waves[wave_num].acquire()
            waves[wave_num].release()

        hall.phase(0, lambda: transition(0))

        with lock(wave):
            ready_count[wave_num] -= 1
            if ready_count[wave_num] == 0:
                ready[wave_num].release(n_guests)
                
        ready[wave_num].acquire()
        hall.phase(1, lambda: transition(1))
        waves[wave_num+1].release()

        for i in range(2, phases):
            sleep(random.random())
            hall.phase(i, lambda: transition(i))
            if i > 2:
                pass
        hall.exit()
            
    for w in range(n_waves):
        for i in range(n_guests):
            guest(w, i, n_rooms).start()

# pb_1()

"""
Bonus 2

Consider the previous problem. The museum is now offering a super exclusive
VIP ticket: These visitors get to enjoy a solo experience, free of distractions.
Rather than interrupting the normal flow of business, the museum realizes
that it can simply prioritize entry to a room when a VIP shows up. Modify your
solution to accommodate VIPs.
- When a VIP checks in, they get the whole room to themselves.
- VIPs get separate rooms from each other.
"""

"""
SOLUTION:

Thanks to our Cascade abstraction, we can introduce the vip threads
with minimal modification to existing code.  As long as we ensure the
following threads only enter once a vip is in the second room, the cascade
ensures the constraints are respected.
"""

def pb_2():
    n_rooms = 7
    n_guests = 4
    n_waves = 5

    hall = Cascade(n_rooms)
    state_mutex = Sem(1)
    state = ["" for _ in range(n_rooms)]
    waves = [Sem(1), *(Sem(0) for _ in range(n_waves))]

    ready_count = [n_guests for _ in range(n_waves)]
    ready = [Sem(0) for _ in range(n_waves)]

    reservation = Sem(1)

    @thread()
    def vip(n, phases: int):
        lbl = f'[vip {n}]'
        wave = '*'

        def transition(i: int):
            state_mutex.acquire()
            if i > 0:
                state[i-1] = state[i-1].removesuffix(wave)
            if i < n_rooms:
                out(lbl, f"entered room {i}")
                state[i] = wave + state[i]
            else:
                out(lbl, f"exit")
            print(state)
            state_mutex.release()
        
        sleep(random.random())
        reservation.acquire()

        hall.phase(0, lambda: transition(0))
        hall.phase(1, lambda: transition(1))
        reservation.release()

        for i in range(2, phases):
            sleep(random.random())
            hall.phase(i, lambda: transition(i))
        hall.exit()
    
    
    @thread()
    def guest(wave, num, phases: int):
        lbl = f'[{wave} {num}]'
        wave_num = wave
        wave = chr(ord('A')+w)

        def transition(i: int):
            state_mutex.acquire()
            if i > 0:
                state[i-1] = state[i-1].removesuffix(wave)
            if i < n_rooms:
                out(lbl, f"entered room {i}")
                state[i] = wave + state[i]
            else:
                out(lbl, f"exit")
            print(state)
            state_mutex.release()

        if wave_num > 0:
            waves[wave_num].acquire()
            waves[wave_num].release()

        # let vips skip the line
        reservation.acquire()
        reservation.release()

        hall.phase(0, lambda: transition(0))

        with lock(wave):
            ready_count[wave_num] -= 1
            if ready_count[wave_num] == 0:
                ready[wave_num].release(n_guests)
                
        ready[wave_num].acquire()
        hall.phase(1, lambda: transition(1))
        waves[wave_num+1].release()

        for i in range(2, phases):
            sleep(random.random() * 0.2)
            hall.phase(i, lambda: transition(i))
        hall.exit()
            
    v = 0
    for w in range(n_waves):
        for i in range(n_guests):
            guest(w, i, n_rooms).start()
        reservation.acquire()
        reservation.release()

        if random.random() > 0.5:
            vip(v, n_rooms).start()
            v += 1

# pb_2