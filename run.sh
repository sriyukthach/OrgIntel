#!/bin/bash
# OrgIntel Single-Command Launcher
# Starts backend server and opens web app

set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

echo "========================================================"
echo "  🚀 Starting ORGINTEL (AI Company Intelligence)"
echo "========================================================"

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is required."
    exit 1
fi

# Run the server
exec python3 run.py "$@"
