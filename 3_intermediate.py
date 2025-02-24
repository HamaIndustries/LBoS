import random
from collections import deque
from threading import Semaphore as Sem
from time import sleep
from functools import reduce

from conc import thread, Synchronizer, lock, semaphores

"""
5.4 Hilzer's Barbershop
"""

def p5_4():
    n_customers = 100
    n_barbers = 3
    sofa_size = 4
    shop_size = 20
    customers_left = n_customers

    sofa = deque()

    sofa_spots = Sem(sofa_size)
    shop_spots = Sem(shop_size)
    
    haircut_ready = Sem(0)
    haircuts = Synchronizer()

    register = Synchronizer()
    paid = Sem(0)

    @thread()
    def customer(label: str):
        def out(s): print(f"{label}: {s}")
        
        shop_spots.acquire()
        out("enterShop")

        sofa_spots.acquire()
        with lock("sofa"):
            out("sitOnSofa")
            sofa.append(label)
        while True:
            # spinlock to get the correct queue member
            # barber signals when ready
            haircut_ready.acquire()
            with lock("sofa"):
                if sofa[0] == label:
                    sofa.popleft()
                    break
            haircut_ready.release()
        
        barber = haircuts.syncA(label)
        sofa_spots.release()
        out(f"getHairCut by {barber}")

        registrar = register.syncA(label)
        out(f"pay {registrar}")
        with lock("customers_left"):
            nonlocal customers_left
            customers_left -= 1
        paid.release()
        shop_spots.release()
        
    @thread()
    def barber(label: str):
        def out(s): print(f"{label}: {s}")
        while True:
            with lock("customers_left"):
                if customers_left < 1:
                    out("done")
                    return
            haircut_ready.release()
            client = haircuts.syncB(label)
            out(f"cutHair for {client}")

            with lock("register"):
                payer = register.syncB(label)
                paid.acquire()
                out(f"acceptPayment {payer}")


    for i in range(n_customers):
        customer(f"[cust {i}]").start()
    
    for i in range(n_barbers):
        barber(f"[barb {i}]").start()

"""
5.6 Building H20

We want to synchronize molecules so that a specified number can pass through
the barrier before the next batch goes through. Rather than maintaining a
data structure to queue up the atoms, we only have semaphores for each
kind of atom. Once the last atom is added, the molecule is completed and
all semaphores are signalled for the next batch.

This functionality is generalized to any recipe, not just h20.
"""
def p5_4():
    h20_recipe = {
        "hydrogen": 2,
        "oxygen": 1
    }

    def make_queue(recipe: dict[str, int]):
        return [0, {kind: Sem(recipe[kind]) for kind in recipe}]

    @thread()
    def atom(label: str, kind: str, recipe: dict[str, int], queue: list[int, dict[str, Sem]]):
        sleep(random.random())
        total = sum(recipe[k] for k in recipe)

        queue[1][kind].acquire()
        print(label, flush=True)
        with lock("queue"):
            queue[0] += 1
            if queue[0] == total:
                queue[0] = 0
                print("----------------", flush=True)
                for k in recipe:
                    queue[1][k].release(recipe[k])

    n_atoms = 20
    q = make_queue(h20_recipe)
    for kind in h20_recipe:
        for i in range(h20_recipe[kind] * n_atoms):
            atom(f"[{kind} {i}]", kind, h20_recipe, q).start()

"""
5.8 Rollercoaster

Super basic, but gave me the idea of a function `semaphores` for
mass instantiation of sems.
"""

def p5_8():
    C = 5
    n = 100

    loaded, boarded, unboard = semaphores(0, 0, 0)

    def out(label, msg, *a, **kw):
        print(f"{label}: {msg}", *a, **kw)


    @thread()
    def passenger(lbl: str):
        sleep(random.random())
        loaded.acquire()
        # board
        out(lbl, "board")
        boarded.release()
        # unboard
        unboard.acquire()
        out(lbl, "unboard")
        

    @thread()
    def car(lbl: str):
        served = 0
        while served < n:
            # load
            out(lbl, "load")
            loaded.release(C)

            for _ in range(C):
                boarded.acquire()
            
            out(lbl, "run")

            out(lbl, "unboard")
            unboard.release(C)

            served += C
    
    car("[car]").start()
    for i in range(n):
        passenger(f"[passenger {i}]").start()

