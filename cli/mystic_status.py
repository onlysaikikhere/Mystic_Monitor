#!/usr/bin/env python3
import socket
import json
import os
import sys
import configparser

def get_config():
    config = configparser.ConfigParser()
    config['Daemon'] = {'socket_path': '/run/mystic/mystic.sock'}
    
    config_paths = ['/etc/mystic-monitor.conf', 'mystic-monitor.conf']
    read_files = config.read(config_paths)
    
    active_config = read_files[0] if read_files else "Built-in Defaults"
    socket_path = config['Daemon']['socket_path']
    return socket_path, active_config

def get_ml_state(socket_path):
    if not os.path.exists(socket_path):
        return None, "DAEMON OFFLINE (Socket not found)"
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect(socket_path)
            data = s.recv(4096)
            if data:
                return json.loads(data.decode('utf-8')), "OK"
            return None, "EMPTY RESPONSE"
    except Exception as e:
        return None, f"ERROR: {str(e)}"

def tail_audit_log(log_path='/var/log/mystic-anomalies.log', lines=10):
    if not os.path.exists(log_path):
        return ["Log file not found."]
    try:
        with open(log_path, 'r') as f:
            return f.readlines()[-lines:]
    except PermissionError:
        return ["Permission denied reading log."]
    except Exception as e:
        return [f"Error reading log: {e}"]

def main():
    print("=" * 50)
    print(" Mystic Monitor - System Status")
    print("=" * 50)

    socket_path, active_config = get_config()
    print(f"Config File: {active_config}")
    print(f"Socket Path: {socket_path}")

    state, error_msg = get_ml_state(socket_path)
    
    print("-" * 50)
    if state:
        print(f"Daemon Status    : Reachable (OK)")
        print(f"Current Status   : {state.get('status', 'N/A')}")
        print(f"Prediction Value : {state.get('prediction', 'N/A')}")
        print(f"Last Action      : {state.get('last_action', 'N/A')}")
    else:
        print(f"Daemon Status    : UNREACHABLE")
        print(f"Error Details    : {error_msg}")

    print("-" * 50)
    print("Recent Audit Log (last 5 lines):")
    for line in tail_audit_log(lines=5):
        print("  " + line.strip())
    print("=" * 50)

if __name__ == "__main__":
    main()
