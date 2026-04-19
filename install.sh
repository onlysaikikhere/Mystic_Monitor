#!/bin/bash
set -e

if [ "$1" = "--uninstall" ]; then
    echo "Uninstalling Mystic Monitor..."
    if [ "$EUID" -ne 0 ]; then
        echo "Please run with sudo: sudo ./install.sh --uninstall"
        exit 1
    fi
    systemctl stop mystic-monitor.service >/dev/null 2>&1 || true
    systemctl disable mystic-monitor.service >/dev/null 2>&1 || true
    rm -f /etc/systemd/system/mystic-monitor.service
    systemctl daemon-reload
    rm -rf /opt/mystic_monitor
    rm -f /usr/local/bin/mystic-top /usr/local/bin/mystic-status
    rm -f /usr/local/share/man/man1/mystic-top.1.gz
    # Keep /etc and /var/log typically to preserve configs and logs
    echo "Uninstallation complete. Configuration (/etc) and Logs (/var/log) were preserved."
    exit 0
fi

echo "Starting Mystic Monitor OS Integration..."

# 1. Require root
if [ "$EUID" -ne 0 ]; then
  echo "Please run this installer with sudo:"
  echo "sudo ./install.sh"
  exit 1
fi

# 2. Setup System Group
echo "[1/7] Setting up 'mystic' system group..."
if ! getent group mystic >/dev/null; then
    groupadd --system mystic
fi
if [ -n "$SUDO_USER" ]; then
    usermod -aG mystic "$SUDO_USER" || true
    echo "  -> Added user ${SUDO_USER} to 'mystic' group."
fi

# 3. Install System Dependencies
echo "[2/7] Installing required OS python packages..."
apt-get update -qq
apt-get install -y python3-psutil python3-sklearn python3-pandas

# 4. Setup OS Configuration File & Logs
echo "[3/7] Installing OS configuration and Audit Logs..."
if [ ! -f /etc/mystic-monitor.conf ]; then
    cp config/mystic-monitor.conf /etc/mystic-monitor.conf
    echo "  -> Created /etc/mystic-monitor.conf"
else
    echo "  -> /etc/mystic-monitor.conf already exists, protecting admin configurations."
fi

touch /var/log/mystic-anomalies.log
chown root:mystic /var/log/mystic-anomalies.log
chmod 0660 /var/log/mystic-anomalies.log

# 5. Setup Background Daemon
echo "[4/7] Setting up background daemon in /opt/mystic_monitor..."

if [ ! -f data/model.pkl ]; then
    echo "  -> Pre-trained ML model not found. Generating an initial baseline model..."
    bash ml/train_pipeline.sh 15
fi

mkdir -p /opt/mystic_monitor
cp daemon/mystic_daemon.py /opt/mystic_monitor/
cp data/model.pkl /opt/mystic_monitor/
chown -R root:root /opt/mystic_monitor
chmod 750 /opt/mystic_monitor
chmod +x /opt/mystic_monitor/mystic_daemon.py

# 6. Setup CLI Client (The 'top' interface)
echo "[5/7] Installing global CLI tools 'mystic-top' and 'mystic-status'..."
cp cli/mystic_top.py /usr/local/bin/mystic-top
cp cli/mystic_status.py /usr/local/bin/mystic-status
chmod +x /usr/local/bin/mystic-top
chmod +x /usr/local/bin/mystic-status

# 7. Install standard Man Page
echo "[6/7] Installing OS manual page..."
mkdir -p /usr/local/share/man/man1
gzip -c cli/mystic-top.1 > /usr/local/share/man/man1/mystic-top.1.gz
mandb -q || true

# 8. Systemd Service Integration
echo "[7/7] Integrating with systemd (Service Manager)..."
if command -v systemctl >/dev/null 2>&1 && systemctl is-system-running >/dev/null 2>&1; then
    cp config/mystic-monitor.service /etc/systemd/system/
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
echo "  mystic-status    (check daemon health and configurations)"
echo "  man mystic-top   (read the official manual page)"
echo "==========================================================="
echo ""
