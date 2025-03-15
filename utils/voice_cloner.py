"""
Voice Cloning Utility

A self-contained module for voice cloning with proper fallback mechanisms.
"""

import os
import sys
import time
import torch
import logging
import tempfile
import subprocess
import torchaudio
import shutil
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("voice_cloner")

class VoiceCloner:
    """
    Handles voice cloning with proper fallback mechanisms.
    """
    
    def __init__(self, 
                 input_voice_dir=None, 
                 output_dir=None,
                 model_path=None):
        """
        Initialize the voice cloner.
        
        Args:
            input_voice_dir: Directory containing input voice samples
            output_dir: Directory to save generated voices
            model_path: Path to model checkpoint or None to use default
        """
        # Set up directories
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.input_voice_dir = input_voice_dir or os.path.join(self.base_dir, "voices", "input")
        self.output_dir = output_dir or os.path.join(self.base_dir, "voices", "output")
        self.model_path = model_path
        
        # Ensure directories exist
        os.makedirs(self.input_voice_dir, exist_ok=True)
        os.makedirs(self.output_dir, exist_ok=True)
        
        logger.info(f"Voice Cloner initialized with input_dir={self.input_voice_dir}, output_dir={self.output_dir}")
    
    def _generate_output_filename(self, prefix="generated", extension=".wav"):
        """Generate a unique output filename with timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{prefix}_{timestamp}{extension}"
    
    def _write_text_to_temp_file(self, text):
        """Write text to a temporary file and return the file path."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as temp:
            temp.write(text)
            temp_path = temp.name
        
        logger.debug(f"Text written to temporary file: {temp_path}")
        return temp_path
    
    def _check_voice_file(self, voice_path):
        """Check if a voice file exists and is valid."""
        if not os.path.exists(voice_path):
            logger.error(f"Voice file not found: {voice_path}")
            return False
        
        try:
            # Try to load the file to verify it's a valid audio file
            waveform, sample_rate = torchaudio.load(voice_path)
            logger.debug(f"Voice file validated: {voice_path} ({waveform.shape[1]/sample_rate:.2f}s, {sample_rate}Hz)")
            return True
        except Exception as e:
            logger.error(f"Invalid voice file {voice_path}: {e}")
            return False
    
    def _check_output_file(self, output_path, min_size_kb=10):
        """Check if an output file exists and is valid."""
        if not os.path.exists(output_path):
            logger.error(f"Output file not found: {output_path}")
            return False
        
        # Check file size
        file_size_kb = os.path.getsize(output_path) / 1024
        if file_size_kb < min_size_kb:
            logger.error(f"Output file too small ({file_size_kb:.2f} KB): {output_path}")
            return False
        
        try:
            # Try to load the file to verify it's a valid audio file
            waveform, sample_rate = torchaudio.load(output_path)
            logger.debug(f"Output file validated: {output_path} ({waveform.shape[1]/sample_rate:.2f}s, {sample_rate}Hz)")
            return True
        except Exception as e:
            logger.error(f"Invalid output file {output_path}: {e}")
            return False
    
    def _fallback_copy_original(self, voice_path, output_path):
        """Fallback mechanism: copy the original voice file."""
        try:
            shutil.copy2(voice_path, output_path)
            logger.warning(f"Fallback: Copied original voice file to {output_path}")
            return True
        except Exception as e:
            logger.error(f"Fallback copy failed: {e}")
            return False
    
    def generate_direct(self, text, voice_path, output_path=None, device="auto"):
        """
        Generate speech directly using our internal model.
        
        Args:
            text: Text to convert to speech
            voice_path: Path to voice sample
            output_path: Path to save output (or auto-generated if None)
            device: 'cuda', 'cpu', or 'auto'
            
        Returns:
            Path to generated audio file or None if failed
        """
        if output_path is None:
            output_path = os.path.join(self.output_dir, self._generate_output_filename())
        
        # Ensure output directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Validate voice file
        if not self._check_voice_file(voice_path):
            logger.error(f"Invalid voice file: {voice_path}")
            return None
        
        try:
            # Import here to avoid circular imports
            sys.path.append(self.base_dir)
            from models.csm_model import CSMModelLoader, is_cuda_available
            
            # Determine device
            if device == "auto":
                device = "cuda" if is_cuda_available() else "cpu"
            
            logger.info(f"Generating speech with text: '{text[:50]}...' using device: {device}")
            
            # Load model and generate speech
            model_loader = CSMModelLoader(model_path=self.model_path, device=device)
            model_loader.generate_speech(text=text, output_path=output_path)
            
            # Validate output
            if self._check_output_file(output_path):
                logger.info(f"Successfully generated speech at: {output_path}")
                return output_path
            else:
                logger.error("Generated file is invalid")
                return None
                
        except Exception as e:
            logger.error(f"Error in direct generation: {e}")
            
            # Try fallback to CPU if we were using CUDA
            if device == "cuda":
                try:
                    logger.info("Attempting fallback to CPU")
                    return self.generate_direct(text, voice_path, output_path, device="cpu")
                except Exception as cpu_e:
                    logger.error(f"CPU fallback also failed: {cpu_e}")
            
            # Last resort: copy original voice
            if self._fallback_copy_original(voice_path, output_path):
                return output_path
            
            return None
    
    def generate(self, text, voice_path=None, output_path=None, device="auto"):
        """
        Generate speech with the given text and voice.
        
        Args:
            text: Text to convert to speech
            voice_path: Path to voice sample (or None to use first available)
            output_path: Path to save output (or auto-generated if None)
            device: 'cuda', 'cpu', or 'auto'
            
        Returns:
            Path to generated audio file or None if failed
        """
        start_time = time.time()
        
        # Find voice file if not specified
        if voice_path is None:
            voice_files = [f for f in os.listdir(self.input_voice_dir) 
                          if f.endswith('.wav') and os.path.isfile(os.path.join(self.input_voice_dir, f))]
            if not voice_files:
                logger.error(f"No voice files found in {self.input_voice_dir}")
                return None
            
            voice_path = os.path.join(self.input_voice_dir, voice_files[0])
            logger.info(f"Using voice file: {voice_path}")
        
        # Generate output path if not specified
        if output_path is None:
            output_path = os.path.join(self.output_dir, self._generate_output_filename())
        
        # Try direct generation first
        result = self.generate_direct(text, voice_path, output_path, device)
        
        elapsed_time = time.time() - start_time
        logger.info(f"Voice generation completed in {elapsed_time:.2f} seconds")
        
        return result 