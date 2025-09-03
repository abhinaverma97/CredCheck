# cred_check.py

import os
import requests
from transformers import AutoTokenizer, AutoModel
import torch
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import json
from langdetect import detect
from convert_to_english import translation
from dotenv import load_dotenv
# ---------------------------
# Constants
# ---------------------------

# Load environment variables
load_dotenv()

# Get API keys from environment variables
GOOGLE_API_KEY = os.environ.get('GOOGLE_SEARCH_API_KEY', '')
CUSTOM_SEARCH_ENGINE_ID = os.environ.get('GOOGLE_SEARCH_ENGINE_ID', '')
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

# Check if required API keys are available
if not GOOGLE_API_KEY or not CUSTOM_SEARCH_ENGINE_ID or not DEEPSEEK_API_KEY:
    print("Warning: One or more required API keys are missing. Please check your .env file.")

TRUSTED_SOURCES = [
    "bbc.com", "reuters.com", "apnews.com", "snopes.com", "theguardian.com", "nytimes.com", "washingtonpost.com",
    "bbc.co.uk", "cnn.com", "forbes.com", "npr.org", "wsj.com", "time.com", "usatoday.com", "bloomberg.com",
    "thehill.com", "guardian.co.uk", "huffpost.com", "independent.co.uk", "scientificamerican.com", "wired.com",
    "nationalgeographic.com", "marketwatch.com", "businessinsider.com", "abcnews.go.com", "news.yahoo.com",
    "theverge.com", "techcrunch.com", "theatlantic.com", "axios.com", "cnbc.com", "newsweek.com", "bbc.co.uk",
    "latimes.com", "thetimes.co.uk", "sky.com", "reuters.uk", "thehindu.com", "straitstimes.com", "foreignpolicy.com",
    "dw.com", "indianexpress.com", "dailymail.co.uk", "smh.com.au", "mint.com", "livemint.com"
]

# Initialize the tokenizer and model for BERT
# It is recommended to initialize these outside of functions if reused frequently
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
model = AutoModel.from_pretrained("bert-base-uncased")

# ---------------------------
# Helper Functions
# ---------------------------

def get_embeddings(text):
    """
    Generates embeddings for the given text using BERT.

    Args:
        text (str): The input text.

    Returns:
        numpy.ndarray: The computed embeddings.
    """
    # Tokenize the input text
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    # Get model outputs
    outputs = model(**inputs)
    # Compute the mean of the last hidden states to get a fixed-size vector
    embeddings = torch.mean(outputs.last_hidden_state, dim=1)
    return embeddings.detach().numpy()

def google_search(query, num_results=5):
    """
    Performs a Google Custom Search for the given query.

    Args:
        query (str): The search query.
        num_results (int, optional): Number of search results to retrieve. Defaults to 5.

    Returns:
        list or dict: A list of search result dictionaries or an error dictionary.
    """
    url = f"https://www.googleapis.com/customsearch/v1?q={query}&key={GOOGLE_API_KEY}&cx={CUSTOM_SEARCH_ENGINE_ID}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            results = response.json().get("items", [])
            # Safely extract 'title', 'description', and 'link' using .get()
            return [
                {
                    "title": item.get("title", "No Title Available"),
                    "description": item.get("snippet", "No Description Available"),  # Replaced 'snippet' with 'description'
                    "link": item.get("link", "No URL Available")
                }
                for item in results[:num_results]
            ]
        elif response.status_code == 429:
            # API quota exceeded
            return {"error": "Google Search API quota exceeded. The system will use alternative verification methods."}
        else:
            return {"error": f"Error {response.status_code}: {response.text}"}
    except Exception as e:
        return {"error": f"Exception occurred: {str(e)}"}

def check_trusted_source(link):
    """
    Checks if the provided link is from a trusted source.

    Args:
        link (str): The URL to check.

    Returns:
        bool: True if the source is trusted, False otherwise.
    """
    for source in TRUSTED_SOURCES:
        if source in link:
            return True
    return False

def calculate_similarity(headline, search_results):
    """
    Calculates the cosine similarity between the headline and each search result.

    Args:
        headline (str): The news headline.
        search_results (list): List of search result dictionaries.

    Returns:
        list: List of similarity scores.
    """
    headline_emb = get_embeddings(headline)
    similarities = []

    for result in search_results:
        # Combine title and description for a comprehensive comparison
        result_text = result["title"] + " " + result["description"]
        result_emb = get_embeddings(result_text)
        # Calculate cosine similarity
        similarity = cosine_similarity(headline_emb, result_emb)[0][0]
        similarities.append(similarity)

    return similarities

def enhance_credibility_score(link, headline):
    """
    Enhances the credibility score based on the source and headline content.

    Args:
        link (str): The URL of the article.
        headline (str): The news headline.

    Returns:
        float: The credibility score.
    """
    credibility_score = 0

    if check_trusted_source(link):
        credibility_score += 0.5

    return credibility_score

def is_english(text):
    """Check if the given text is in English."""
    try:
        return detect(text) == 'en'
    except:
        return False

