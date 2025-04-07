#!/bin/bash

if [ -f ".env" ]; then
    rm .env
fi
if [ -f ".cursorrules" ]; then
    rm .cursorrules
fi

if [ -f ".windsurfrules" ]; then
    rm .windsurfrules
fi

if [ -f "global_rules.md" ]; then
    rm "global_rules.md"
fi


version=$(jq -r '.version' version.json)

echo $version

if [ -d "release/$version" ]; then
    rm "release/$version"
fi

