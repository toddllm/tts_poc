#!/home/tdeshane/nexa_venv/bin/python3
"""
TTS Web API Server

A simple web server that serves an HTML demo page and exposes a REST API for TTS generation.
"""

import os
import sys
import json
import logging
import time
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template_string, send_from_directory
from flask_cors import CORS
from concurrent.futures import ThreadPoolExecutor
import threading

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tts_web_api")

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import the voice cloner and CSM adapter
from utils.voice_cloner import VoiceCloner
from utils.csm_adapter import CSMModelAdapter

# Initialize Flask app
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize the TTS engines
voice_cloner = VoiceCloner()
try:
    csm_adapter = CSMModelAdapter()
    csm_available = True
except Exception as e:
    logger.warning(f"CSM Model Adapter not available: {e}")
    csm_available = False

# Set up executor for background tasks
executor = ThreadPoolExecutor(max_workers=2)

# Background task dictionary to track progress
tasks = {}
task_lock = threading.Lock()

# Load voice data
VOICE_DATA_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "characters", "voices.json")
try:
    with open(VOICE_DATA_PATH, 'r') as f:
        VOICE_DATA = json.load(f)
    logger.info(f"Loaded {len(VOICE_DATA)} voice entries from {VOICE_DATA_PATH}")
except Exception as e:
    logger.error(f"Error loading voice data from {VOICE_DATA_PATH}: {e}")
    VOICE_DATA = []

