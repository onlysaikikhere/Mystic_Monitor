# Mystic Monitor

**Mystic Monitor** is a hybrid Machine Learning & Operating Systems project. It acts as an **Active Server Mitigation Engine**, predicting system performance degradation on Linux/Ubuntu via real-time kernel metrics and actively intervening (via `kill` and `renice` system calls) to prevent downtime. It natively broadcasts system state through an interactive, `htop`-style terminal dashboard.

Unlike standard standalone python scripts, Mystic Monitor is architected to integrate deeply into the OS layer—utilizing Systemd daemons, Unix Domain Sockets, `/etc/` configurations, and global executable paths.

---

## 🏗️ System Architecture

The project is split into three distinct subsystems that cleanly separate user-space offline tasks from kernel-space live monitoring.

### 1. The Inference Engine (`mystic_daemon.py` & Systemd)
The core intelligence of the application runs as a continuous, headless Systemd background service.
* Constantly reads live OS stats (CPU, Memory, Process Counts, Disk I/O) via `psutil`.
* Feeds data into a Pre-trained Scikit-Learn **Random Forest Classifier** (`model.pkl`) every 5 seconds.
* Instead of inefficiently writing to the hard disk, it hosts a high-speed **Unix Domain Socket** (`/tmp/mystic.sock`) to immediately stream JSON payloads to any front-end client entirely in-memory.

### 2. The Active Mitigation Escalation Matrix
The daemon isn't just an observer; it's an automated System Administrator. If the ML model warns of imminent degradation:
1. **The Whitelist Check:** The daemon examines the highest CPU-consuming process against a strict `/etc/` whitelist (e.g., `sshd`, `systemd`). If the process is a critical system service, it is safely ignored.
2. **The Auto-Reaper with 15-Second Grace Period (`SIGKILL`):** If degradation reaches critical exhaustion (e.g., >95% CPU), the daemon logs the threat and starts a 15-second countdown. During this grace period, it actively throttles the process (`renice 19`). If the process fails to stabilize below the threshold after 15 seconds, the daemon fires a fatal `SIGKILL` directly via the OS to instantly destroy the threat.
3. **OS Process Throttling (`renice`):** If a rogue script is causing moderate degradation (e.g., >40% CPU) but hasn't reached critical exhaustion, the daemon dips into the Linux scheduler and applies a `+19` nice value, pushing the task to the absolute lowest CPU priority queue so standard web traffic can breathe freely.
4. **Historical Logging:** Every mitigation action is permanently journaled with timestamps into `/var/log/mystic-anomalies.log`.

### 3. The Interactive Dashboard (`mystic_top.py`)
A fast, `curses`-based frontend UI explicitly designed to mimic legacy tools like `top` and `htop`.
* Parses data dynamically from the `/tmp/mystic.sock` in real-time (500ms refresh rate).
* Includes stunning, dynamically-colored ASCII progress bars for CPU, Mem, and Swap tracking.
* Boldly highlights anomalous "Culprit" processes causing degradation dynamically across the UI grid.
* Surfaces real-time "DAEMON LOG" events whenever the Auto-Reaper acts against the system.

*(Note: The `collector.py` and `train.py` scripts act as the Offline Training Pipeline to generate custom `model.pkl` inference objects for your specific machine telemetry.)*

---

## ⚙️ OS Configuration (`/etc/mystic-monitor.conf`)

By design, System Administrators should never have to hardcode Python scripts.
All aggression thresholds, ML polling loop speeds, and Whitelisted binaries are strictly controlled inside a standard `.ini` configuration file that the installer securely places into `/etc/mystic-monitor.conf`.

---

## 🚀 Quick Start Guide

### Step 1: Global OS Installation
Install the monitoring suite globally as root. This will install native OS dependencies (`apt`), configure the daemon inside `/etc/systemd/system/`, copy the binaries into `/usr/local/bin/`, and provision the `man` manual pages.

```bash
chmod +x install.sh
sudo ./install.sh
```

### Step 2: Use the Dashboard
The application is now integrated universally into your OS environment. From anywhere in your terminal, interact with it like a native Linux utility.

```bash
# Launch the ML-Enhanced TOP Interactive Dashboard
mystic-top

# Open the User Manual pages
man mystic-top
```

### Step 3: Triggering the Auto-Reaper (Stress Test!)
Want to see the Machine Learning engine actively defend your server live? Open two terminal windows side-by-side:

**Terminal 1:**
```bash
mystic-top
```

**Terminal 2:**
```bash
stress --cpu 32
```
*The Machine learning engine will immediately predict the massive incoming CPU spike, correctly identify the dummy payload, and dynamically throttle the process while starting a 15-second grace period. If the load persists, it physically executes an OS `SIGKILL` to save your server layout—logging the countdown and final killshot cleanly across your `mystic-top` UI!*
