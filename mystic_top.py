#!/usr/bin/env python3
import curses
import psutil
import time
import json
import os
import getpass
import datetime
import socket
import configparser

config = configparser.ConfigParser()
config['Daemon'] = {'socket_path': '/tmp/mystic.sock'}
config.read(['/etc/mystic-monitor.conf', 'mystic-monitor.conf'])
SOCKET_PATH = config['Daemon']['socket_path']

def get_ml_state():
    try:
        if not os.path.exists(SOCKET_PATH):
            return {"status": "DAEMON OFFLINE", "prediction": -1, "last_action": "None"}
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(0.5) 
            s.connect(SOCKET_PATH)
            data = s.recv(4096)
            if data:
                return json.loads(data.decode('utf-8'))
        return {"status": "DAEMON ERROR", "prediction": -1, "last_action": "None"}
    except Exception as e:
        return {"status": f"ERROR: {str(e)[:15]}", "prediction": -1, "last_action": "None"}

def get_uptime():
    uptime_seconds = time.time() - psutil.boot_time()
    return datetime.timedelta(seconds=int(uptime_seconds))

def get_process_list():
    procs = []
    for p in psutil.process_iter(['pid', 'username', 'cpu_percent', 'memory_percent', 'name', 'cmdline']):
        try: procs.append(p.info)
        except: pass
    procs.sort(key=lambda x: x['cpu_percent'] or 0.0, reverse=True)
    return procs

def draw_ascii_bar(percent, width=30):
    if percent > 100: percent = 100.0
    filled_blocks = int((percent / 100.0) * width)
    empty_blocks = width - filled_blocks
    pipe_str = "|" * filled_blocks
    space_str = " " * empty_blocks
    perc_str = f"{percent:.1f}%"
    bar_content = pipe_str + space_str
    if len(bar_content) >= len(perc_str) + 2:
        bar_content = bar_content[:-len(perc_str)] + perc_str
    return f"[{bar_content}]"

