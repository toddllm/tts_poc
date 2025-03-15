#!/usr/bin/env python3
"""
CSM Model Adapter

A simplified adapter that connects to the actual CSM model in the movie_maker project.
This allows reusing the existing voice generation functionality while providing a cleaner interface.
"""

import os
import sys
import logging
import subprocess
import tempfile
import json
import time
import shutil
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("csm_adapter")

# Paths to the movie_maker project
MOVIE_MAKER_PATH = "/home/tdeshane/movie_maker"
VOICE_POC_PATH = os.path.join(MOVIE_MAKER_PATH, "voice_poc")
VOICE_GENERATOR_SCRIPT = os.path.join(VOICE_POC_PATH, "run_voice_generator.sh")
SCENES_OUTPUT_DIR = os.path.join(MOVIE_MAKER_PATH, "hdmy5movie_voices", "scenes")

class CSMModelAdapter:
    """
    Adapter for the CSM model from the movie_maker project.
    This provides a simpler interface to the existing voice generation functionality.
    """
    
    def __init__(self):
        """Initialize the adapter."""
        # Ensure the CSM model script exists
        if not os.path.exists(VOICE_GENERATOR_SCRIPT):
            logger.error(f"Voice generator script not found: {VOICE_GENERATOR_SCRIPT}")
            raise FileNotFoundError(f"Voice generator script not found: {VOICE_GENERATOR_SCRIPT}")
        
        # Ensure output directory exists
        os.makedirs(SCENES_OUTPUT_DIR, exist_ok=True)
        
        logger.info(f"CSM Model Adapter initialized")
        logger.info(f"Using voice generator script: {VOICE_GENERATOR_SCRIPT}")
        logger.info(f"Using output directory: {SCENES_OUTPUT_DIR}")
    
    def check_gpu_memory(self):
        """Check if CUDA is available and has enough memory."""
        try:
            # Try to import torch to check CUDA
            import torch
            if not torch.cuda.is_available():
                logger.info("CUDA not available, using CPU")
                return False, "CUDA not available"
            
            # Check available GPU memory
            device = torch.cuda.current_device()
            free_memory = torch.cuda.get_device_properties(device).total_memory - torch.cuda.memory_allocated(device)
            free_memory_mb = free_memory / (1024 * 1024)  # Convert to MB
            
            # Need at least 2 GB of free memory for the CSM model
            if free_memory_mb < 2000:
                logger.info(f"Not enough GPU memory ({free_memory_mb:.2f} MB free), using CPU")
                return False, f"Not enough GPU memory ({free_memory_mb:.2f} MB free)"
            
            logger.info(f"CUDA available with {free_memory_mb:.2f} MB free memory")
            return True, f"Using GPU with {free_memory_mb:.2f} MB free memory"
        except Exception as e:
            logger.warning(f"Error checking GPU memory: {e}")
            return False, f"Error checking GPU: {str(e)}"
    
    def generate_speech(self, text, voice_path=None, device="auto"):
        """
        Generate speech using the CSM model.
        
        Args:
            text: The text to convert to speech
            voice_path: Path to the voice sample file (or None to use default)
            device: 'cuda', 'cpu', or 'auto'
            
        Returns:
            Path to the generated audio file or None if failed
        """
        start_time = time.time()
        
        # For very short texts, add a period if missing to ensure proper TTS
        if len(text) < 10 and not text.endswith(('.', '!', '?')):
            text = text + "."
            logger.debug(f"Added period to short text: '{text}'")
        
        logger.info(f"Generating speech for text: {text}")
        
        # Use a scene ID based on timestamp to avoid collisions
        scene_id = int(time.time() * 1000) % 10000
        
        # Create a JSON prompts file in the expected format
        prompts_file = None
        try:
            # Create a temporary file for the prompts
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as temp:
                # Format as JSON with scene_id as key and text as value
                import json
                json.dump({str(scene_id): text}, temp)
                prompts_file = temp.name
            
            logger.debug(f"Created prompts file: {prompts_file}")
            
            # Determine device - for very short texts, CPU might be faster due to startup time
            if device == "auto":
                if len(text) < 5:  # For extremely short texts, CPU might be faster
                    device = "cpu"
                    logger.debug("Using CPU for very short text")
                else:
                    cuda_available, _ = self.check_gpu_memory()
                    device = "cuda" if cuda_available else "cpu"
            
            # Build the command
            cmd = [
                VOICE_GENERATOR_SCRIPT,
                "--scene", str(scene_id),
                "--device", device,
                "--output", SCENES_OUTPUT_DIR,
                "--prompts", prompts_file
            ]
            
            logger.info(f"Running voice generation with device: {device}")
            
            # Run the command
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=VOICE_POC_PATH
            )
            
            # Wait for the process to complete
            stdout, stderr = process.communicate()
            
            # Only log details if there's an error or we're at debug level
            if process.returncode != 0:
                logger.error(f"STDOUT: {stdout}")
                logger.error(f"STDERR: {stderr}")
            else:
                logger.debug(f"STDOUT: {stdout}")
                if stderr:
                    logger.debug(f"STDERR: {stderr}")
            
            # Check the return code
            if process.returncode != 0:
                logger.error(f"Voice generation failed with return code: {process.returncode}")
                
                # Check for typical errors
                if "CUDA out of memory" in stderr:
                    logger.warning("CUDA out of memory error detected")
                    if device == "cuda":
                        logger.info("CUDA failed, falling back to CPU")
                        # Recursive call with CPU device
                        return self.generate_speech(text, voice_path, device="cpu")
                
                if "No prompt found for scene" in stdout or "No prompt found for scene" in stderr:
                    logger.error("Prompt file format error detected")
                
                return None
            
            logger.info(f"Voice generation command succeeded")
            
            # Look for specific output patterns in the stdout to find the file path
            output_path = None
            for line in stdout.splitlines():
                if "Output file:" in line or "Generated file:" in line or "Saved to:" in line:
                    parts = line.split(":", 1)
                    if len(parts) == 2:
                        possible_path = parts[1].strip()
                        if os.path.exists(possible_path) and possible_path.endswith('.wav'):
                            output_path = possible_path
                            logger.debug(f"Found output path from stdout: {output_path}")
                            break
            
            # If we didn't find it in stdout, check various locations
            if not output_path or not os.path.exists(output_path):
                # Try standard patterns
                potential_paths = [
                    os.path.join(SCENES_OUTPUT_DIR, f"scene_{scene_id}.wav"),
                    os.path.join(SCENES_OUTPUT_DIR, f"scene{scene_id}.wav"),
                    os.path.join(SCENES_OUTPUT_DIR, f"{scene_id}.wav"),
                    os.path.join(VOICE_POC_PATH, f"output_{scene_id}.wav"),
                    os.path.join(VOICE_POC_PATH, f"scene_{scene_id}.wav")
                ]
                
                for path in potential_paths:
                    if os.path.exists(path):
                        output_path = path
                        logger.debug(f"Found output using pattern matching: {output_path}")
                        break
                
                # If still not found, look for any new .wav files
                if not output_path:
                    # Check if any new .wav files were created in the last 30 seconds
                    current_time = time.time()
                    newest_file = None
                    newest_time = 0
                    
                    # Check both directories
                    for check_dir in [SCENES_OUTPUT_DIR, VOICE_POC_PATH]:
                        if os.path.exists(check_dir):
                            for filename in os.listdir(check_dir):
                                filepath = os.path.join(check_dir, filename)
                                if filename.endswith('.wav') and os.path.isfile(filepath):
                                    file_mtime = os.path.getmtime(filepath)
                                    if current_time - file_mtime < 30 and file_mtime > newest_time:
                                        newest_time = file_mtime
                                        newest_file = filepath
                
                    if newest_file:
                        output_path = newest_file
                        logger.debug(f"Found newest output file: {output_path}")
            
            if not output_path or not os.path.exists(output_path):
                logger.error(f"Output file not found after exhaustive search")
                return None
            
            logger.info(f"Generated speech saved to: {output_path}")
            
            # Copy to our output directory
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            final_output = f"/home/tdeshane/tts_poc/voices/output/generated_{timestamp}.wav"
            shutil.copy2(output_path, final_output)
            
            logger.info(f"Copied output to: {final_output}")
            
            elapsed_time = time.time() - start_time
            logger.info(f"Speech generation completed in {elapsed_time:.2f} seconds")
            
            return final_output
        
        except Exception as e:
            logger.exception(f"Error generating speech: {e}")
            return None
        
        finally:
            # Clean up temporary prompts file
            if prompts_file and os.path.exists(prompts_file):
                try:
                    os.unlink(prompts_file)
                    logger.debug(f"Removed temporary prompts file: {prompts_file}")
                except Exception as e:
                    logger.warning(f"Failed to remove temporary file: {e}")

# Test code
if __name__ == "__main__":
    adapter = CSMModelAdapter()
    output = adapter.generate_speech("This is a test of the CSM model adapter. Let's see if it works!")
    if output:
        print(f"Generated speech at: {output}")
    else:
        print("Failed to generate speech") 