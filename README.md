# TTS Proof of Concept

A minimal, reliable Text-to-Speech system inspired by ElevenLabs. This project provides a clean implementation focused on robust text-to-speech generation with proper fallback mechanisms and error handling.

## Project Structure

- `models/` - Contains model files or interface code for models
  - `csm_model.py` - Main model loader with fallback mechanisms
  - `csm_standalone.py` - Standalone CSM model implementation
  - `placeholder_csm.py` - Placeholder model for when the real model is unavailable
- `voices/` - Contains input voice samples and generated output
  - `input/` - Reference voice samples
  - `output/` - Generated speech files
- `utils/` - Helper functions and utilities
  - `voice_cloner.py` - Main voice cloning utility
- `scripts/` - Command-line scripts for TTS generation
  - `generate_speech.py` - Command-line script for generating speech
  - `serve_tts.py` - Web server for TTS API
  - `debug_tts.html` - Debug page for testing the TTS API

## Setup

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Copy a sample voice file:
```bash
mkdir -p voices/input
cp /home/tdeshane/movie_maker/voices/explore/speaker_7_temp_1.3_topk_80_accent_variation_120.wav voices/input/
```

## Usage

### Command-line Usage

Generate speech from the command line:

```bash
./scripts/generate_speech.py --text "Your text here" --device cpu
```

Options:
- `--text`: Text to convert to speech (required)
- `--voice`: Path to voice sample (optional, uses first available if not specified)
- `--output`: Path to save output (optional, auto-generated if not specified)
- `--device`: Device to use for generation (auto, cuda, or cpu, default: auto)
- `--model`: Path to model checkpoint (optional)
- `--verbose`: Enable verbose logging

### Web API Usage

1. Start the TTS server:
```bash
./start_server.sh
```

2. In a separate terminal, start the debug page server:
```bash
./serve_debug_page.sh
```

3. Access the debug page at: http://localhost:8081/scripts/debug_tts.html

4. Use the web interface to generate speech:
   - Select a voice from the dropdown
   - Enter text in the input box
   - Click "Generate Speech"
   - The generated audio will play automatically

### API Endpoints

- `GET /api/health`: Check server health
- `POST /api/tts`: Generate speech
  - Request body: `{ "text": "Your text here", "voice": "/path/to/voice.wav", "device": "auto" }`
  - Response: `{ "success": true, "output_path": "/path/to/output.wav", "url": "/voices/output/output.wav" }`

## Features

- Robust fallback from GPU to CPU when needed
- Clear error messages and diagnostics
- Simple, focused API for TTS generation
- Proper handling of file paths and I/O
- Progress indicators for long-running operations
- Web interface for easy testing and debugging 