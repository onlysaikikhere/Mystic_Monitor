import psutil
import time
import pickle
import warnings

# Suppress feature name warnings
warnings.filterwarnings("ignore", category=UserWarning)

try:
    model = pickle.load(open("model.pkl", "rb"))
except FileNotFoundError:
    print("Error: model.pkl not found. Please run train.py first to train and save the model.")
    exit(1)

print("Starting performance degradation prediction monitoring...")

while True:
    cpu = psutil.cpu_percent()
    memory = psutil.virtual_memory().percent
    processes = len(psutil.pids())
    disk = psutil.disk_io_counters().read_bytes

    # Predict using the collected metrics
    prediction = model.predict([[cpu, memory, processes, disk]])

    if prediction[0] == 1:
        print("WARNING: Performance degradation likely")
    else:
        print("System normal")

    time.sleep(5)
