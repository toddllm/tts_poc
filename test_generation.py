#!/home/tdeshane/nexa_venv/bin/python3
"""
Test Generation Script

A simple script to test the TTS generation functionality.
"""

import os
import sys
import logging
import argparse

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("test_generation")

# Add the tts_poc directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import from our project
from utils.voice_cloner import VoiceCloner

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Test TTS generation.")
    parser.add_argument("--force-device", choices=["cpu", "cuda", "auto"], default="auto",
                       help="Force a specific device for generation")
    parser.add_argument("--text", type=str, 
                       default="This is a test of our text to speech system. It should generate audio even if CUDA is not available or fails.",
                       help="Text to convert to speech")
    parser.add_argument("--verbose", action="store_true", 
                       help="Enable more verbose output")
    return parser.parse_args()

def main():
    """Main function to test TTS generation."""
    # Parse arguments
    args = parse_arguments()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
        
    logger.info("Starting TTS test generation")
    logger.info(f"Using device: {args.force_device}")
    
    # Initialize the voice cloner
    cloner = VoiceCloner()
    
    # Check if we have the sample voice file
    sample_voice_path = os.path.join(cloner.input_voice_dir, "speaker_7_temp_1.3_topk_80_accent_variation_120.wav")
    if not os.path.exists(sample_voice_path):
        logger.error(f"Sample voice file not found: {sample_voice_path}")
        logger.info("Attempting to copy from movie_maker...")
        
        # Try to copy from movie_maker
        source_path = "/home/tdeshane/movie_maker/voices/explore/speaker_7_temp_1.3_topk_80_accent_variation_120.wav"
        if os.path.exists(source_path):
            import shutil
            os.makedirs(os.path.dirname(sample_voice_path), exist_ok=True)
            shutil.copy2(source_path, sample_voice_path)
            logger.info(f"Copied sample voice file to {sample_voice_path}")
        else:
            logger.error(f"Source voice file not found: {source_path}")
            return 1
    
    # Generate speech
    logger.info(f"Generating speech with text: {args.text}")
    logger.info(f"Using device: {args.force_device}")
    
    # Generate with specified device
    output_path = cloner.generate(
        text=args.text,
        voice_path=sample_voice_path,
        device=args.force_device
    )
    
    if output_path:
        logger.info(f"Successfully generated speech at: {output_path}")
        return 0
    else:
        logger.error(f"Failed to generate speech with {args.force_device}")
        
        # If not already tried with CPU, try it
        if args.force_device != "cpu":
            logger.info("Trying again with CPU explicitly...")
            output_path = cloner.generate(
                text=args.text,
                voice_path=sample_voice_path,
                device="cpu"
            )
            
            if output_path:
                logger.info(f"Successfully generated speech with CPU at: {output_path}")
                return 0
        
        logger.error("Failed to generate speech even with fallback")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 