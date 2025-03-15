#!/bin/bash
# Serve the debug page

# Change to the project directory
cd "$(dirname "$0")"

# Start a simple HTTP server on port 8081
echo "Starting HTTP server for debug page on port 8081..."
echo "Access the debug page at: http://localhost:8081/scripts/debug_tts.html"
python -m http.server 8081 