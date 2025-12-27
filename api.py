from flask import Flask, request, jsonify
import cloudscraper
import json
import time
import re
from urllib.parse import urlparse, parse_qs, unquote
import gzip
import zstandard as zstd
import brotli
from threading import Thread, Lock
import uuid

app = Flask(__name__)

class SpotMateAPI:
    def __init__(self):
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'android',
                'mobile': True
            }
        )
        self.base_url = "https://spotmate.online"
        self.session_lock = Lock()
        
    def init_session(self):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; V2434) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.35 Mobile Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Accept-Language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'sec-ch-ua': '"Android WebView";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?1',
            'sec-ch-ua-platform': '"Android"',
            'sec-fetch-site': 'none',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
            'upgrade-insecure-requests': '1'
        }
        
        with self.session_lock:
            try:
                response = self.scraper.get(f'{self.base_url}/en1', headers=headers, timeout=30)
                
                if response.status_code == 200:
                    session_cookies = response.cookies.get_dict()
                    
                    csrf_match = re.search(r'name="csrf-token"\s+content="([^"]+)"', response.text)
                    csrf_token = csrf_match.group(1) if csrf_match else None
                    
                    return {
                        'success': True,
                        'cookies': session_cookies,
                        'csrf_token': csrf_token
                    }
                else:
                    return {
                        'success': False,
                        'error': f'Status code: {response.status_code}'
                    }
            except Exception as e:
                return {
                    'success': False,
                    'error': str(e)
                }
        
    def get_track_data(self, spotify_url, csrf_token, cookies):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; V2434) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.35 Mobile Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Content-Type': 'application/json',
            'sec-ch-ua-platform': '"Android"',
            'x-csrf-token': csrf_token,
            'sec-ch-ua': '"Android WebView";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?1',
            'origin': self.base_url,
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': f'{self.base_url}/en1',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'priority': 'u=1, i'
        }
        
        payload = {'spotify_url': spotify_url}
        
        try:
            response = self.scraper.post(
                f'{self.base_url}/getTrackData',
                json=payload,
                headers=headers,
                cookies=cookies,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json()
                }
            else:
                return {
                    'success': False,
                    'error': f'Status code: {response.status_code}'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        
    def convert_track(self, spotify_url, csrf_token, cookies):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Linux; Android 15; V2434) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.7499.35 Mobile Safari/537.36',
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Content-Type': 'application/json',
            'sec-ch-ua-platform': '"Android"',
            'x-csrf-token': csrf_token,
            'sec-ch-ua': '"Android WebView";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
            'sec-ch-ua-mobile': '?1',
            'origin': self.base_url,
            'sec-fetch-site': 'same-origin',
            'sec-fetch-mode': 'cors',
            'sec-fetch-dest': 'empty',
            'referer': f'{self.base_url}/en1',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'priority': 'u=1, i'
        }
        
        payload = {'urls': spotify_url}
        
        try:
            response = self.scraper.post(
                f'{self.base_url}/convert',
                json=payload,
                headers=headers,
                cookies=cookies,
                timeout=30
            )
            
            if response.status_code == 200:
                return {
                    'success': True,
                    'data': response.json()
                }
            else:
                return {
                    'success': False,
                    'error': f'Status code: {response.status_code}'
                }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
        
    def process_track(self, spotify_url):
        session_result = self.init_session()
        if not session_result['success']:
            return {
                'success': False,
                'error': 'Failed to initialize session',
                'details': session_result.get('error')
            }
            
        csrf_token = session_result['csrf_token']
        cookies = session_result['cookies']
        
        time.sleep(1)
        
        track_result = self.get_track_data(spotify_url, csrf_token, cookies)
        if not track_result['success']:
            return {
                'success': False,
                'error': 'Failed to get track data',
                'details': track_result.get('error')
            }
            
        time.sleep(2)
        
        convert_result = self.convert_track(spotify_url, csrf_token, cookies)
        if not convert_result['success']:
            return {
                'success': False,
                'error': 'Failed to convert track',
                'details': convert_result.get('error')
            }
            
        convert_data = convert_result['data']
        track_data = track_result['data']
        
        download_url = None
        if 'download_url' in convert_data:
            download_url = convert_data['download_url']
        elif 'url' in convert_data:
            download_url = convert_data['url']
        elif 'data' in convert_data and 'download_url' in convert_data['data']:
            download_url = convert_data['data']['download_url']
            
        if not download_url:
            return {
                'success': False,
                'error': 'Could not extract download URL'
            }
            
        return {
            'success': True,
            'track_info': track_data,
            'download_url': download_url,
            'raw_response': {
                'track_data': track_data,
                'convert_data': convert_data
            }
        }

spotmate_api = SpotMateAPI()

def validate_spotify_url(url):
    patterns = [
        r'https?://open\.spotify\.com/track/[a-zA-Z0-9]+',
        r'spotify:track:[a-zA-Z0-9]+'
    ]
    
    for pattern in patterns:
        if re.match(pattern, url):
            return True
    return False

