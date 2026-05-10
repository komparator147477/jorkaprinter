#!/bin/bash
set -e

# Configuration
INSTALL_DIR="$HOME/.local/bin"
SCRIPT_NAME="jorka-maintenance"
SERVICE_NAME="jorka-maintenance"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== JorkaPrinter Installer ===${NC}"

# 1. Check Dependencies
echo "Checking dependencies..."
for cmd in python3 lp convert; do
    if ! command -v $cmd &> /dev/null; then
        echo -e "${RED}Error: '$cmd' is not installed.${NC}"
        echo "Please install it (e.g., sudo pacman -S python cups imagemagick)"
        exit 1
    fi
done
echo "Dependencies OK."

# 2. Setup Install Directory
mkdir -p "$INSTALL_DIR"
echo "Installing script to $INSTALL_DIR/$SCRIPT_NAME..."
cp maintenance.py "$INSTALL_DIR/$SCRIPT_NAME"
chmod +x "$INSTALL_DIR/$SCRIPT_NAME"

# 3. Detect Printer
DEFAULT_PRINTER=$(lpstat -d 2>/dev/null | sed -n 's/^system default destination: //p')
if [ -z "$DEFAULT_PRINTER" ]; then
    DEFAULT_PRINTER=""
fi
echo -n "Enter Printer Name [Default: $DEFAULT_PRINTER]: "
read -r USER_PRINTER
PRINTER_NAME=${USER_PRINTER:-$DEFAULT_PRINTER}

if [ -z "$PRINTER_NAME" ]; then
    echo -e "${RED}Error: No printer specified and no default found.${NC}"
    exit 1
fi
echo "Using Printer: $PRINTER_NAME"

# 4. Create Systemd Units
echo "Configuring Systemd User Units..."
mkdir -p "$HOME/.config/systemd/user/"

# Service File
cat <<EOF > "$HOME/.config/systemd/user/$SERVICE_NAME.service"
[Unit]
Description=JorkaPrinter Maintenance for $PRINTER_NAME

[Service]
Type=oneshot
ExecStart=$INSTALL_DIR/$SCRIPT_NAME --printer "$PRINTER_NAME"
EOF

# Timer File
cat <<EOF > "$HOME/.config/systemd/user/$SERVICE_NAME.timer"
[Unit]
Description=Run JorkaPrinter Maintenance Check Daily

[Timer]
OnCalendar=daily
Persistent=true

[Install]
WantedBy=timers.target
EOF

# 5. Enable Timer
echo "Enabling Systemd Timer..."
systemctl --user daemon-reload
systemctl --user enable --now "$SERVICE_NAME.timer"

echo -e "${GREEN}Success!${NC}"
echo "Your printer '$PRINTER_NAME' will be checked daily."
echo "If unused for 7 days, a random test pattern will be printed."
echo "To test immediately, run: $INSTALL_DIR/$SCRIPT_NAME --force"
