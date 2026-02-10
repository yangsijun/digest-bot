#!/bin/bash
# Installation script for News Digest Bot
# This script sets up the systemd service and configures the environment

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
SERVICE_NAME="digest-bot"
# Use current directory if not already in /opt
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="${INSTALL_DIR:-$SCRIPT_DIR}"
SERVICE_FILE="digest-bot.service"
BACKUP_SCRIPT="cron/backup.sh"
CRON_LOG="/var/log/digest-bot-backup.log"

echo -e "${YELLOW}=== News Digest Bot Installation ===${NC}"
echo ""

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   echo -e "${RED}Error: This script must be run as root (use sudo)${NC}"
   exit 1
fi

# Step 1: Create digest-bot user if it doesn't exist
echo -e "${YELLOW}Step 1: Creating digest-bot system user...${NC}"
if id "$SERVICE_NAME" &>/dev/null; then
    echo -e "${GREEN}✓ User '$SERVICE_NAME' already exists${NC}"
else
    useradd --system --no-create-home --shell /bin/false "$SERVICE_NAME"
    echo -e "${GREEN}✓ Created system user '$SERVICE_NAME'${NC}"
fi
echo ""

# Step 2: Copy service file to systemd directory
echo -e "${YELLOW}Step 2: Installing systemd service file...${NC}"
if [ ! -f "$SERVICE_FILE" ]; then
    echo -e "${RED}Error: $SERVICE_FILE not found in current directory${NC}"
    exit 1
fi
cp "$SERVICE_FILE" "$SERVICE_DIR/$SERVICE_FILE"
chmod 644 "$SERVICE_DIR/$SERVICE_FILE"
echo -e "${GREEN}✓ Installed $SERVICE_FILE to $SERVICE_DIR${NC}"
echo ""

# Step 3: Set up project directory permissions
echo -e "${YELLOW}Step 3: Setting up project directory permissions...${NC}"
if [ ! -d "$INSTALL_DIR" ]; then
    echo -e "${RED}Error: Installation directory $INSTALL_DIR does not exist${NC}"
    echo "Please ensure the digest-bot project is installed at $INSTALL_DIR"
    exit 1
fi
chown -R "$SERVICE_NAME:$SERVICE_NAME" "$INSTALL_DIR"
chmod 755 "$INSTALL_DIR"
echo -e "${GREEN}✓ Set permissions for $INSTALL_DIR${NC}"
echo ""

# Step 4: Create .env file from example if it doesn't exist
echo -e "${YELLOW}Step 4: Checking environment configuration...${NC}"
if [ -f "$INSTALL_DIR/.env" ]; then
    echo -e "${GREEN}✓ .env file already exists${NC}"
else
    if [ -f "$INSTALL_DIR/.env.example" ]; then
        cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
        chmod 600 "$INSTALL_DIR/.env"
        chown "$SERVICE_NAME:$SERVICE_NAME" "$INSTALL_DIR/.env"
        echo -e "${YELLOW}⚠ Created .env from .env.example - PLEASE EDIT WITH YOUR CREDENTIALS${NC}"
        echo -e "${YELLOW}  Edit: $INSTALL_DIR/.env${NC}"
        echo -e "${YELLOW}  Required variables:${NC}"
        echo -e "${YELLOW}    - TELEGRAM_BOT_TOKEN${NC}"
        echo -e "${YELLOW}    - TELEGRAM_CHAT_ID${NC}"
        echo -e "${YELLOW}    - PRODUCTHUNT_CLIENT_ID${NC}"
        echo -e "${YELLOW}    - PRODUCTHUNT_CLIENT_SECRET${NC}"
    else
        echo -e "${RED}Error: .env.example not found${NC}"
        exit 1
    fi
fi
echo ""

# Step 5: Reload systemd daemon
echo -e "${YELLOW}Step 5: Reloading systemd daemon...${NC}"
systemctl daemon-reload
echo -e "${GREEN}✓ Systemd daemon reloaded${NC}"
echo ""

# Step 6: Enable service for auto-start
echo -e "${YELLOW}Step 6: Enabling service for auto-start...${NC}"
systemctl enable "$SERVICE_NAME"
echo -e "${GREEN}✓ Service enabled (will start on system boot)${NC}"
echo ""

# Step 7: Set up backup cron job
echo -e "${YELLOW}Step 7: Setting up backup cron job...${NC}"
if [ -f "$INSTALL_DIR/$BACKUP_SCRIPT" ]; then
    chmod +x "$INSTALL_DIR/$BACKUP_SCRIPT"
    
    # Create cron log directory
    mkdir -p "$(dirname "$CRON_LOG")"
    touch "$CRON_LOG"
    chown "$SERVICE_NAME:$SERVICE_NAME" "$CRON_LOG"
    
    # Add cron job (run daily at 03:00)
    CRON_JOB="0 3 * * * $INSTALL_DIR/$BACKUP_SCRIPT >> $CRON_LOG 2>&1"
    
    # Check if cron job already exists
    if crontab -u "$SERVICE_NAME" -l 2>/dev/null | grep -q "$BACKUP_SCRIPT"; then
        echo -e "${GREEN}✓ Backup cron job already configured${NC}"
    else
        (crontab -u "$SERVICE_NAME" -l 2>/dev/null; echo "$CRON_JOB") | crontab -u "$SERVICE_NAME" -
        echo -e "${GREEN}✓ Added backup cron job (daily at 03:00)${NC}"
    fi
else
    echo -e "${YELLOW}⚠ Backup script not found at $INSTALL_DIR/$BACKUP_SCRIPT${NC}"
fi
echo ""

# Step 8: Display next steps
echo -e "${GREEN}=== Installation Complete ===${NC}"
echo ""
echo -e "${YELLOW}Next Steps:${NC}"
echo "1. Edit environment variables:"
echo -e "   ${GREEN}sudo nano $INSTALL_DIR/.env${NC}"
echo ""
echo "2. Start the service:"
echo -e "   ${GREEN}sudo systemctl start $SERVICE_NAME${NC}"
echo ""
echo "3. Check service status:"
echo -e "   ${GREEN}sudo systemctl status $SERVICE_NAME${NC}"
echo ""
echo "4. View service logs:"
echo -e "   ${GREEN}sudo journalctl -u $SERVICE_NAME -f${NC}"
echo ""
echo "5. View backup logs:"
echo -e "   ${GREEN}tail -f $CRON_LOG${NC}"
echo ""
echo -e "${YELLOW}Useful Commands:${NC}"
echo "  Stop service:     sudo systemctl stop $SERVICE_NAME"
echo "  Restart service:  sudo systemctl restart $SERVICE_NAME"
echo "  Disable service:  sudo systemctl disable $SERVICE_NAME"
echo "  View logs:        sudo journalctl -u $SERVICE_NAME -n 50"
echo "  Follow logs:      sudo journalctl -u $SERVICE_NAME -f"
echo ""
