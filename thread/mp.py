import time
import threading
import multiprocessing

start = time.perf_counter()

def do_some():
    time.sleep(3)


# p1 = multiprocessing.Process(target=do_some)
# p2 = multiprocessing.Process(target=do_some)

# p1.start()
# p2.start()

# p1.join()
# p2.join()

arr = []

for _ in range(10):
    p = multiprocessing.Process(target= do_some)
    p.start()
    arr.append(p)

for i in arr:
    i.join()


finish = time.perf_counter()

# print(round(finish-start))
print(finish-start)