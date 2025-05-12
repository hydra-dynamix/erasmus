#!/bin/bash

uv run packager package erasmus cli/main.py

bash scripts/build_installer.sh
