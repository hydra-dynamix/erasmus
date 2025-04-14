#!/bin/bash

# Set up colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
WHITE='\033[0;37m'
NC='\033[0m' # No Color

# Create build directory
PWD=$(pwd)
BUILD_DIR="$PWD/gamesync_demo"
mkdir -p "$BUILD_DIR"

# Copy example architecture
echo -e "${YELLOW}Copying example architecture...${NC}"
cp "$PWD/docs/examples/game_sync/.erasmus/.architecture.md" "$BUILD_DIR/.erasmus/.architecture.md"

cd "$BUILD_DIR"

# Clone Erasmus repository
echo -e "${YELLOW}Cloning Erasmus repository...${NC}"
git clone https://github.com/Bakobiibizo/erasmus.git
cd erasmus
git checkout packager
cd ..

# Set up Python virtual environment
echo -e "${YELLOW}Setting up virtual environment...${NC}"
uv venv
source .venv/bin/activate

# Install Erasmus and dependencies
echo -e "${YELLOW}Installing Erasmus and dependencies...${NC}"
uv pip install -e ./erasmus

# Create initial project files
cat >README.md <<EOF
# GameSync: Real-time Multiplayer Game Leaderboard and Replay System

## Create environment
Run \`uv venv\`
Activate with \`source .venv/bin/activate\`

## Components
- Game Client (Pygame)
- Event Processor (Rust)
- Leaderboard Service (Go)
- Replay Visualization (React)

## Getting Started
Run \`uv run erasmus --setup\` to configure erasmus and \`uv run erasmus --watch\` to start the development environment
EOF

uv add \
    pygame \
    rustworkx \
    redis \
    react \
    three \
    pandas

echo -e "${GREEN}GameSync demo project setup complete!${NC}"
echo -e "${YELLOW}Next steps:${NC}"
echo -e "${BLUE}1. Open the demo directory: ${WHITE}CTRL-K CTRL-O $BUILD_DIR${NC}"
echo -e "${BLUE}2. Run: ${WHITE}'uv run erasmus --setup'${NC}"
echo -e "${BLUE}3. Run: ${WHITE}'uv run erasmus --watch'${NC}"
echo -e "${BLUE}4. Enable write mode${NC}"
echo -e "${BLUE}5. Open your IDE agent: ${WHITE}CTRL-L${NC}"
echo -e "${BLUE}6. Enter ${WHITE}'Please begin development following the workflow and using TDD'${NC}"
