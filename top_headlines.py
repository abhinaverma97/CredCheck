# top_headlines.py
import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# NewsAPI endpoint and API key
API_KEY = os.environ.get('NEWS_API_KEY', '')
BASE_URL = "https://newsapi.org/v2/top-headlines"

# Check if API key is available
if not API_KEY:
    print("Warning: NewsAPI key is missing. Please check your .env file.")

def fetch_headlines():
    # Check if API key is configured
    if not API_KEY:
        return {"error": "NewsAPI key is not configured. Please set the NEWS_API_KEY environment variable."}

    # Parameters for the API request
    params = {
        "country": "us",  # Change 'us' to other country codes as needed
        "apiKey": API_KEY,
        "pageSize": 10,    # Fetch only 10 news articles
    }

    try:
        response = requests.get(BASE_URL, params=params)
        if response.status_code == 200:
            news_data = response.json()
            if news_data.get("status") == "ok":
                articles = news_data.get("articles", [])
                headlines = [article['title'] for article in articles if 'title' in article]
                return headlines
            else:
                return {"error": f"NewsAPI Error: {news_data.get('message', 'Unknown error')}"}
        elif response.status_code == 401:
            return {"error": "Invalid NewsAPI key. Please check your API key configuration."}
        else:
            return {"error": f"HTTP Error: {response.status_code} - {response.text}"}
    except requests.exceptions.RequestException as e:
        return {"error": f"Request Error: {str(e)}"}

# Alias for backward compatibility
fetch_top_headlines = fetch_headlines
