# Mystic Monitor

**Mystic Monitor** is a hybrid Machine Learning & Operating Systems project. It predicts performance degradation on Linux/Ubuntu systems by analyzing real-time kernel metrics and broadcasting them via an interactive, native terminal dashboard.

Unlike standard python scripts, Mystic Monitor is designed to be deeply integrated into the OS layer—utilizing Systemd daemons and global binary paths.

---

## 🏗️ Architecture

The project is split into two distinct lifecycle phases:

### 1. User-Space Training Pipeline
Offline scripts used to gather system telemetry data and train the Random Forest inference engine.
* `collector.py`: Gathers system metrics (`cpu`, `memory`, `processes`, `disk I/O`) into `data.csv`.
* `train.py`: Uses `scikit-learn` to build `model.pkl` mapping metrics to performance degradation likelihoods.

### 2. Kernel/System Inference Engine (The OS Integration)
The live deployment architecture integrated directly into Ubuntu.
* `mystic_daemon.py`: A `systemd` background service that constantly monitors the system kernel and runs `model.pkl` to compute system degradation probabilities.
* `/tmp/mystic_state.json`: A shared IPC socket file where the daemon continuously dumps the machine learning state.
* `mystic-top`: An interactive, Curses-based CLI dashboard that reads `psutil` load and interpolates it with the background daemon's live prediction status.

---

## 🚀 Quick Start Guide

### Step 1: Train the Engine (Optional, pre-trained model included)
To build a custom model based on your system's telemetry:
1. Run data collection until you have enough rows: `python3 collector.py`
2. Run training: `python3 train.py`
This generates your unique `model.pkl`.

### Step 2: OS Installation
Install the monitoring suite globally as root. This will install OS dependencies (`apt`), configure the daemon inside `/etc/systemd/`, copy the binaries into `/usr/local/bin/`, and install the `man` page.

```bash
chmod +x install.sh
sudo ./install.sh
```

### Step 3: Run the Dashboard
The application is now integrated globally into your OS environment. From anywhere in your terminal, you can interact with it just like traditional Linux utilities.

```bash
# Launch the ML-Enhanced TOP Interactive Dashboard
mystic-top

# Open the User Manual pages
man mystic-top
```
