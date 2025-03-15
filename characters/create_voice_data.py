#!/home/tdeshane/nexa_venv/bin/python3
"""
Create a voice data JSON file for the TTS demo.
"""

import os
import json
import re
import random

# Input directory with voice samples
input_dir = "/home/tdeshane/tts_poc/voices/input"

# Output JSON file
output_file = "/home/tdeshane/tts_poc/characters/voices.json"

# Dictionary of character names by speaker ID
character_names = {
    "0": "James Cooper",
    "1": "Alex Morgan",
    "2": "Emily Winters",
    "3": "Michael Chen",
    "4": "Sophia Rodriguez",
    "5": "David Johnson",
    "6": "Olivia Parker",
    "7": "Nathan Williams"
}

# Dictionary of character professions/roles by speaker ID
character_roles = {
    "0": "Game Narrator",
    "1": "Sci-Fi Storyteller",
    "2": "AI Assistant",
    "3": "Technical Instructor",
    "4": "Virtual Guide",
    "5": "News Anchor",
    "6": "Meditation Coach",
    "7": "Adventure Narrator"
}

# Dictionary of character descriptions by speaker ID
character_descriptions = {
    "0": "A veteran voice actor known for his dynamic range and captivating storytelling ability.",
    "1": "A versatile narrator who specializes in futuristic and science fiction content.",
    "2": "A friendly and helpful voice with a calm and reassuring tone.",
    "3": "A precise and articulate speaker who excels at explaining complex topics clearly.",
    "4": "A warm and engaging voice that guides users through digital experiences.",
    "5": "A professional and authoritative voice for news and informational content.",
    "6": "A soothing voice with excellent pacing for relaxation and mindfulness content.",
    "7": "An energetic storyteller who brings adventure and excitement to any narrative."
}

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
            
            # Get character name and role from dictionaries
            character_name = character_names.get(speaker_id, f"Speaker {speaker_id}")
            character_role = character_roles.get(speaker_id, "Voice Artist")
            character_description = character_descriptions.get(speaker_id, f"A professional {gender} voice actor with expertise in various styles.")
            
            # Add to voice data
            voice_data.append({
                "filename": base_filename,
                "file_path": file_path,
                "gender": gender,
                "gender_confidence": 95,
                "speaker_id": speaker_id,
                "temperature": temp,
                "topk": topk,
                "style": style.replace("_", " "),
                "character_name": character_name,
                "character_role": character_role,
                "character_description": character_description
            })

# Write to JSON file
with open(output_file, "w") as f:
    json.dump(voice_data, f, indent=2)

print(f"Voice data saved to {output_file} with {len(voice_data)} entries.") 