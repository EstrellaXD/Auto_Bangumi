import multiprocessing
from module import app, api

if __name__ == "__main__":
    num_processes = 2
    processes = []
    p1 = multiprocessing.Process(target=app.run)
    p2 = multiprocessing.Process(target=api.run)
    process_list = [p1, p2]
    for p in process_list:
        p.start()
        processes.append(p)
    for p in processes:
        p.join()
