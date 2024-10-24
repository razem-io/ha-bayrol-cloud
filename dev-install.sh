#!/bin/bash

# Configuration
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
    echo -e "\nUsage:"
    echo "1. Edit the script variables if needed:"
    echo "   - REMOTE_USER: The Home Assistant user (default: root)"
    echo "   - REMOTE_HOST: Your Home Assistant hostname or IP"
    echo "   - REMOTE_PATH: Path to custom_components directory"
    echo ""
    echo "2. Make the script executable:"
    echo "   chmod +x dev-install.sh"
    echo ""
    echo "3. Run the script:"
    echo "   ./dev-install.sh"
    echo ""
    echo "Options:"
    echo "   -h, --help    Show this help message"
}

# Check for help flag
if [[ "$1" == "-h" ]] || [[ "$1" == "--help" ]]; then
    show_usage
    exit 0
fi

# Check if rsync is installed
if ! command -v rsync &> /dev/null; then
    echo -e "${RED}Error: rsync is not installed. Please install it first.${NC}"
    show_usage
    exit 1
fi

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
