#!/home/tdeshane/nexa_venv/bin/python3
"""
TTS Generation Test Script

This script tests both the simple voice cloner and the CSM model adapter.
It allows generating speech from text using either of the available models.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_generation")

# Add the project directory to the path so we can import our modules
script_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(script_dir)

# Import our modules
try:
    from utils.voice_cloner import VoiceCloner
    from utils.csm_adapter import CSMModelAdapter
except ImportError as e:
    logger.error(f"Error importing modules: {e}")
    print(f"Error importing modules: {e}")
    sys.exit(1)

def main():
    """Main function for testing TTS generation."""
    parser = argparse.ArgumentParser(description="Test TTS generation")
    parser.add_argument("--text", default="Hello world.", 
                        help="Text to convert to speech")
    parser.add_argument("--model", choices=["simple", "csm"], default="simple",
                        help="Model to use for TTS generation")
    parser.add_argument("--device", choices=["cpu", "cuda", "auto"], default="auto",
                        help="Device to use for TTS generation")
    parser.add_argument("--voice", default=None,
                        help="Path to voice sample file (optional)")
    
    args = parser.parse_args()
    
    # Use an even shorter text for CPU tests
    if args.device == "cpu" and args.text == "Hello world.":
        args.text = "Test."
        logger.info(f"Using shorter text for CPU test: '{args.text}'")
    
    # Create output directory if it doesn't exist
    output_dir = os.path.join(script_dir, "voices", "output")
    os.makedirs(output_dir, exist_ok=True)

    if args.model == "simple":
        logger.info("Using simple voice cloner model")
        try:
            vc = VoiceCloner()
            
            # Check if a sample voice file was provided
            voice_file = args.voice
            if not voice_file:
                # Use a default voice sample if available
                sample_dir = os.path.join(script_dir, "voices", "input")
                if os.path.exists(sample_dir):
                    sample_files = [f for f in os.listdir(sample_dir) if f.endswith('.wav')]
                    if sample_files:
                        voice_file = os.path.join(sample_dir, sample_files[0])
                        logger.info(f"Using sample voice file: {voice_file}")
            
            # Generate speech
            output_file = vc.generate(args.text, voice_path=voice_file, device=args.device)
            
            if output_file and os.path.exists(output_file):
                print(f"Successfully generated speech at: {output_file}")
                print(f"Text: \"{args.text}\"")
            else:
                print("Failed to generate speech.")
                
        except Exception as e:
            logger.exception(f"Error during TTS generation: {e}")
            print(f"Error during TTS generation: {e}")
            sys.exit(1)
    
    elif args.model == "csm":
        logger.info("Using CSM model adapter")
        try:
            adapter = CSMModelAdapter()
            
            # Generate speech
            output_file = adapter.generate_speech(args.text, voice_path=args.voice, device=args.device)
            
            if output_file and os.path.exists(output_file):
                print(f"Successfully generated speech with CSM model at: {output_file}")
                print(f"Text: \"{args.text}\"")
            else:
                print("Failed to generate speech with CSM model.")
                
        except Exception as e:
            logger.exception(f"Error during CSM TTS generation: {e}")
            print(f"Error during CSM TTS generation: {e}")
            sys.exit(1)

if __name__ == "__main__":
    main() 