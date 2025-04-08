#!/bin/bash

# Change to the project root directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT" || { echo "Failed to change to project root directory."; exit 1; }
echo "Changed to project root directory: $PROJECT_ROOT"

if [ -f "$PROJECT_ROOT/.env" ]; then
    rm "$PROJECT_ROOT/.env"
fi
if [ -f "$PROJECT_ROOT/.cursorrules" ]; then
    rm "$PROJECT_ROOT/.cursorrules"
fi

if [ -f "$PROJECT_ROOT/.windsurfrules" ]; then
    rm "$PROJECT_ROOT/.windsurfrules"
fi

if [ -f "$PROJECT_ROOT/global_rules.md" ]; then
    rm "$PROJECT_ROOT/"global_rules.md""
fi


version=$(jq -r '.version' version.json)

release_dir="$PROJECT_ROOT/release/v$version"

if [ -d "$release_dir" ]; then
    rm -rf "$release_dir"
fi

