#!/bin/bash
# Start the TTS server

# Change to the project directory
cd "$(dirname "$0")"

# Create necessary directories
mkdir -p voices/input voices/output

# Check if we have a sample voice file
if [ ! -f "voices/input/speaker_7_temp_1.3_topk_80_accent_variation_120.wav" ]; then
    echo "Copying sample voice file..."
    cp /home/tdeshane/movie_maker/voices/explore/speaker_7_temp_1.3_topk_80_accent_variation_120.wav voices/input/ 2>/dev/null || echo "Warning: Could not copy sample voice file"
fi

# Start the server
echo "Starting TTS server on port 8080..."
python scripts/serve_tts.py --verbose "$@" 