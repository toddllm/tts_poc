#!/home/tdeshane/nexa_venv/bin/python3
"""
Create a voice data JSON file for the TTS demo.
"""

import os
import json
import re

# Input directory with voice samples
input_dir = "/home/tdeshane/tts_poc/voices/input"

# Output JSON file
output_file = "/home/tdeshane/tts_poc/characters/voices.json"

# Regular expression to extract information from the filename
pattern = r"speaker_(\d+)_temp_(\d+\.\d+)_topk_(\d+)_(.+)"

# List of voice data
voice_data = []

# Get all .wav files in the input directory
for filename in sorted(os.listdir(input_dir)):
    if filename.endswith(".wav"):
        file_path = f"voices/input/{filename}"
        base_filename = filename[:-4]  # Remove .wav extension
        
        # Extract information using the pattern
        match = re.match(pattern, base_filename)
        if match:
            speaker_id = match.group(1)
            temp = match.group(2)
            topk = match.group(3)
            style = match.group(4)
            
            # Determine gender based on speaker ID (even = female, odd = male)
            # This is just a simple rule for demo purposes
            gender = "female" if int(speaker_id) % 2 == 0 else "male"
            
            # Add to voice data
            voice_data.append({
                "filename": base_filename,
                "file_path": file_path,
                "gender": gender,
                "gender_confidence": 95,
                "speaker_id": speaker_id,
                "temperature": temp,
                "topk": topk,
                "style": style.replace("_", " ")
            })

# Write to JSON file
with open(output_file, "w") as f:
    json.dump(voice_data, f, indent=2)

print(f"Voice data saved to {output_file} with {len(voice_data)} entries.") 