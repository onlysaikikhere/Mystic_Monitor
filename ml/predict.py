import os
import psutil
import time
import pickle
import warnings

# Suppress feature name warnings
warnings.filterwarnings("ignore", category=UserWarning)

try:
    model_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "model.pkl")
    model = pickle.load(open(model_path, "rb"))
except FileNotFoundError:
    print(f"Error: {model_path} not found. Please run train.py first to train and save the model.")
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
