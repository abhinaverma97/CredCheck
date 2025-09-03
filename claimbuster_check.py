# claimbuster_check.py
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

API_KEY = os.environ.get('CLAIMBUSTER_API_KEY', '')
API_ENDPOINT = os.environ.get('CLAIMBUSTER_ENDPOINT', '')

# Check if API key and endpoint are available
if not API_KEY or not API_ENDPOINT:
    print("Warning: ClaimBuster API key or endpoint is missing. Please check your .env file.")

def check_claim(sentences):
    if not API_KEY or not API_ENDPOINT:
        return {"error": "ClaimBuster API key or endpoint not configured"}
        
    url = f"{API_ENDPOINT}{requests.utils.quote(sentences)}"
    headers = {"x-api-key": API_KEY}

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            return {"error": f"HTTP {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": str(e)}
    
