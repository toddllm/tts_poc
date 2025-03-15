"""
Placeholder CSM Model

A minimal implementation of the CSM model interface when the actual model cannot be loaded.
This serves as a fallback to maintain API compatibility.
"""

import os
import torch
import logging
import numpy as np
import torchaudio

logger = logging.getLogger("placeholder_csm")

class PlaceholderCSMModel:
    """A placeholder for the CSM model that maintains the API but provides warnings."""
    
    def __init__(self):
        self.sample_rate = 24000  # Standard sample rate for CSM model
        logger.warning("Using placeholder CSM model - generation quality will be limited")
    
    def generate(self, text, speaker=0, context=None, max_audio_length_ms=10000):
        """
        Generate placeholder audio that maintains the API.
        
        Args:
            text: The text to convert to speech
            speaker: Speaker ID to use
            context: Optional context for generation
            max_audio_length_ms: Maximum audio length in milliseconds
            
        Returns:
            A placeholder audio tensor (silent by default)
        """
        logger.warning(f"Placeholder generate called with text: '{text[:50]}...'")
        
        # Calculate number of samples for the requested duration
        num_samples = int(self.sample_rate * max_audio_length_ms / 1000)
        
        # Generate silent audio
        audio = torch.zeros(num_samples)
        
        logger.info(f"Generated placeholder silent audio ({num_samples} samples)")
        return audio

def load_csm_1b(model_path=None, device="cpu"):
    """
    Placeholder function that mimics the interface of the real load_csm_1b function.
    
    Args:
        model_path: Path to model checkpoint (ignored in placeholder)
        device: Device to load model on (ignored in placeholder)
        
    Returns:
        A placeholder model instance
    """
    logger.warning(f"Placeholder load_csm_1b called with model_path={model_path}, device={device}")
    logger.warning("This is a PLACEHOLDER implementation and will not produce real speech")
    
    return PlaceholderCSMModel() 