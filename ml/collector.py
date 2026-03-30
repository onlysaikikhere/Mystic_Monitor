import psutil
import time
import csv

with open("data.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["cpu", "memory", "processes", "disk", "label"])

    while True:
        cpu = psutil.cpu_percent()
        memory = psutil.virtual_memory().percent
        processes = len(psutil.pids())
        disk = psutil.disk_io_counters().read_bytes

        if cpu > 90 or memory > 85:
            label = 1
        else:
            label = 0

        writer.writerow([cpu, memory, processes, disk, label])
        print(f"CPU: {cpu}%, Memory: {memory}%, Label: {label}")

        time.sleep(5)
