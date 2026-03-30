#!/usr/bin/env python3
import curses
import psutil
import time
import json
import os
import getpass
import datetime

STATE_FILE = "/tmp/mystic_state.json"

def get_ml_state():
    try:
        if os.path.exists(STATE_FILE):
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        return {"status": "UNKNOWN (Daemon Offline)", "prediction": -1, "timestamp": 0}
    except Exception:
        return {"status": "ERROR (Reading Daemon)", "prediction": -1, "timestamp": 0}

def get_uptime():
    boot_time = psutil.boot_time()
    uptime_seconds = time.time() - boot_time
    return datetime.timedelta(seconds=int(uptime_seconds))

def get_process_list():
    procs = []
    for p in psutil.process_iter(['pid', 'username', 'cpu_percent', 'memory_percent', 'name', 'cmdline']):
        try:
            info = p.info
            procs.append(info)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    # Sort by cpu descending
    procs.sort(key=lambda x: x['cpu_percent'] or 0.0, reverse=True)
    return procs

def draw_interface(stdscr):
    # Setup Colors
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)   # Normal
    curses.init_pair(2, curses.COLOR_GREEN, -1)   # OK / Normal State
    curses.init_pair(3, curses.COLOR_RED, -1)     # Critical / Degradation State
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE) # Header Bar
    curses.init_pair(5, curses.COLOR_CYAN, -1)    # Keys / Info

    stdscr.nodelay(True) # Non-blocking input
    stdscr.timeout(500) # 500 ms refresh rate

    while True:
        try:
            max_y, max_x = stdscr.getmaxyx()
            stdscr.clear()

            # --- Gather System Data ---
            ml_state = get_ml_state()
            cpu_percent = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            load1, load5, load15 = os.getloadavg() if hasattr(os, 'getloadavg') else (0,0,0)
            uptime = get_uptime()
            procs_list = get_process_list()

            # --- Row 1: Top Bar & ML Banner ---
            top_bar = f" Mystic Top - Uptime: {uptime} - Load Avg: {load1:.2f}, {load5:.2f}, {load15:.2f} "
            stdscr.attron(curses.color_pair(4))
            stdscr.addstr(0, 0, top_bar[:max_x].ljust(max_x))
            stdscr.attroff(curses.color_pair(4))

            # --- Row 2: ML Prediction Engine Status ---
            pred_val = ml_state["prediction"]
            pred_status = ml_state["status"]
            banner_color = curses.color_pair(2) if pred_val == 0 else curses.color_pair(3)
            if pred_val == -1: banner_color = curses.color_pair(1)

            daemon_age = int(time.time() - ml_state.get("timestamp", 0))
            if daemon_age > 15 and pred_val != -1: # Stale data
                pred_status += " (STALE - DAEMON DEAD?)"
                banner_color = curses.color_pair(3)

            banner_text = f" ML PREDICTION: [ {pred_status} ] "
            col_x = max(0, (max_x - len(banner_text)) // 2)
            stdscr.attron(curses.color_pair(4))
            stdscr.addstr(1, 0, " " * max_x)
            stdscr.attroff(curses.color_pair(4))
            stdscr.attron(banner_color | curses.A_BOLD)
            stdscr.addstr(1, col_x, banner_text[:max_x])
            stdscr.attroff(banner_color | curses.A_BOLD)

            # --- Row 3 & 4: General Stats ---
            row = 3
            stdscr.addstr(row, 2, f"CPU [%]: {cpu_percent:5.1f}% ", curses.color_pair(1))
            total_tasks = len(procs_list)
            stdscr.addstr(row, 25, f"Tasks: {total_tasks} total", curses.color_pair(1))
            row += 1

            stdscr.addstr(row, 2, f"Mem [%]: {mem.percent:5.1f}% ", curses.color_pair(1))
            stdscr.addstr(row, 25, f"Used: {mem.used//(1024**2)}M / {mem.total//(1024**2)}M", curses.color_pair(1))
            row += 1

            stdscr.addstr(row, 2, f"Swp [%]: {swap.percent:5.1f}% ", curses.color_pair(1))
            stdscr.addstr(row, 25, f"Used: {swap.used//(1024**2)}M / {swap.total//(1024**2)}M", curses.color_pair(1))
            row += 2

            # --- Row 5: Process Header ---
            proc_hdr = f"{'PID':>7} {'USER':<12} {'%CPU':>6} {'%MEM':>6} {'COMMAND'}"
            stdscr.attron(curses.color_pair(4))
            stdscr.addstr(row, 0, proc_hdr[:max_x].ljust(max_x))
            stdscr.attroff(curses.color_pair(4))
            row += 1

            # --- Process List Loop ---
            for p in procs_list:
                if row >= max_y - 1:
                    break
                pid = p.get('pid', '')
                user = (str(p.get('username')) or '')[:11]
                cpu = p.get('cpu_percent') or 0.0
                mem_p = p.get('memory_percent') or 0.0
                name = str(p.get('name')) or ''
                
                line = f"{pid:>7} {user:<12} {cpu:>6.1f} {mem_p:>6.1f} {name}"
                stdscr.addstr(row, 0, line[:max_x])
                row += 1

            stdscr.refresh()

            # Handle user input gracefully
            ch = stdscr.getch()
            if ch == ord('q') or ch == ord('Q'):
                break

        except curses.error:
            pass # Handle window too small naturally by skipping rest of draw

def main():
    try:
        curses.wrapper(draw_interface)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
