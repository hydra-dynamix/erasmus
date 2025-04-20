#!/bin/bash

uv run packager package erasmus

bash scripts/build_installer.sh