# HTML template for the demo page
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Character TTS Demo</title>
    <style>
        body {
            font-family: 'Arial', sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
        }
        
        h1, h2 {
            text-align: center;
            color: #333;
        }
        
        .character-card {
            background: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            overflow: hidden;
            margin: 20px 0;
            border-left: 5px solid #4a90e2;
        }
        
        .character-header {
            padding: 15px;
            border-bottom: 1px solid #eee;
        }
        
        .character-name {
            margin: 0;
            color: #333;
        }
        
        .character-title {
            margin: 5px 0 0;
            color: #666;
            font-style: italic;
        }
        
        .character-body {
            padding: 15px;
        }
        
        .character-description {
            color: #555;
            margin-bottom: 15px;
        }
        
        .voice-info {
            display: flex;
            justify-content: space-between;
            margin-bottom: 10px;
            font-size: 0.9em;
            color: #666;
        }
        
        .voice-params {
            font-family: monospace;
            background: #f0f0f0;
            padding: 2px 5px;
            border-radius: 3px;
        }
        
        audio {
            width: 100%;
            margin: 5px 0;
        }
        
        .tts-container {
            margin-top: 15px;
            padding-top: 15px;
            border-top: 1px solid #eee;
        }
        
        .tts-input {
            width: 100%;
            height: 80px;
            padding: 10px;
            border: 1px solid #ddd;
            border-radius: 5px;
            resize: vertical;
            font-family: 'Arial', sans-serif;
            margin-bottom: 10px;
        }
        
        .tts-controls {
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .tts-generate {
            background: #4a90e2;
            color: white;
            border: none;
            padding: 8px 15px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            transition: background 0.3s ease;
        }
        
        .tts-generate:hover {
            background: #3a80d2;
        }
        
        .tts-generate:disabled {
            background: #cccccc;
            cursor: not-allowed;
        }
        
        /* Status message styles */
        .tts-status {
            margin-top: 10px;
            padding: 8px 12px;
            border-radius: 4px;
            font-size: 0.9em;
            display: none;
        }
        
        .status-starting {
            display: block;
            background-color: #e8f5e9;
            color: #2e7d32;
            border-left: 4px solid #2e7d32;
        }
        
        .status-generating {
            display: block;
            background-color: #fff3e0;
            color: #e65100;
            border-left: 4px solid #e65100;
        }
        
        .status-retrying {
            display: block;
            background-color: #fff8e1;
            color: #ff8f00;
            border-left: 4px solid #ff8f00;
        }
        
        .status-success {
            display: block;
            background-color: #e8f5e9;
            color: #2e7d32;
            border-left: 4px solid #2e7d32;
        }
        
        .status-error {
            display: block;
            background-color: #ffebee;
            color: #c62828;
            border-left: 4px solid #c62828;
        }
        
        .debug-panel {
            background: #f8f8f8;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 15px;
            margin-top: 20px;
        }
        
        .debug-panel h3 {
            margin-top: 0;
            border-bottom: 1px solid #ddd;
            padding-bottom: 10px;
        }
        
        .log-entry {
            margin: 5px 0;
            font-family: monospace;
        }
        
        .log-error {
            color: #c62828;
        }
        
        .log-info {
            color: #2e7d32;
        }
        
        .log-warn {
            color: #ff8f00;
        }
        
        .file-check-panel {
            background-color: #fffde7;
            border: 1px solid #ffd54f;
            padding: 10px;
            margin-top: 10px;
            border-radius: 4px;
        }
        
        .file-check-result {
            font-family: monospace;
            margin: 5px 0;
        }
        
        .check-success {
            color: #388e3c;
        }
        
        .check-error {
            color: #d32f2f;
        }
        
        .check-warning {
            color: #f57c00;
        }
        
        .fix-action {
            margin-top: 10px;
            padding: 10px;
            background: #e3f2fd;
            border-radius: 4px;
            border-left: 4px solid #2196f3;
        }
    </style>
</head>
<body>
    <h1>Character TTS Demo</h1>
    <p style="text-align: center;">A demonstration of character-based text-to-speech generation</p>
    
    <div class="character-card">
        <div class="character-header">
            <h3 class="character-name" id="character-name">Select a Voice</h3>
            <p class="character-title" id="character-title"></p>
        </div>
        <div class="character-body">
            <p class="character-description" id="character-description">
                Choose a voice from the dropdown below to get started.
            </p>
            
            <div class="voice-info">
                <span id="voice-gender-info">GENDER (confidence)</span>
                <span class="voice-params" id="voice-params">temp: 0.0, topk: 0</span>
            </div>
            <div class="voice-info">
                <span id="voice-style">Style: None</span>
                <span id="voice-id">Speaker ID: 0</span>
            </div>
            
            <div id="sample-audio-container">
                <p><strong>Voice Samples:</strong></p>
                <div id="select-voice-container">
                    <select id="voice-selector">
                        <option value="">Select a voice...</option>
                    </select>
                </div>
                <audio id="sample-audio" controls>
                    <source src="" type="audio/wav">
                    Your browser does not support the audio element.
                </audio>
            </div>
            
            <div class="tts-container">
                <div>
                    <label for="device">Processing Device:</label>
                    <select id="device">
                        <option value="auto">Auto (CUDA if available, else CPU)</option>
                        <option value="cuda">CUDA (GPU)</option>
                        <option value="cpu">CPU</option>
                    </select>
                </div>
                
                <p><strong>Generate New Speech:</strong></p>
                <textarea class="tts-input" id="tts-text" placeholder="Enter text for this character to speak...">Welcome to the world of Aetheria, where magic flows like water and danger lurks around every corner.</textarea>
                <div class="tts-controls">
                    <button class="tts-generate" id="generate-btn">Generate Speech</button>
                    <div>
                        <span class="loading" id="loading-indicator" style="display: none;">Processing...</span>
                    </div>
                </div>
                <div class="tts-status" id="status-message">Waiting to start...</div>
                <div id="generated-audio-container" style="display: none; margin-top: 10px;">
                    <p><strong>Generated Speech:</strong></p>
                    <audio id="generated-audio" controls>
                        <source src="" type="audio/wav">
                        Your browser does not support the audio element.
                    </audio>
                </div>
            </div>
        </div>
    </div>
    
    <div class="file-check-panel" id="file-check-panel" style="display: none;">
        <h3>File Accessibility Checks</h3>
        <div id="file-check-results"></div>
        <div class="fix-action" id="fix-action" style="display: none;"></div>
    </div>
    
    <div class="debug-panel">
        <h3>Debug Information</h3>
        <div id="debug-logs"></div>
    </div>
    
    <script>
        // Voice data that will be loaded from the server
        let voiceData = [];
        
        // Function to log debug messages
        function logDebug(message, type = 'info') {
            const logContainer = document.getElementById('debug-logs');
            const logEntry = document.createElement('div');
            logEntry.className = `log-entry log-${type}`;
            
            const timestamp = new Date().toISOString().substring(11, 23);
            logEntry.textContent = `[${timestamp}] ${message}`;
            
            logContainer.prepend(logEntry);
            console.log(`[DEBUG] ${message}`);
        }
        
        // Function to update character information based on voice selection
        function updateCharacterInfo(voiceId) {
            const voice = voiceData.find(v => v.file_path === voiceId);
            if (!voice) return;
            
            // Extract information from voice data
            const speakerId = voice.speaker_id;
            const gender = voice.gender;
            const style = voice.style || "standard";
            const temp = voice.temperature;
            const topk = voice.topk;
            
            // Use character information from voice data
            const characterName = voice.character_name || `Speaker ${speakerId}`;
            const characterTitle = voice.character_role || `${gender.charAt(0).toUpperCase() + gender.slice(1)} Voice Artist`;
            const characterDescription = voice.character_description || 
                `A professionally trained ${gender} voice actor with expertise in ${style} performances.`;
            
            // Update the UI
            document.getElementById('character-name').textContent = characterName;
            document.getElementById('character-title').textContent = characterTitle;
            document.getElementById('character-description').textContent = characterDescription;
            document.getElementById('voice-gender-info').textContent = `${gender.toUpperCase()} (${voice.gender_confidence || 95}% confidence)`;
            document.getElementById('voice-params').textContent = `temp: ${temp}, topk: ${topk}`;
            document.getElementById('voice-style').textContent = `Style: ${style}`;
            document.getElementById('voice-id').textContent = `Speaker ID: ${speakerId}`;
            
            // Update sample audio
            const sampleAudio = document.getElementById('sample-audio');
            sampleAudio.src = voiceId;
            sampleAudio.load();
            
            logDebug(`Updated character information for: ${characterName}`);
        }
        
        // Function to check if a file exists by making a HEAD request
        async function checkFileExists(url) {
            try {
                const response = await fetch(url, { method: 'HEAD' });
                return {
                    exists: response.ok,
                    status: response.status,
                    statusText: response.statusText,
                    contentType: response.headers.get('Content-Type'),
                    contentLength: response.headers.get('Content-Length')
                };
            } catch (error) {
                return {
                    exists: false,
                    error: error.message
                };
            }
        }
        
        // Function to add file check result
        function addFileCheckResult(message, status) {
            document.getElementById('file-check-panel').style.display = 'block';
            const resultsContainer = document.getElementById('file-check-results');
            const resultEntry = document.createElement('div');
            resultEntry.className = `file-check-result check-${status}`;
            resultEntry.textContent = message;
            resultsContainer.appendChild(resultEntry);
        }
        
        // Perform comprehensive file checks
        async function performFileChecks(audioPath) {
            const fileCheckPanel = document.getElementById('file-check-panel');
            const fixAction = document.getElementById('fix-action');
            fileCheckPanel.style.display = 'block';
            document.getElementById('file-check-results').innerHTML = '';
            fixAction.style.display = 'none';
            fixAction.innerHTML = '';
            
            // Normalize path
            const normalizedPath = audioPath.startsWith('/') ? audioPath : '/' + audioPath;
            const filename = normalizedPath.split('/').pop();
            
            // Check the original path
            logDebug(`Checking file accessibility at: ${audioPath}`);
            const fileCheck = await checkFileExists(audioPath);
            
            if (fileCheck.exists) {
                addFileCheckResult(`✅ File is accessible at ${audioPath}`, 'success');
                addFileCheckResult(`   Content-Type: ${fileCheck.contentType}`, 'info');
                addFileCheckResult(`   Content-Length: ${fileCheck.contentLength} bytes`, 'info');
                return true;
            } else {
                addFileCheckResult(`❌ File not accessible at ${audioPath}: ${fileCheck.status} ${fileCheck.statusText || fileCheck.error}`, 'error');
                
                // Try with a different base path
                const altPath = `/audio/${filename}`;
                logDebug(`Trying alternate path: ${altPath}`);
                const altCheck = await checkFileExists(altPath);
                
                if (altCheck.exists) {
                    addFileCheckResult(`✅ File is accessible at alternate path: ${altPath}`, 'success');
                    addFileCheckResult(`   Content-Type: ${altCheck.contentType}`, 'info');
                    addFileCheckResult(`   Content-Length: ${altCheck.contentLength} bytes`, 'info');
                    
                    // Show fix action
                    fixAction.style.display = 'block';
                    fixAction.innerHTML = `<p><strong>Fix:</strong> Use this alternate URL instead: <code>${altPath}</code></p>
                                          <button id="use-alt-path">Use This Path</button>`;
                    
                    document.getElementById('use-alt-path').addEventListener('click', function() {
                        document.getElementById('generated-audio').src = altPath;
                        document.getElementById('generated-audio').load();
                        document.getElementById('generated-audio-container').style.display = 'block';
                        logDebug(`Updated audio source to alternate path: ${altPath}`, 'info');
                    });
                    
                    return true;
                }
                
                // Give up - propose testing with curl
                addFileCheckResult(`❌ File not found at any tested path`, 'error');
                fixAction.style.display = 'block';
                fixAction.innerHTML = `<p><strong>Debugging suggestion:</strong> Check the server with:</p>
                                      <pre>curl -I "http://${location.host}/${normalizedPath.substring(1)}"</pre>`;
                
                return false;
            }
        }
        
        // Function to generate TTS using the server API
        async function generateTTS(voicePath, text, device) {
            logDebug(`Generating TTS for voice: ${voicePath}`);
            logDebug(`Text: ${text}`);
            logDebug(`Device: ${device}`);
            
            try {
                // Call the TTS API endpoint
                logDebug(`Sending request to /api/tts`);
                const response = await fetch('/api/tts', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        voice_path: voicePath,
                        text: text,
                        device: device
                    })
                });
                
                if (!response.ok) {
                    const errorText = await response.text();
                    logDebug(`HTTP error! status: ${response.status}, response: ${errorText}`, 'error');
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                logDebug(`Got response: ${JSON.stringify(data)}`);
                
                if (data.success) {
                    logDebug(`Audio generated at: ${data.output_file}`);
                    logDebug(`Generation time: ${data.generation_time_ms}ms`);
                    return data.output_file;
                } else {
                    logDebug(`API returned error: ${data.error || 'Unknown error'}`, 'error');
                    throw new Error(data.error || 'Unknown error occurred');
                }
            } catch (error) {
                logDebug(`Error calling TTS API: ${error.message}`, 'error');
                throw error;
            }
        }
        
        // Load voice data from server
        async function loadVoiceData() {
            logDebug('Loading voice data from server...');
            
            try {
                const response = await fetch('/api/voices');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                voiceData = await response.json();
                logDebug(`Loaded ${voiceData.length} voice entries`);
                
                // Populate voice selector
                const voiceSelector = document.getElementById('voice-selector');
                
                // Clear existing options (except the first one)
                while (voiceSelector.options.length > 1) {
                    voiceSelector.remove(1);
                }
                
                // Add voices grouped by gender and speaker
                const maleVoices = voiceData.filter(v => v.gender === 'male');
                const femaleVoices = voiceData.filter(v => v.gender === 'female');
                
                if (maleVoices.length > 0) {
                    const maleGroup = document.createElement('optgroup');
                    maleGroup.label = 'Male Voices';
                    
                    maleVoices.forEach(voice => {
                        const option = document.createElement('option');
                        option.value = voice.file_path;
                        option.textContent = `${voice.character_name || `Speaker ${voice.speaker_id}`} - ${voice.style} (${voice.temperature}, ${voice.topk})`;
                        maleGroup.appendChild(option);
                    });
                    
                    voiceSelector.appendChild(maleGroup);
                }
                
                if (femaleVoices.length > 0) {
                    const femaleGroup = document.createElement('optgroup');
                    femaleGroup.label = 'Female Voices';
                    
                    femaleVoices.forEach(voice => {
                        const option = document.createElement('option');
                        option.value = voice.file_path;
                        option.textContent = `${voice.character_name || `Speaker ${voice.speaker_id}`} - ${voice.style} (${voice.temperature}, ${voice.topk})`;
                        femaleGroup.appendChild(option);
                    });
                    
                    voiceSelector.appendChild(femaleGroup);
                }
                
                logDebug('Voice selector populated');
            } catch (error) {
                logDebug(`Error loading voice data: ${error.message}`, 'error');
            }
        }
        
        // Run server diagnostic
        async function runDiagnostic() {
            logDebug('Running server diagnostic...');
            
            try {
                const response = await fetch('/api/diagnostic');
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                
                const data = await response.json();
                logDebug('Diagnostic results:');
                
                // Log system info
                if (data.system) {
                    logDebug(`System: ${JSON.stringify(data.system)}`);
                }
                
                // Log torch info
                if (data.torch) {
                    logDebug(`PyTorch: ${JSON.stringify(data.torch)}`);
                }
                
                // Log voice cloner info
                if (data.voice_cloner) {
                    logDebug(`Voice Cloner: ${JSON.stringify(data.voice_cloner)}`);
                }
                
                // Log path checks
                if (data.path_checks) {
                    logDebug(`Path Checks: ${JSON.stringify(data.path_checks)}`);
                }
                
                logDebug(`Status: ${data.status}`);
            } catch (error) {
                logDebug(`Error running diagnostic: ${error.message}`, 'error');
            }
        }
        
        // Update status message
        function updateStatus(message, status) {
            const statusElement = document.getElementById('status-message');
            statusElement.textContent = message;
            statusElement.className = 'tts-status';
            
            if (status) {
                statusElement.classList.add(`status-${status}`);
            }
            
            statusElement.style.display = 'block';
        }
        
        // Document ready
        document.addEventListener('DOMContentLoaded', () => {
            logDebug('Page loaded, initializing...');
            
            // Load voice data
            loadVoiceData();
            
            // Set up voice selector change event
            const voiceSelector = document.getElementById('voice-selector');
            voiceSelector.addEventListener('change', function() {
                if (this.value) {
                    updateCharacterInfo(this.value);
                }
            });
            
            // Set up generate button click event
            const generateBtn = document.getElementById('generate-btn');
            generateBtn.addEventListener('click', async function() {
                const textInput = document.getElementById('tts-text');
                const text = textInput.value.trim();
                
                if (!text) {
                    alert('Please enter some text to generate speech.');
                    return;
                }
                
                const voicePath = document.getElementById('voice-selector').value;
                if (!voicePath) {
                    alert('Please select a voice first.');
                    return;
                }
                
                const device = document.getElementById('device').value;
                const loadingIndicator = document.getElementById('loading-indicator');
                const generatedAudioContainer = document.getElementById('generated-audio-container');
                const generatedAudio = document.getElementById('generated-audio');
                
                // Reset file check panel
                document.getElementById('file-check-panel').style.display = 'none';
                document.getElementById('file-check-results').innerHTML = '';
                
                // Show loading indicator and update status
                loadingIndicator.style.display = 'inline-block';
                updateStatus('Starting TTS generation...', 'starting');
                generateBtn.disabled = true;
                
                try {
                    // Check server health
                    logDebug('Checking server health...');
                    try {
                        const healthCheck = await fetch('/api/health');
                        if (!healthCheck.ok) {
                            logDebug('Server health check failed', 'error');
                            updateStatus('Server may be down. Please wait a moment and try again.', 'error');
                            return;
                        }
                        logDebug('Server is healthy');
                    } catch (error) {
                        logDebug('Cannot connect to server', 'error');
                        updateStatus('Cannot connect to server. Please ensure it is running.', 'error');
                        return;
                    }
                    
                    // Generate TTS
                    updateStatus('Generating speech...', 'generating');
                    const outputPath = await generateTTS(voicePath, text, device);
                    
                    // Update audio source and display player
                    const audioUrl = `/audio/${outputPath.split('/').pop()}`;
                    generatedAudio.src = audioUrl;
                    generatedAudio.load();
                    generatedAudioContainer.style.display = 'block';
                    
                    // Update status
                    updateStatus('Speech generated successfully!', 'success');
                    
                    // Perform file checks
                    await performFileChecks(audioUrl);
                } catch (error) {
                    logDebug(`TTS generation failed: ${error.message}`, 'error');
                    updateStatus(`Error: ${error.message}`, 'error');
                } finally {
                    // Hide loading indicator and re-enable button
                    loadingIndicator.style.display = 'none';
                    generateBtn.disabled = false;
                }
            });
            
            // Add diagnostic button
            const debugPanel = document.querySelector('.debug-panel');
            const diagnosticSection = document.createElement('div');
            diagnosticSection.style.marginTop = '20px';
            diagnosticSection.style.borderTop = '1px solid #ddd';
            diagnosticSection.style.paddingTop = '10px';
            diagnosticSection.innerHTML = `
                <h3>Server Diagnostics</h3>
                <button id="run-diagnostic" class="tts-generate">Run Server Diagnostic</button>
            `;
            debugPanel.appendChild(diagnosticSection);
            
            // Set up diagnostic button click event
            document.getElementById('run-diagnostic').addEventListener('click', runDiagnostic);
        });
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    """Serve the demo page."""
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/voices', methods=['GET'])
def get_voices():
    """Return the list of available voices."""
    return jsonify(VOICE_DATA)

