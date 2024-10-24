#!/bin/bash

# Default Configuration
REMOTE_USER="root"
REMOTE_HOST="homeassistant.local"  # Change this to your Home Assistant IP or hostname
REMOTE_PATH="/config/custom_components"
LOCAL_COMPONENT="custom_components/bayrol_cloud"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Show usage instructions
show_usage() {
    echo -e "\nUsage: ./dev-install.sh [-u user] [-h host]"
    echo ""
    echo "Options:"
    echo "   -u, --user    Remote user (default: root)"
    echo "   -h, --host    Remote host (default: homeassistant.local)"
    echo "   --help        Show this help message"
    echo ""
    echo "Example:"
    echo "   ./dev-install.sh -u admin -h 192.168.1.100"
    echo ""
    echo "Note: Make sure the script is executable (chmod +x dev-install.sh)"
}

# Parse command line arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -u|--user) REMOTE_USER="$2"; shift ;;
        -h|--host) REMOTE_HOST="$2"; shift ;;
        --help) show_usage; exit 0 ;;
        *) echo "Unknown parameter: $1"; show_usage; exit 1 ;;
    esac
    shift
done

# Check if rsync is installed
if ! command -v rsync &> /dev/null; then
    echo -e "${RED}Error: rsync is not installed. Please install it first.${NC}"
    show_usage
    exit 1
fi

# Display current configuration
echo -e "Using configuration:"
echo -e "  Remote User: ${GREEN}${REMOTE_USER}${NC}"
echo -e "  Remote Host: ${GREEN}${REMOTE_HOST}${NC}"
echo -e "  Remote Path: ${GREEN}${REMOTE_PATH}${NC}"
echo ""

# Sync files to Home Assistant
echo "Syncing files to Home Assistant..."
rsync -av --delete \
    "${LOCAL_COMPONENT}/" \
    "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}/bayrol_cloud/"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}Files synced successfully!${NC}"
    
    # Restart Home Assistant
    echo "Attempting to restart Home Assistant..."
    ssh "${REMOTE_USER}@${REMOTE_HOST}" 'ha core restart'
    
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}Home Assistant restart initiated.${NC}"
        echo "Waiting for Home Assistant to come back online..."
        sleep 30
        echo -e "${GREEN}Development installation complete!${NC}"
    else
        echo -e "${RED}Failed to restart Home Assistant. Please restart manually.${NC}"
        exit 1
    fi
else
    echo -e "${RED}Failed to sync files to Home Assistant.${NC}"
    show_usage
    exit 1
fi
