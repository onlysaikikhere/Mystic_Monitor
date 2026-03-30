import pandas as pd
import matplotlib.pyplot as plt

try:
    data = pd.read_csv("data.csv")
    plt.plot(data["cpu"])
    plt.title("CPU Usage Over Time")
    plt.xlabel("Time Step (Seconds)")
    plt.ylabel("CPU %")
    plt.show()
except FileNotFoundError:
    print("Error: data.csv not found. Please run collector.py for a while to generate data.")