def extract_from_boxed_content(content):
    """
    Extract content from DeepSeek's \boxed{} format
    
    Args:
        content (str): The raw content from DeepSeek response
        
    Returns:
        str: Cleaned content without the \boxed{} wrapper
    """
    if content.startswith("\\boxed{") and content.endswith("}"):
        # Remove \boxed{ and } from the content
        cleaned_content = content[7:-1]
        
        # If content is wrapped in quotes, remove them
        if cleaned_content.startswith('"') and cleaned_content.endswith('"'):
            cleaned_content = cleaned_content[1:-1]
            
        return cleaned_content
    
    return content

def deepseek_check(article_text):
    """
    Second layer: Uses DeepSeek AI to check if the news is real or fake.
    
    Args:
        article_text (str): The news article or headline to analyze.
        
    Returns:
        dict: Dictionary containing the verdict and full response.
    """
    try:
        # Check if text is in English and translate if needed
        if not is_english(article_text):
            translated_text = translation(article_text)
            # Store the original and translated text
            original_text = article_text
            article_text = translated_text
        
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps({
                "model": "deepseek/deepseek-r1-zero:free",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a fact-checking AI that determines whether a news article is real or fake based on reliable sources and only answer with 'Fake' or 'Real'. You should not provide any additional information or context. Your answer should be concise and to the point."
                    },
                    {
                        "role": "user",
                        "content": f"Analyze the credibility of this news article:\n\n{article_text}\n\nIs this news likely to be fake or real? Provide an explanation."
                    }
                ],
            })
        )

        result = response.json()  # Convert response to dictionary
        
        # Check if the response has the expected structure
        if "choices" not in result or len(result["choices"]) == 0:
            return {
                "error": "No choices in API response",
                "is_fake": None,
                "verdict": "Error in DeepSeek analysis"
            }
            
        if "message" not in result["choices"][0]:
            return {
                "error": "No message in API response choice",
                "is_fake": None,
                "verdict": "Error in DeepSeek analysis"
            }
        
        # Extract and clean the verdict
        raw_verdict = result["choices"][0]["message"]["content"]  # Extract AI's response
        verdict = extract_from_boxed_content(raw_verdict)
        
        # Determine if the verdict indicates fake news
        is_fake = "fake" in verdict.lower()
        
        response_data = {
            "verdict": verdict,
            "raw_verdict": raw_verdict,
            "is_fake": is_fake,
            "full_response": result
        }
        
        # Add translation info if translation was performed
        if locals().get('original_text'):
            response_data["original_text"] = original_text
            response_data["translated"] = True
        
        return response_data
    except Exception as e:
        return {
            "error": str(e),
            "is_fake": None,
            "verdict": "Error in DeepSeek analysis"
        }

def fake_news_detector(headline):
    """
    Layered fake news detection system.
    
    Layer 1: Credibility check based on trusted sources
    Layer 2: DeepSeek AI analysis
    Layer 3: ClaimBuster API (to be handled in app.py)

    Args:
        headline (str): The news headline to analyze.

    Returns:
        dict: Dictionary containing analysis results from all available layers.
    """
    # Initialize result dictionary
    result = {
        "headline": headline,
        "layers": {}
    }
    
    # Layer 1: Credibility check based on trusted sources
    search_results = google_search(headline.strip())
    if isinstance(search_results, dict) and "error" in search_results:
        # Store error but still mark as potentially suspicious
        if "quota exceeded" in search_results["error"].lower():
            result["layers"]["credibility"] = {
                "error": search_results["error"],
                "message": "The credibility check cannot be performed due to API limits. Using other verification methods.",
                "is_fake": None  # Neutral when API is unavailable
            }
        else:
            result["layers"]["credibility"] = {"error": search_results["error"]}
    else:
        # Check if search returned any results at all
        if not search_results:
            # No search results should be considered suspicious
            result["layers"]["credibility"] = {
                "average_similarity": 0.0,
                "average_credibility": 0.0,
                "is_fake": True,  # Consider no search results as a sign of fake news
                "search_results": []
            }
        else:
            similarities = calculate_similarity(headline, search_results)
            credibility_scores = [
                enhance_credibility_score(search_result["link"], search_result["title"]) for search_result in search_results
            ]

            average_similarity = float(np.mean(similarities)) if similarities else 0
            average_credibility = float(np.mean(credibility_scores)) if credibility_scores else 0
            is_fake_by_credibility = (average_similarity < 0.78) and (average_credibility <= 0.17)
            
            result["layers"]["credibility"] = {
                "average_similarity": average_similarity,
                "average_credibility": average_credibility,
                "is_fake": is_fake_by_credibility,
                "search_results": search_results
            }
    
    # Layer 2: DeepSeek AI analysis
    deepseek_result = deepseek_check(headline)
    result["layers"]["deepseek"] = deepseek_result
    
    # NOTE: No longer determining overall fakeness here
    # Final verdict will be determined in app.py using majority rule with all 3 layers
    
    return result