@app.route('/api/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({'status': 'healthy'})

@app.route('/api/generate', methods=['POST'])
def generate_speech():
    """Generate speech from text."""
    text = request.json.get('text', '')
    voice_path = request.json.get('voice', '')
    device = request.json.get('device', 'auto')
    model = request.json.get('model', 'simple')
    
    if not text:
        return jsonify({"error": "Text is required"}), 400
    
    # For very short texts in testing, default to CPU to avoid GPU overhead
    if len(text) < 5 and device == "auto":
        device = "cpu"
        logger.info("Short text detected, using CPU for efficiency")
    
    try:
        # Create a unique task ID
        task_id = str(int(time.time() * 1000))
        
        with task_lock:
            tasks[task_id] = {
                "status": "pending",
                "progress": 0,
                "error": None,
                "output": None,
                "text_length": len(text)
            }
        
        # Submit the generation task to run in the background
        executor.submit(
            perform_generation, 
            task_id=task_id,
            text=text,
            voice_path=voice_path,
            device=device,
            model=model
        )
        
        return jsonify({"task_id": task_id})
    
    except Exception as e:
        logger.exception(f"Error submitting generation task: {e}")
        return jsonify({"error": str(e)}), 500

def perform_generation(task_id, text, voice_path, device, model):
    """Perform speech generation in a background thread."""
    try:
        with task_lock:
            if task_id not in tasks:
                return
            
            tasks[task_id]["status"] = "running"
            tasks[task_id]["progress"] = 10
        
        # Short text optimization
        is_short_text = len(text) < 10
        
        # Validate the voice path
        if voice_path:
            if voice_path.startswith('input/'):
                voice_path = os.path.join(script_dir, 'voices', voice_path)
            elif not os.path.isabs(voice_path):
                voice_path = os.path.join(script_dir, 'voices', 'input', voice_path)
        
        with task_lock:
            tasks[task_id]["progress"] = 20
        
        # Check if the selected model is available
        if model == "csm" and not csm_available:
            raise ValueError("CSM model is not available")
        
        # Choose the appropriate model
        if model == "csm":
            logger.info(f"Generating speech with CSM model: '{text}'")
            output_path = csm_adapter.generate_speech(text, voice_path, device)
        else:
            logger.info(f"Generating speech with simple model: '{text}'")
            output_path = voice_cloner.generate_speech(text, voice_path, device)
        
        with task_lock:
            tasks[task_id]["progress"] = 90
            
        if output_path and os.path.exists(output_path):
            # Get relative path for frontend
            rel_path = os.path.relpath(output_path, os.path.join(script_dir, 'voices'))
            rel_path = rel_path.replace('\\', '/')  # Handle Windows paths
            
            with task_lock:
                tasks[task_id]["status"] = "complete"
                tasks[task_id]["progress"] = 100
                tasks[task_id]["output"] = rel_path
                
                # Add generation time information for diagnostics
                tasks[task_id]["generation_time"] = time.time() - tasks[task_id].get("start_time", time.time())
        else:
            with task_lock:
                tasks[task_id]["status"] = "error"
                tasks[task_id]["progress"] = 100
                tasks[task_id]["error"] = "Failed to generate speech"
    
    except Exception as e:
        logger.exception(f"Error during speech generation: {e}")
        with task_lock:
            if task_id in tasks:
                tasks[task_id]["status"] = "error"
                tasks[task_id]["progress"] = 100
                tasks[task_id]["error"] = str(e)

@app.route('/audio/<filename>')
def serve_audio(filename):
    """Serve generated audio files."""
    output_dir = voice_cloner.output_dir
    return send_from_directory(output_dir, filename)

@app.route('/api/diagnostic', methods=['GET'])
def diagnostic():
    """Run a diagnostic check on the TTS system."""
    try:
        import torch
        import platform
        import psutil
        
        # Basic system info
        system_info = {
            'platform': platform.platform(),
            'python_version': platform.python_version(),
            'cpu_count': psutil.cpu_count(logical=False),
            'logical_cpu_count': psutil.cpu_count(logical=True),
            'memory_total_gb': round(psutil.virtual_memory().total / (1024**3), 2),
            'memory_available_gb': round(psutil.virtual_memory().available / (1024**3), 2)
        }
        
        # PyTorch and CUDA info
        torch_info = {
            'torch_version': torch.__version__,
            'cuda_available': torch.cuda.is_available(),
            'cuda_device_count': torch.cuda.device_count() if torch.cuda.is_available() else 0,
        }
        
        # Add CUDA device info if available
        if torch.cuda.is_available():
            device = torch.cuda.current_device()
            free_memory = torch.cuda.get_device_properties(device).total_memory - torch.cuda.memory_allocated(device)
            free_memory_mb = free_memory / (1024 * 1024)
            torch_info['cuda_device_name'] = torch.cuda.get_device_name(device)
            torch_info['cuda_device_capability'] = torch.cuda.get_device_capability(device)
            torch_info['cuda_free_memory_mb'] = round(free_memory_mb, 2)
        
        # Voice cloner info
        voice_cloner_info = {
            'input_dir': voice_cloner.input_voice_dir,
            'output_dir': voice_cloner.output_dir,
            'input_files': len([f for f in os.listdir(voice_cloner.input_voice_dir) if f.endswith('.wav')]),
            'output_files': len([f for f in os.listdir(voice_cloner.output_dir) if f.endswith('.wav')])
        }
        
        # File paths check
        path_checks = {
            'input_dir_exists': os.path.exists(voice_cloner.input_voice_dir),
            'output_dir_exists': os.path.exists(voice_cloner.output_dir),
            'input_dir_writable': os.access(voice_cloner.input_voice_dir, os.W_OK),
            'output_dir_writable': os.access(voice_cloner.output_dir, os.W_OK)
        }
        
        return jsonify({
            'system': system_info,
            'torch': torch_info,
            'voice_cloner': voice_cloner_info,
            'path_checks': path_checks,
            'status': 'healthy'
        })
    
    except Exception as e:
        logger.exception("Error running diagnostic")
        return jsonify({'error': str(e), 'status': 'error'}), 500

@app.route('/api/status/<task_id>')
def get_task_status(task_id):
    """Get the status of a generation task."""
    with task_lock:
        if task_id not in tasks:
            return jsonify({"error": "Task not found"}), 404
        
        return jsonify(tasks[task_id])

@app.route('/api/diagnostics')
def get_diagnostics():
    """Get system diagnostics information."""
    try:
        # Check CUDA availability
        import torch
        
        cuda_available = torch.cuda.is_available()
        cuda_details = {}
        
        if cuda_available:
            device = torch.cuda.current_device()
            cuda_details = {
                "device_count": torch.cuda.device_count(),
                "current_device": device,
                "device_name": torch.cuda.get_device_name(device),
                "total_memory_mb": torch.cuda.get_device_properties(device).total_memory / (1024 * 1024),
                "allocated_memory_mb": torch.cuda.memory_allocated(device) / (1024 * 1024),
                "free_memory_mb": (torch.cuda.get_device_properties(device).total_memory - torch.cuda.memory_allocated(device)) / (1024 * 1024)
            }
        
        # Get voice sample info
        input_dir = os.path.join(script_dir, "voices", "input")
        output_dir = os.path.join(script_dir, "voices", "output")
        
        input_count = 0
        output_count = 0
        
        if os.path.exists(input_dir):
            input_count = len([f for f in os.listdir(input_dir) if f.endswith('.wav')])
        
        if os.path.exists(output_dir):
            output_count = len([f for f in os.listdir(output_dir) if f.endswith('.wav')])
        
        # Get model info
        csm_info = {
            "available": csm_available,
            "script_path": os.path.join(script_dir, "utils", "csm_adapter.py"),
            "movie_maker_path_exists": os.path.exists("/home/tdeshane/movie_maker")
        }
        
        return jsonify({
            "cuda": {
                "available": cuda_available,
                "details": cuda_details
            },
            "voices": {
                "input_count": input_count,
                "output_count": output_count
            },
            "models": {
                "simple": {
                    "available": True
                },
                "csm": csm_info
            }
        })
    except Exception as e:
        logger.exception(f"Error getting diagnostics: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Ensure the output directory exists
    os.makedirs(voice_cloner.output_dir, exist_ok=True)
    
    # Log startup information
    logger.info(f"Starting TTS Web API server")
    logger.info(f"Input voice directory: {voice_cloner.input_voice_dir}")
    logger.info(f"Output voice directory: {voice_cloner.output_dir}")
    
    # Start the server
    app.run(host='0.0.0.0', port=9000, debug=True) 