#!/usr/bin/env python3
"""
Generate Speech

A command-line script to generate speech using the voice cloning utility.
"""

import os
import sys
import argparse
import logging
import time

# Add parent directory to path to allow importing from tts_poc
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.voice_cloner import VoiceCloner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("generate_speech")

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Generate speech from text using voice cloning")
    
    parser.add_argument("--text", type=str, required=True,
                        help="Text to convert to speech")
    
    parser.add_argument("--voice", type=str, default=None,
                        help="Path to voice sample (WAV file)")
    
    parser.add_argument("--output", type=str, default=None,
                        help="Path to save output audio file")
    
    parser.add_argument("--device", type=str, default="auto", choices=["auto", "cuda", "cpu"],
                        help="Device to use for generation (auto, cuda, or cpu)")
    
    parser.add_argument("--model", type=str, default=None,
                        help="Path to model checkpoint (optional)")
    
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose logging")
    
    return parser.parse_args()

def main():
    """Main function."""
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Print arguments
    logger.info(f"Text: {args.text}")
    logger.info(f"Voice: {args.voice or 'auto'}")
    logger.info(f"Output: {args.output or 'auto'}")
    logger.info(f"Device: {args.device}")
    logger.info(f"Model: {args.model or 'default'}")
    
    # Initialize voice cloner
    cloner = VoiceCloner(model_path=args.model)
    
    # Generate speech
    start_time = time.time()
    output_path = cloner.generate(
        text=args.text,
        voice_path=args.voice,
        output_path=args.output,
        device=args.device
    )
    
    # Print result
    elapsed_time = time.time() - start_time
    if output_path:
        logger.info(f"Speech generated successfully in {elapsed_time:.2f} seconds")
        logger.info(f"Output saved to: {output_path}")
        return 0
    else:
        logger.error(f"Speech generation failed after {elapsed_time:.2f} seconds")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 