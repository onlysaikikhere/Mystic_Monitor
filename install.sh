#!/bin/bash
set -e

echo "Starting Mystic Monitor OS Integration..."

# 1. Require root
if [ "$EUID" -ne 0 ]; then
  echo "Please run this installer with sudo:"
  echo "sudo ./install.sh"
  exit 1
fi

# 2. Install System Dependencies
echo "[1/5] Installing required OS python packages..."
apt-get update -qq
apt-get install -y python3-psutil python3-sklearn python3-pandas

# 3. Setup Background Daemon
echo "[2/5] Setting up background daemon in /opt/mystic_monitor..."
mkdir -p /opt/mystic_monitor
cp mystic_daemon.py /opt/mystic_monitor/
cp model.pkl /opt/mystic_monitor/
chmod +x /opt/mystic_monitor/mystic_daemon.py

# 4. Setup CLI Client (The 'top' interface)
echo "[3/5] Installing global CLI tool 'mystic-top'..."
cp mystic_top.py /usr/local/bin/mystic-top
chmod +x /usr/local/bin/mystic-top

# 5. Install standard Man Page
echo "[4/5] Installing OS manual page..."
mkdir -p /usr/local/share/man/man1
gzip -c mystic-top.1 > /usr/local/share/man/man1/mystic-top.1.gz
mandb -q || true

# 6. Systemd Service Integration
echo "[5/5] Integrating with systemd (Service Manager)..."
if command -v systemctl >/dev/null 2>&1 && systemctl is-system-running >/dev/null 2>&1; then
    cp mystic-monitor.service /etc/systemd/system/
    systemctl daemon-reload
    systemctl enable mystic-monitor.service
    systemctl restart mystic-monitor.service
    echo "Service enabled and running!"
else
    echo ""
    echo "WARNING: systemd is not active in this WSL environment."
    echo "The daemon has been installed but could not be started automatically."
    echo "To run the daemon manually in the background, you can use:"
    echo "  sudo nohup /usr/bin/python3 /opt/mystic_monitor/mystic_daemon.py > /dev/null 2>&1 &"
    echo ""
fi

echo ""
echo "==========================================================="
echo "   Installation Complete! The OS is now monitored."
echo "==========================================================="
echo "You can now type the following commands anywhere in the OS:"
echo ""
echo "  mystic-top       (launch the interactive monitoring dashboard)"
echo "  man mystic-top   (read the official manual page)"
echo "==========================================================="
echo ""
