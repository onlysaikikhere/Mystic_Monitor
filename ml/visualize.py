import os
import pandas as pd
import matplotlib.pyplot as plt

try:
    data_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "data.csv")
    data = pd.read_csv(data_path)
    plt.plot(data["cpu"])
    plt.title("CPU Usage Over Time")
    plt.xlabel("Time Step (Seconds)")
    plt.ylabel("CPU %")
    plt.show()
except FileNotFoundError:
    print(f"Error: {data_path} not found. Please run collector.py for a while to generate data.")
