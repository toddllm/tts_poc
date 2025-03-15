#!/usr/bin/env python3
"""
TTS Server

A simple web server that provides a REST API for TTS generation.
"""

import os
import sys
import json
import logging
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs, urlparse

# Add parent directory to path to allow importing from tts_poc
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.voice_cloner import VoiceCloner

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("serve_tts")

# Global voice cloner instance
cloner = None

class TTSRequestHandler(BaseHTTPRequestHandler):
    """HTTP request handler for TTS API."""
    
    def _set_headers(self, status_code=200, content_type="application/json"):
        """Set response headers."""
        self.send_response(status_code)
        self.send_header("Content-type", content_type)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
    
    def _send_json_response(self, data, status_code=200):
        """Send JSON response."""
        self._set_headers(status_code)
        self.wfile.write(json.dumps(data).encode())
    
    def _send_file_response(self, file_path, content_type="audio/wav"):
        """Send file response."""
        if not os.path.exists(file_path):
            self._send_json_response({"error": "File not found"}, 404)
            return
        
        # Get file size
        file_size = os.path.getsize(file_path)
        
        # Send headers
        self._set_headers(content_type=content_type)
        self.send_header("Content-Length", str(file_size))
        self.end_headers()
        
        # Send file content
        with open(file_path, "rb") as f:
            self.wfile.write(f.read())
    
    def _parse_post_data(self):
        """Parse POST data."""
        content_length = int(self.headers.get("Content-Length", 0))
        post_data = self.rfile.read(content_length).decode("utf-8")
        
        try:
            return json.loads(post_data)
        except json.JSONDecodeError:
            return parse_qs(post_data)
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_path = urlparse(self.path)
        path = parsed_path.path
        
        # Serve static files
        if path.startswith("/voices/"):
            file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), path[1:])
            self._send_file_response(file_path)
            return
        
        # API endpoints
        if path == "/api/health":
            self._send_json_response({"status": "ok"})
            return
        
        # Default: 404
        self._send_json_response({"error": "Not found"}, 404)
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path == "/api/tts":
            # Parse request data
            data = self._parse_post_data()
            
            # Extract parameters
            text = data.get("text", [""])[0] if isinstance(data, dict) and isinstance(data.get("text"), list) else data.get("text", "")
            voice = data.get("voice", [""])[0] if isinstance(data, dict) and isinstance(data.get("voice"), list) else data.get("voice", "")
            device = data.get("device", ["auto"])[0] if isinstance(data, dict) and isinstance(data.get("device"), list) else data.get("device", "auto")
            
            # Validate parameters
            if not text:
                self._send_json_response({"error": "Missing text parameter"}, 400)
                return
            
            # Generate speech
            try:
                logger.info(f"Generating speech for text: '{text[:50]}...'")
                output_path = cloner.generate(text=text, voice_path=voice or None, device=device)
                
                if output_path:
                    # Return success response
                    self._send_json_response({
                        "success": True,
                        "output_path": output_path,
                        "url": f"/voices/output/{os.path.basename(output_path)}"
                    })
                else:
                    # Return error response
                    self._send_json_response({
                        "success": False,
                        "error": "Failed to generate speech"
                    }, 500)
            except Exception as e:
                logger.error(f"Error generating speech: {e}")
                self._send_json_response({
                    "success": False,
                    "error": str(e)
                }, 500)
            
            return
        
        # Default: 404
        self._send_json_response({"error": "Not found"}, 404)
    
    def do_OPTIONS(self):
        """Handle OPTIONS requests (for CORS)."""
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description="Start TTS server")
    
    parser.add_argument("--host", type=str, default="0.0.0.0",
                        help="Host to bind server to")
    
    parser.add_argument("--port", type=int, default=8080,
                        help="Port to bind server to")
    
    parser.add_argument("--model", type=str, default=None,
                        help="Path to model checkpoint (optional)")
    
    parser.add_argument("--verbose", action="store_true",
                        help="Enable verbose logging")
    
    return parser.parse_args()

def main():
    """Main function."""
    global cloner
    
    args = parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("Verbose logging enabled")
    
    # Initialize voice cloner
    cloner = VoiceCloner(model_path=args.model)
    
    # Start server
    server_address = (args.host, args.port)
    httpd = HTTPServer(server_address, TTSRequestHandler)
    
    logger.info(f"Starting TTS server on {args.host}:{args.port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Stopping server...")
        httpd.server_close()
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 