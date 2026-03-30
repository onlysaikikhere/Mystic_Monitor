#!/usr/bin/env python3
import psutil
import time
import pickle
import warnings
import json
import os
import sys
import socket
import socketserver
import threading
import configparser
import logging
import signal

warnings.filterwarnings("ignore", category=UserWarning)

# Setup Configparser Native Fallbacks
config = configparser.ConfigParser()
config['Daemon'] = {
    'poll_interval_seconds': '5',
    'model_path': os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "model.pkl"),
    'socket_path': '/tmp/mystic.sock'
}
config['ActiveMitigation'] = {
    'enable_throttling': 'true',
    'throttle_cpu_threshold': '40.0',
    'enable_reaper': 'true',
    'reaper_cpu_threshold': '95.0',
    'protected_processes': 'systemd,sshd,bash,mystic_top,tmux,python3,init',
    'audit_log_path': '/var/log/mystic-anomalies.log'
}

# Pull from /etc/ over local
config.read(['/etc/mystic-monitor.conf', 'mystic-monitor.conf'])

POLL_INTERVAL = int(config['Daemon']['poll_interval_seconds'])
MODEL_PATH = config['Daemon']['model_path']
SOCKET_PATH = config['Daemon']['socket_path']
LOG_PATH = config['ActiveMitigation']['audit_log_path']

# Setup Historical Audit Logging
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format='%(asctime)s - [ActiveMitigation] - %(levelname)s - %(message)s'
)

# Thread-safe global state for the socket server to read from
app_state = {
    "status": "INITIALIZING...",
    "prediction": -1,
    "timestamp": 0,
    "last_action": "None",
    "metrics": {}
}
state_lock = threading.Lock()
reaper_tracking = {}

class MysticSocketHandler(socketserver.StreamRequestHandler):
    def handle(self):
        try:
            with state_lock:
                payload = json.dumps(app_state).encode('utf-8')
            self.wfile.write(payload)
        except Exception as e:
            print(f"Socket Handler error: {e}", file=sys.stderr)

def start_socket_server():
    if os.path.exists(SOCKET_PATH):
        try:
            os.unlink(SOCKET_PATH)
        except OSError:
            pass
    server = socketserver.UnixStreamServer(SOCKET_PATH, MysticSocketHandler)
    os.chmod(SOCKET_PATH, 0o666)
    server.serve_forever()

def mitigate_threat(cpu_percent, memory_percent):
    """
    Identifies the top culprit process and applies the OS Escalation Matrix
    (Ignore Whitelist -> Throttle(renice) -> Kill(SIGKILL)).
    """
    procs = list(psutil.process_iter(['pid', 'name', 'cpu_percent', 'cmdline']))
    procs.sort(key=lambda x: x.info['cpu_percent'] or 0.0, reverse=True)
    if not procs: return "None"
    
    culprit = procs[0].info
    pid = culprit['pid']
    name = str(culprit['name'] or 'unknown')
    cmdline = ' '.join(culprit['cmdline'] or [])
    proc_cpu = culprit['cpu_percent'] or 0.0
    
    # Check Whitelist Safety Protocol
    whitelist = [wp.strip() for wp in config['ActiveMitigation']['protected_processes'].split(',')]
    for wp in whitelist:
        if wp and (wp in name or wp in cmdline):
            logging.info(f"IGNORED: Process PID {pid} ({name}) is protected by OS whitelist.")
            return f"WHITELISTED: {name} (Safe)"

    try:
        reaper_threshold = config.getfloat('ActiveMitigation', 'reaper_cpu_threshold')
        
        # Cleanup old tracking entries
        current_pids = {p.info['pid']: p.info['cpu_percent'] or 0.0 for p in procs}
        for t_pid in list(reaper_tracking.keys()):
            if t_pid not in current_pids or current_pids[t_pid] <= reaper_threshold:
                del reaper_tracking[t_pid]

        # 1. Auto-Reaper (Over threshold)
        if config.getboolean('ActiveMitigation', 'enable_reaper') and proc_cpu > reaper_threshold:
            if pid not in reaper_tracking:
                reaper_tracking[pid] = time.time()
                
            if time.time() - reaper_tracking[pid] >= 15:
                os.kill(pid, signal.SIGKILL)
                action_msg = f"KILLED (SIGKILL) '{name}' PID {pid} (CPU: {proc_cpu}%) after 15s"
                logging.critical(action_msg)
                if pid in reaper_tracking:
                    del reaper_tracking[pid]
                return action_msg
            else:
                remaining = int(15 - (time.time() - reaper_tracking[pid]))
                action_msg = f"GRACE PENDING: '{name}' {remaining}s until SIGKILL"
                
                # Apply throttle during grace period if enabled
                if config.getboolean('ActiveMitigation', 'enable_throttling'):
                    psutil.Process(pid).nice(19)
                return action_msg
                
        # 2. Dynamic OS Scheduler Throttle (Over 40%)
        if config.getboolean('ActiveMitigation', 'enable_throttling') and proc_cpu > config.getfloat('ActiveMitigation', 'throttle_cpu_threshold'):
            psutil.Process(pid).nice(19) # Push to absolute lowest OS priority scheduling queue
            action_msg = f"THROTTLED (renice 19) '{name}' PID {pid} (CPU: {proc_cpu}%)"
            logging.warning(action_msg)
            return action_msg
            
        return "None"
        
    except Exception as e:
        err_msg = f"MITIGATION FAILED against PID {pid}: {str(e)}"
        logging.error(err_msg)
        return err_msg

def main():
    print(f"Starting Mystic Monitor Active Mitigation Daemon...")
    try:
        with open(MODEL_PATH, "rb") as f:
            model = pickle.load(f)
    except FileNotFoundError:
        print(f"CRITICAL: {MODEL_PATH} not found.", file=sys.stderr)
        sys.exit(1)

    threading.Thread(target=start_socket_server, daemon=True).start()

    while True:
        try:
            cpu = psutil.cpu_percent()
            memory = psutil.virtual_memory().percent
            processes = len(psutil.pids())
            disk = psutil.disk_io_counters().read_bytes

            prediction = int(model.predict([[cpu, memory, processes, disk]])[0])
            
            # Fire Mitigation Subsystem if ML degrades
            mitigation_taken = "None"
            if prediction == 1:
                mitigation_taken = mitigate_threat(cpu, memory)

            with state_lock:
                app_state["timestamp"] = time.time()
                app_state["metrics"] = {"cpu": cpu, "memory": memory, "processes": processes, "disk_io": disk}
                app_state["status"] = "EMERGENCY: DEGRADATION DETECTED" if prediction == 1 else "NORMAL"
                app_state["prediction"] = prediction
                if mitigation_taken != "None":
                    app_state["last_action"] = mitigation_taken

        except Exception as e:
            print(f"ERROR calculating state: {e}", file=sys.stderr)

        time.sleep(POLL_INTERVAL)

if __name__ == "__main__":
    main()