@app.route('/', methods=['GET'])
def home():
    docs = {
        "api_name": "SpotMate Professional API",
        "version": "1.0.0",
        "description": "Professional Spotify Music Downloader API",
        "api_dev": "@ISmartCoder",
        "updates_channel": "@abirxdhackz",
        "developer": "Abir Arafat Chawdhury",
        "endpoints": {
            "/": {
                "method": "GET",
                "description": "API Documentation",
                "parameters": "None"
            },
            "/sp/dl": {
                "method": "GET",
                "description": "Download Spotify Track",
                "parameters": {
                    "url": {
                        "type": "string",
                        "required": True,
                        "description": "Spotify track URL",
                        "example": "https://open.spotify.com/track/56zZ48jdyY2oDXHVnwg5Di"
                    }
                },
                "example_request": "/sp/dl?url=https://open.spotify.com/track/56zZ48jdyY2oDXHVnwg5Di",
                "response_format": {
                    "success": "boolean",
                    "request_id": "string (UUID)",
                    "spotify_url": "string",
                    "track_info": {
                        "id": "string",
                        "name": "string",
                        "artists": "array",
                        "album": "object",
                        "duration_ms": "integer"
                    },
                    "download_url": "string",
                    "raw_response": "object",
                    "api_dev": "string",
                    "updates_channel": "string",
                    "timestamp": "integer"
                }
            }
        },
        "response_codes": {
            "200": "Success",
            "400": "Bad Request - Missing or invalid parameters",
            "500": "Internal Server Error"
        },
        "usage_examples": {
            "curl": "curl 'http://localhost:8000/sp/dl?url=https://open.spotify.com/track/56zZ48jdyY2oDXHVnwg5Di'",
            "python": "import requests\nresponse = requests.get('http://localhost:8000/sp/dl', params={'url': 'https://open.spotify.com/track/56zZ48jdyY2oDXHVnwg5Di'})\nprint(response.json())",
            "javascript": "fetch('http://localhost:8000/sp/dl?url=https://open.spotify.com/track/56zZ48jdyY2oDXHVnwg5Di').then(res => res.json()).then(data => console.log(data))"
        },
        "notes": [
            "This API uses threading for concurrent requests",
            "All responses are in JSON format",
            "Rate limiting may apply for excessive requests",
            "Download URLs are temporary and expire after some time"
        ],
        "support": {
            "telegram": "@abirxdhackz",
            "developer": "@ISmartCoder"
        }
    }
    
    return jsonify(docs), 200

@app.route('/sp/dl', methods=['GET'])
def download_spotify():
    request_id = str(uuid.uuid4())
    timestamp = int(time.time())
    
    spotify_url = request.args.get('url')
    
    if not spotify_url:
        return jsonify({
            "success": False,
            "error": "Missing required parameter: url",
            "request_id": request_id,
            "api_dev": "@ISmartCoder",
            "updates_channel": "@abirxdhackz",
            "timestamp": timestamp,
            "usage": "Add ?url=YOUR_SPOTIFY_URL to the request"
        }), 400
        
    if not validate_spotify_url(spotify_url):
        return jsonify({
            "success": False,
            "error": "Invalid Spotify URL format",
            "request_id": request_id,
            "spotify_url": spotify_url,
            "api_dev": "@ISmartCoder",
            "updates_channel": "@abirxdhackz",
            "timestamp": timestamp,
            "expected_format": "https://open.spotify.com/track/XXXXXXXXX"
        }), 400
        
    try:
        result = spotmate_api.process_track(spotify_url)
        
        if result['success']:
            response_data = {
                "success": True,
                "request_id": request_id,
                "spotify_url": spotify_url,
                "track_info": result['track_info'],
                "download_url": result['download_url'],
                "raw_response": result['raw_response'],
                "api_dev": "@ISmartCoder",
                "updates_channel": "@abirxdhackz",
                "developer": "Abir Arafat Chawdhury",
                "timestamp": timestamp,
                "message": "Track processed successfully"
            }
            return jsonify(response_data), 200
        else:
            return jsonify({
                "success": False,
                "error": result.get('error', 'Unknown error'),
                "details": result.get('details'),
                "request_id": request_id,
                "spotify_url": spotify_url,
                "api_dev": "@ISmartCoder",
                "updates_channel": "@abirxdhackz",
                "timestamp": timestamp
            }), 500
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": "Internal server error",
            "details": str(e),
            "request_id": request_id,
            "spotify_url": spotify_url,
            "api_dev": "@ISmartCoder",
            "updates_channel": "@abirxdhackz",
            "timestamp": timestamp
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({
        "status": "healthy",
        "service": "SpotMate Professional API",
        "api_dev": "@ISmartCoder",
        "updates_channel": "@abirxdhackz",
        "timestamp": int(time.time())
    }), 200

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        "success": False,
        "error": "Endpoint not found",
        "available_endpoints": ["/", "/sp/dl", "/health"],
        "api_dev": "@ISmartCoder",
        "updates_channel": "@abirxdhackz",
        "timestamp": int(time.time())
    }), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({
        "success": False,
        "error": "Internal server error",
        "api_dev": "@ISmartCoder",
        "updates_channel": "@abirxdhackz",
        "timestamp": int(time.time())
    }), 500

if __name__ == '__main__':
    print("="*70)
    print(" SpotMate Professional API Server")
    print("="*70)
    print(" Developer: Abir Arafat Chawdhury")
    print(" Telegram: @ISmartCoder")
    print(" Updates Channel: @abirxdhackz")
    print("="*70)
    print(" Server starting on http://0.0.0.0:8000")
    print(" API Documentation: http://0.0.0.0:8000/")
    print(" Download Endpoint: http://0.0.0.0:8000/sp/dl?url=SPOTIFY_URL")
    print("="*70)
    print()
    
    app.run(host='0.0.0.0', port=8000, debug=False, threaded=True)
