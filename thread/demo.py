import time
import threading
import concurrent.futures

start = time.perf_counter()

def do_some(seconds):
    time.sleep(seconds)

# do_some()
# do_some()

# t1 = threading.Thread(target=do_some)
# t2 = threading.Thread(target=do_some)

# t1.start()
# t2.start()

# t1.join()
# t2.join()

threads = []

for _ in range(10):
    t = threading.Thread(target=do_some, args=[1.5])
    t.start()
    threads.append(t)


for i in threads:
    i.join()


finish = time.perf_counter()

# print(round(finish-start))
print(finish-start)