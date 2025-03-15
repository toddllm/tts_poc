#!/bin/bash
# Initialize the TTS proof-of-concept project

# Change to the project directory
cd "$(dirname "$0")"

# Create necessary directories
echo "Creating directories..."
mkdir -p voices/input voices/output

# Copy sample voice file
echo "Copying sample voice file..."
cp /home/tdeshane/movie_maker/voices/explore/speaker_7_temp_1.3_topk_80_accent_variation_120.wav voices/input/ 2>/dev/null || echo "Warning: Could not copy sample voice file"

# Create Python virtual environment
echo "Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install required packages
echo "Installing required packages..."
pip install -r requirements.txt

# Make scripts executable
echo "Making scripts executable..."
chmod +x scripts/generate_speech.py scripts/serve_tts.py start_server.sh serve_debug_page.sh

echo ""
echo "Initialization complete!"
echo ""
echo "To start the TTS server:"
echo "  ./start_server.sh"
echo ""
echo "To serve the debug page:"
echo "  ./serve_debug_page.sh"
echo ""
echo "To generate speech from the command line:"
echo "  ./scripts/generate_speech.py --text \"Your text here\" --device cpu"
echo "" 