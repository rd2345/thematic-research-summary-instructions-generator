#!/bin/bash

# Default dev_mode to false
DEV_MODE=false

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dev_mode|--dev)
            DEV_MODE=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [--dev_mode|--dev] [--help]"
            echo "  --dev_mode, --dev    Enable development mode (shows debug elements)"
            echo "  --help               Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "Starting: Custom Score Creation Tool..."
echo "Development mode: $DEV_MODE"

# Export dev_mode as environment variable
export DEV_MODE=$DEV_MODE

# Kill any existing Flask processes on port 5000
echo "Checking for existing Flask processes..."
lsof -ti:5000 | xargs kill -9 2>/dev/null && echo "Killed existing processes on port 5000" || echo "No existing processes found on port 5000"

# Wait a moment for processes to clean up
sleep 2

# Activate virtual environment
source venv/bin/activate

echo "Starting Flask application..."
python3 app_frontend.py
