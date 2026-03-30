#!/usr/bin/env python3
import time
import math
import sys
import multiprocessing

def heavy_computation():
    print(f"[{multiprocessing.current_process().name}] Started malicious CPU loop. My PID is {os.getpid()}...")
    while True:
        # Endless floating point math specifically designed to consume CPU cycles
        [math.sqrt(i) for i in range(1000000)]

if __name__ == "__main__":
    import os
    print(f"Warning: Starting Rogue CPU Stress Test (PID: {os.getpid()})")
    print("If Mystic Monitor is running properly, the daemon ML should notice the degradation and terminate this process instantly.")
    
    # Spawn multiple processes to truly spike the overall system
    cores_to_burn = max(1, multiprocessing.cpu_count() - 1)
    print(f"Spawning {cores_to_burn} child processes. Hold on tight...")
    
    processes = []
    for _ in range(cores_to_burn):
        p = multiprocessing.Process(target=heavy_computation)
        p.start()
        processes.append(p)
        
    try:
        for p in processes:
            p.join()
    except KeyboardInterrupt:
        print("Test stopped manually.")
        for p in processes:
            p.terminate()
        sys.exit(0)