def draw_interface(stdscr):
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_WHITE, -1)   
    curses.init_pair(2, curses.COLOR_GREEN, -1)   
    curses.init_pair(3, curses.COLOR_RED, -1)     
    curses.init_pair(4, curses.COLOR_BLACK, curses.COLOR_WHITE) 
    curses.init_pair(5, curses.COLOR_CYAN, -1)    
    curses.init_pair(6, curses.COLOR_YELLOW, -1)  

    stdscr.nodelay(True)
    stdscr.timeout(500)

    while True:
        try:
            max_y, max_x = stdscr.getmaxyx()
            stdscr.clear()

            ml_state = get_ml_state()
            cpu_percent = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            swap = psutil.swap_memory()
            load1, load5, load15 = os.getloadavg() if hasattr(os, 'getloadavg') else (0,0,0)
            procs_list = get_process_list()

            # Row 1: Top Bar
            top_bar = f" Mystic Top - Uptime: {get_uptime()} - Load Avg: {load1:.2f}, {load5:.2f}, {load15:.2f} "
            stdscr.attron(curses.color_pair(4))
            stdscr.addstr(0, 0, top_bar[:max_x].ljust(max_x))
            stdscr.attroff(curses.color_pair(4))

            # Row 2: ML Banner
            pred_val = ml_state.get("prediction", -1)
            pred_status = ml_state.get("status", "UNKNOWN")
            banner_color = curses.color_pair(2) if pred_val == 0 else curses.color_pair(3)
            
            top_process = procs_list[0] if procs_list else {}
            culprit_name = str(top_process.get('name', 'unknown'))
            culprit_cpu = top_process.get('cpu_percent', 0.0)
            
            if pred_val == 1 and culprit_cpu > 15.0:
                pred_status = f"{pred_status} [ Culprit: {culprit_name} ]"
            if pred_val == -1: banner_color = curses.color_pair(1)

            banner_text = f" ML PREDICTION: [ {pred_status} ] "
            col_x = max(0, (max_x - len(banner_text)) // 2)
            stdscr.attron(curses.color_pair(4))
            stdscr.addstr(1, 0, " " * max_x)
            stdscr.attroff(curses.color_pair(4))
            stdscr.attron(banner_color | curses.A_BOLD)
            stdscr.addstr(1, col_x, banner_text[:max_x])
            stdscr.attroff(banner_color | curses.A_BOLD)

            # Row 3: Daemon Action Mitigation Log
            last_action = ml_state.get("last_action", "None")
            action_col = max(0, (max_x - len(last_action) - 13) // 2)
            if last_action != "None":
                stdscr.addstr(2, action_col, f"DAEMON LOG > ", curses.color_pair(6) | curses.A_BOLD)
                stdscr.addstr(2, action_col + 13, f"{last_action}", curses.color_pair(1))

            # Rows 4-6: Graphical Resource Bars
            row = 4
            bar_width = min(40, max_x - 15)
            
            cpu_color = curses.color_pair(3) if cpu_percent > 85.0 else (curses.color_pair(6) if cpu_percent > 60.0 else curses.color_pair(5))
            stdscr.addstr(row, 2, "CPU ", curses.color_pair(1) | curses.A_BOLD)
            stdscr.addstr(row, 6, draw_ascii_bar(cpu_percent, bar_width), cpu_color)
            if max_x > bar_width + 12:
                stdscr.addstr(row, bar_width + 10, f"Tasks: {len(procs_list)} total", curses.color_pair(1))
            row += 1

            mem_color = curses.color_pair(3) if mem.percent > 85.0 else (curses.color_pair(6) if mem.percent > 60.0 else curses.color_pair(5))
            stdscr.addstr(row, 2, "Mem ", curses.color_pair(1) | curses.A_BOLD)
            stdscr.addstr(row, 6, draw_ascii_bar(mem.percent, bar_width), mem_color)
            if max_x > bar_width + 12:
                stdscr.addstr(row, bar_width + 10, f"Used: {mem.used//(1024**2)}M / {mem.total//(1024**2)}M", curses.color_pair(1))
            row += 1

            swap_color = curses.color_pair(3) if swap.percent > 85.0 else (curses.color_pair(6) if swap.percent > 60.0 else curses.color_pair(5))
            stdscr.addstr(row, 2, "Swp ", curses.color_pair(1) | curses.A_BOLD)
            stdscr.addstr(row, 6, draw_ascii_bar(swap.percent, bar_width), swap_color)
            if max_x > bar_width + 12:
                stdscr.addstr(row, bar_width + 10, f"Used: {swap.used//(1024**2)}M / {swap.total//(1024**2)}M", curses.color_pair(1))
            row += 2

            # Row 7: Process Header
            proc_hdr = f"{'PID':>7} {'USER':<12} {'%CPU':>6} {'%MEM':>6} {'COMMAND'}"
            stdscr.attron(curses.color_pair(4))
            stdscr.addstr(row, 0, proc_hdr[:max_x].ljust(max_x))
            stdscr.attroff(curses.color_pair(4))
            row += 1

            # Process List Loop
            for i, p in enumerate(procs_list):
                if row >= max_y - 1: break
                pid = p.get('pid', '')
                user = (str(p.get('username')) or '')[:11]
                cpu = p.get('cpu_percent') or 0.0
                mem_p = p.get('memory_percent') or 0.0
                name = str(p.get('name')) or ''
                
                line = f"{pid:>7} {user:<12} {cpu:>6.1f} {mem_p:>6.1f} {name}"
                
                is_culprit = False
                if pred_val == 1:
                    if i == 0 and (cpu > 15.0 or mem_p > 20.0): is_culprit = True
                    elif cpu > 40.0 or mem_p > 50.0: is_culprit = True
                
                if is_culprit:
                    stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
                    stdscr.addstr(row, 0, line[:max_x])
                    stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)
                else:
                    stdscr.addstr(row, 0, line[:max_x])
                row += 1

            stdscr.refresh()
            ch = stdscr.getch()
            if ch == ord('q') or ch == ord('Q'): break
        except curses.error: pass 

def main():
    try: curses.wrapper(draw_interface)
    except KeyboardInterrupt: pass

if __name__ == "__main__": main()
