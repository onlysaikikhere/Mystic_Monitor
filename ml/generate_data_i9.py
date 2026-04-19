#!/usr/bin/env python3
import os
import random
import pandas as pd
import subprocess
import sys

# Setup directories
data_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
os.makedirs(data_dir, exist_ok=True)
data_path = os.path.join(data_dir, "data.csv")

print("[*] Generating synthetic AI training data tailored for i9-14900hx...")

records = []
# An i9-14900hx typically has a huge volume of monotonic disk reads over an uptime cycle
disk_counter = 200_000_000_000 

# Generate 5000 rows of system state samples
for _ in range(5000):
    disk_counter += random.randint(1_000_000, 50_000_000)
    
    if random.random() < 0.75:
        # NORMAL STATE (Label: 0)
        # Even doing normal tasks, an i9-14900hx has high process counts but low overall CPU usage
        cpu = round(random.uniform(0.1, 12.0), 1)
        mem = round(random.uniform(8.0, 35.0), 1)
        procs = random.randint(450, 600)
        label = 0
    else:
        # STRESSED STATE (Label: 1)
        # CPU is pegged under heavy workload, temps rising, many processes spawned
        cpu = round(random.uniform(75.0, 100.0), 1)
        mem = round(random.uniform(40.0, 95.0), 1)
        procs = random.randint(550, 850)
        label = 1
        
    records.append([cpu, mem, procs, disk_counter, label])

# Save to CSV
df = pd.DataFrame(records, columns=["cpu", "memory", "processes", "disk", "label"])
df.to_csv(data_path, index=False)
print(f"[+] Saved {len(df)} simulated hardware records to {data_path}")

# Run the project's native training script
train_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "train.py")
print("\n[*] Invoking ml/train.py to compile the Random Forest model...")

try:
    subprocess.run([sys.executable, train_script], check=True)
    print("\n=========================================================")
    print("[SUCCESS] New Machine Learning Model Trained!")
    print("=========================================================")
    print("To install your new custom high-end model, run:")
    print("  sudo cp data/model.pkl /opt/mystic_monitor/")
    print("  sudo systemctl restart mystic-monitor.service")
    print("=========================================================")
except subprocess.CalledProcessError as e:
    print(f"[-] Training failed: {e}")
