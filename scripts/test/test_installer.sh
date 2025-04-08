#!/bin/bash

# Exit on error
set -e

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
cd "$PROJECT_ROOT" || { echo -e "${RED}Failed to change to project root directory.${NC}"; exit 1; }
echo -e "${GREEN}Changed to project root directory: $PROJECT_ROOT${NC}"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed!${NC}"
    echo "Please install Docker before running this script."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed!${NC}"
    echo "Please install Docker Compose before running this script."
    exit 1
fi

# Check if the installer exists
if [ ! -f "release/v0.0.1/erasmus_v0.0.1.sh" ]; then
    echo -e "${YELLOW}Installer not found. Building the release package...${NC}"
    uv run main.py build
    if [ $? -ne 0 ]; then
        echo -e "${RED}Failed to build the release package.${NC}"
        exit 1
    fi
fi

# Build and run the Docker container
echo -e "${YELLOW}Building and running the Docker container...${NC}"
cd build/docker || { echo -e "${RED}Failed to change to Docker directory.${NC}"; exit 1; }

# Get current user ID and group ID for permission preservation
USER_ID=$(id -u)
GROUP_ID=$(id -g)

# Export variables for docker-compose
export USER_ID
export GROUP_ID

# Build the Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker compose build

# Run the Docker container
echo -e "${YELLOW}Running Docker container...${NC}"
docker compose up

# Check if the installation was successful
if [ $? -eq 0 ]; then
    echo -e "${GREEN}Installation test completed successfully!${NC}"
else
    echo -e "${RED}Installation test failed.${NC}"
    # Don't exit on failure - try to fix permissions anyway
fi

# Fix permissions on any files that might have been created by Docker
echo -e "${YELLOW}Fixing permissions on files created by Docker...${NC}"
cd "$PROJECT_ROOT" || { echo -e "${RED}Failed to change to project root directory.${NC}"; exit 1; }
sudo find . -not -user $USER_ID -exec chown $USER_ID:$GROUP_ID {} \; 2>/dev/null || true

# Return to the project root directory
cd "$PROJECT_ROOT" || { echo -e "${RED}Failed to change to project root directory.${NC}"; exit 1; } 