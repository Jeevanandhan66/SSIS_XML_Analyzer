#!/bin/bash

# Start Python FastAPI server in the background
echo "Starting Python FastAPI server on port 8000..."
python api_server.py &
PYTHON_PID=$!

# Give Python server time to start
sleep 3

# Start Node.js server
echo "Starting Node.js server..."
npm run dev

# Cleanup on exit
trap "kill $PYTHON_PID" EXIT
