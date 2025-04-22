#!/bin/bash

# Get the version from the command line
version=$1

# Download the install script
curl -L https://raw.githubusercontent.com/hydra-dynamix/erasmus/refs/heads/main/releases/erasmus/$version/erasmus_v$version.sh -o erasmus.sh

# Make the script executable
chmod +x erasmus.sh

# Run the script
./erasmus.sh

# Remove the script
rm erasmus.sh
