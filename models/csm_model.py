"""
CSM Model Loader

A simplified interface for loading and using the Conversational Speech Model (CSM)
with proper error handling and GPU/CPU fallback.
"""

import os
import torch
import logging
from huggingface_hub import hf_hub_download

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("csm_model")

class ModelNotAvailableError(Exception):
    """Raised when the model cannot be loaded."""
    pass

def is_cuda_available():
    """Check if CUDA is available and has enough memory."""
    try:
        if not torch.cuda.is_available():
            logger.info("CUDA not available")
            return False
        
        # Check available GPU memory
        device = torch.cuda.current_device()
        free_memory = torch.cuda.get_device_properties(device).total_memory - torch.cuda.memory_allocated(device)
        free_memory_mb = free_memory / (1024 * 1024)
        
        # Need at least 2 GB of free memory for the model
        if free_memory_mb < 2000:
            logger.info(f"Not enough GPU memory ({free_memory_mb:.2f} MB free)")
            return False
        
        logger.info(f"CUDA available with {free_memory_mb:.2f} MB free memory")
        return True
    except Exception as e:
        logger.warning(f"Error checking CUDA: {e}")
        return False

class CSMModelLoader:
    """
    Handles loading and using the CSM model with proper fallback mechanisms.
    """
    
    def __init__(self, model_path=None, device="auto"):
        """
        Initialize the model loader.
        
        Args:
            model_path: Path to model checkpoint or None to download from HF
            device: 'cuda', 'cpu', or 'auto' (to choose best available)
        """
        self.model_path = model_path
        self.model = None
        self.loaded_device = None
        
        # Determine the device to use
        if device == "auto":
            if is_cuda_available():
                self.target_device = "cuda"
            else:
                self.target_device = "cpu"
        else:
            self.target_device = device
        
        logger.info(f"Will attempt to load model on {self.target_device}")
    
    def load_model(self, force_cpu=False):
        """
        Load the CSM model with fallback to CPU if CUDA fails.
        
        Args:
            force_cpu: Force loading on CPU regardless of target device
            
        Returns:
            The loaded model or raises ModelNotAvailableError
        """
        if self.model is not None and not force_cpu:
            logger.info(f"Model already loaded on {self.loaded_device}")
            return self.model
        
        # Download model if needed
        if self.model_path is None or not os.path.exists(self.model_path):
            try:
                logger.info("Downloading model from HuggingFace Hub")
                self.model_path = hf_hub_download(repo_id="sesame/csm-1b", filename="ckpt.pt")
                logger.info(f"Model downloaded to {self.model_path}")
            except Exception as e:
                logger.error(f"Failed to download model: {e}")
                raise ModelNotAvailableError(f"Failed to download model: {e}")
        
        # Try preferred device first
        device_to_try = "cpu" if force_cpu else self.target_device
        
        try:
            logger.info(f"Loading model on {device_to_try}")
            
            # Use our standalone implementation
            from .csm_standalone import load_csm_1b
            
            # Actually load the model
            self.model = load_csm_1b(self.model_path, device_to_try)
            self.loaded_device = device_to_try
            logger.info(f"Successfully loaded model on {device_to_try}")
            return self.model
            
        except torch.cuda.OutOfMemoryError:
            logger.warning("CUDA out of memory, falling back to CPU")
            if device_to_try == "cpu":
                # We're already trying on CPU, so this is a different issue
                raise ModelNotAvailableError("Out of memory error even on CPU")
            
            # Try loading on CPU instead
            return self.load_model(force_cpu=True)
            
        except Exception as e:
            logger.error(f"Failed to load model on {device_to_try}: {e}")
            
            # If we failed on GPU, try CPU
            if device_to_try != "cpu":
                logger.info("Attempting fallback to CPU")
                try:
                    return self.load_model(force_cpu=True)
                except Exception as cpu_e:
                    logger.error(f"CPU fallback also failed: {cpu_e}")
            
            raise ModelNotAvailableError(f"Failed to load model: {str(e)}")
    
    def generate_speech(self, text, speaker_id=0, output_path=None):
        """
        Generate speech for the provided text.
        
        Args:
            text: The text to convert to speech
            speaker_id: ID of the speaker to use
            output_path: Path to save the output audio file (optional)
            
        Returns:
            Audio tensor if output_path is None, otherwise None
        """
        if self.model is None:
            self.load_model()
        
        try:
            logger.info(f"Generating speech for text: '{text[:50]}...' with speaker {speaker_id}")
            audio = self.model.generate(
                text=text,
                speaker=speaker_id,
                context=[],  # No context for simplicity
                max_audio_length_ms=20000  # Max 20 seconds
            )
            
            if output_path:
                # Ensure output directory exists
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
                # Save audio
                logger.info(f"Saving audio to {output_path}")
                
                # Use torchaudio for saving
                import torchaudio
                torchaudio.save(output_path, audio.unsqueeze(0).cpu(), self.model.sample_rate)
            
            return audio
            
        except Exception as e:
            logger.error(f"Speech generation failed: {e}")
            raise 