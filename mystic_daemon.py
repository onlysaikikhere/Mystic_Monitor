#!/usr/bin/env python3
import psutil
import time
import pickle
import warnings
import json
import os
import sys

# Suppress warnings from scikit-learn
warnings.filterwarnings("ignore", category=UserWarning)

# We will load the model from the directory where the daemon runs
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "model.pkl")
STATE_FILE = "/tmp/mystic_state.json"
TMP_STATE_FILE = "/tmp/mystic_state.json.tmp"

def main():
    print(f"Starting Mystic Monitor Daemon...")
    try:
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
        print(f"Loaded model successfully from {MODEL_PATH}")
    except FileNotFoundError:
        print(f"CRITICAL: {MODEL_PATH} not found. Daemon cannot start.", file=sys.stderr)
        sys.exit(1)

    while True:
        try:
            # Collect metrics exactly as trained
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            processes = len(psutil.pids())
            disk = psutil.disk_io_counters().read_bytes

            # Run prediction
            prediction = int(model.predict([[cpu, memory, processes, disk]])[0])

            # Prepare state payload
            state = {
                "timestamp": time.time(),
                "metrics": {
                    "cpu": cpu,
                    "memory": memory,
                    "processes": processes,
                    "disk_io": disk
                },
                "status": "WARNING: DEGRADATION EXPECTED" if prediction == 1 else "NORMAL",
                "prediction": prediction
            }

            # Atomic write to state file so the client never reads partial data
            with open(TMP_STATE_FILE, "w") as f:
                json.dump(state, f)
            os.rename(TMP_STATE_FILE, STATE_FILE)

            # Optional: log degradation directly to OS journal (systemd handles stdout)
            if prediction == 1:
                print(f"WARNING: Performance degradation detected: CPU: {cpu}%, Mem: {memory}%, Proc: {processes}")

        except Exception as e:
            print(f"ERROR calculating state: {e}", file=sys.stderr)

        time.sleep(5)

if __name__ == "__main__":
    main()
