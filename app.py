from flask import Flask, request, jsonify, render_template, send_from_directory, send_file
import os
from langdetect import detect
from audio_to_text import transcribe_audio
from video_to_text import transcribe_and_translate_video
from convert_to_english import translation
from cred_check import fake_news_detector, get_embeddings, calculate_similarity
from claimbuster_check import check_claim
from top_headlines import fetch_headlines, fetch_top_headlines
from img_to_text import extract_text_from_image
from database import Database
import json
import tempfile
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
from dotenv import load_dotenv
import requests
from realTimeArticle import RealTimeNewsMonitor
import atexit
import subprocess
import glob
from LiveVideoFeed import get_live_analysis_results, start_live_video_process_in_background


DEFAULT_YOUTUBE_URL = "https://www.youtube.com/watch?v=gCNeDWCI0vo"  # al jazeera


# DEFAULT_YOUTUBE_URL = "https://www.youtube.com/watch?v=sYZtOFzM78M"  # india


# DEFAULT_YOUTUBE_URL = "https://www.youtube.com/watch?v=vOTiJkg1voo"  # abc news






# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Ensure static/images directory exists
os.makedirs('static/images', exist_ok=True)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize database
try:
    db = Database()
    logger.info("Database initialized successfully")
except Exception as e:
    logger.error(f"Error initializing database: {e}")
    db = None

# Initialize the Real-Time News Monitor with a fast check interval
news_monitor = RealTimeNewsMonitor(check_interval=60, max_recent_articles=30)  # 60 seconds to quickly analyze new articles

# Start the monitor immediately 
news_monitor.start()
logger.info("Started real-time news monitoring on initialization")

# Add source diversity check to the callback function
def analyze_new_article(article):
    try:
        # Skip articles that are too short to analyze meaningfully
        if not article.get('title') or len(article.get('title', '')) < 10:
            return
        
        # Get recent articles to check source diversity
        with news_monitor.lock:
            analyzed_sources = [a.get('source') for a in news_monitor.recent_articles 
                             if a.get('analyzed', False) and a.get('source') != article.get('source')]
        
        # Only analyze if we don't have too many from the same source
        same_source_count = sum(1 for source in analyzed_sources if source == article.get('source'))
        if same_source_count > 2:  # Skip if we already have more than 2 from this source
            logger.info(f"Skipping article from {article.get('source')} to maintain source diversity")
            return
            
        # Run our fake news detection on the article title
        detection_result = fake_news_detector(article['title'])
        
        # Initialize our layers structure
        layers = {
            "credibility": detection_result.get("layers", {}).get("credibility", {}),
            "deepseek": detection_result.get("layers", {}).get("deepseek", {}),
            "claimbuster": []
        }
        
        # Add ClaimBuster analysis
        try:
            headline = article['title']
            if not is_english(headline):
                translated_headline = translation(headline)
            else:
                translated_headline = headline
            
            claimbuster_result = check_claim(translated_headline)
            
            if "error" not in claimbuster_result:
                claimbuster_results = []
                for cb_result in claimbuster_result["results"]:
                    score = cb_result["score"]
                    classification = classify_claim(score)
                    claimbuster_results.append({
                        "text": cb_result["text"],
                        "score": score,
                        "classification": classification
                    })
                layers["claimbuster"] = claimbuster_results
        except Exception as e:
            logger.error(f"Error with ClaimBuster for new article: {e}")
        
        # Now determine fakeness using majority rule
        is_fake = determine_fakeness_by_majority_rule(layers)
        
        # Update the article with the analysis results
        article['analyzed'] = True
        article['is_fake'] = is_fake
        
        # Get the credibility score if available
        if 'credibility' in detection_result.get('layers', {}):
            credibility_layer = detection_result['layers']['credibility']
            if 'score' in credibility_layer:
                article['credibility_score'] = credibility_layer['score']
        
        # Save the analysis to the database
        if db:
            db.save_analysis(
                headline=article['title'],
                is_fake=is_fake,
                credcheck_classification=classify_auth(is_fake),
                claimbuster_results=layers["claimbuster"],
                source_type="real-time"
            )
            
        logger.info(f"Analyzed real-time article: {article['title']}")
    except Exception as e:
        logger.error(f"Error in analyze_new_article: {e}")

# Register the callback function with the news monitor
news_monitor.register_callback(analyze_new_article)

# Instead of using app.before_first_request, we'll keep the monitor running for the app's lifetime
def start_news_monitor_on_startup():
    if not news_monitor.running:
        news_monitor.start()
        logger.info("Started real-time news monitoring")

# Call the function in the appropriate place
with app.app_context():
    # No need to start again - it's already started above
    pass

# Only stop on actual app shutdown, not on every request
@atexit.register
def shutdown_news_monitor():
    news_monitor.stop()
    logger.info("Stopped real-time news monitoring on application shutdown")

# Set up temporary file paths
TEMP_DIR = tempfile.gettempdir()

# Adjust temp file paths to use system temp directory
def get_temp_path(prefix, extension=""):
    return os.path.join(TEMP_DIR, f"{prefix}_{os.urandom(8).hex()}{extension}")

# Helper function to check if text is in English
def is_english(text):
    """Check if the given text is in English."""
    try:
        return detect(text) == 'en'
    except:
        return False

# Define threshold for fake news classification
SCORE_THRESHOLD = 0.66

def classify_claim(score):
    """Classify the claim based on the score."""
    return "🔴 Fake" if score < SCORE_THRESHOLD else "🟢 Real"

def classify_auth(is_fake):
    """Classify the authentication result."""
    return "🔴 Fake" if is_fake else "🟢 Real"

def determine_fakeness_by_majority_rule(layers):
    """
    Determine fakeness using majority rule from all three layers.
    Returns True if majority of available layers indicate content is fake.
    
    Args:
        layers: Dictionary containing results from all available layers.
    
    Returns:
        bool: True if majority of layers indicate fake, False otherwise.
    """
    # Count votes for each layer
    fake_votes = 0
    real_votes = 0
    
    # Layer 1: Credibility
    if "credibility" in layers:
        credibility_result = layers["credibility"]
        if credibility_result and "is_fake" in credibility_result:
            if credibility_result["is_fake"] == True:
                fake_votes += 1
            elif credibility_result["is_fake"] == False:
                real_votes += 1
            # If None, it means the layer couldn't determine, so no vote counted
    
    # Layer 2: DeepSeek
    if "deepseek" in layers:
        deepseek_result = layers["deepseek"]
        if deepseek_result and "is_fake" in deepseek_result:
            if deepseek_result["is_fake"] == True:
                fake_votes += 1
            elif deepseek_result["is_fake"] == False:
                real_votes += 1
    
    # Layer 3: ClaimBuster
    if "claimbuster" in layers and layers["claimbuster"]:
        # If more than half of claims are marked fake, count as a fake vote
        claimbuster_results = layers["claimbuster"]
        fake_claims = sum(1 for r in claimbuster_results if r.get("classification", "").startswith("🔴"))
        
        if fake_claims > len(claimbuster_results) / 2:
            fake_votes += 1
        else:
            real_votes += 1
    
    # Decide based on majority
    total_votes = fake_votes + real_votes
    
    # Special case: If no valid votes, default to not fake
    if total_votes == 0:
        return False
    
    # Return True if majority (more than half) of votes indicate fake
    return fake_votes > total_votes / 2

def get_layer_classification(layer_result, layer_name):
    """Get a formatted classification string for a specific detection layer."""
    if not layer_result or "error" in layer_result:
        return f"{layer_name}: ⚠️ Error"
    
    if layer_name == "deepseek":
        fake_status = layer_result.get("is_fake", None)
        if fake_status is None:
            return f"{layer_name}: ⚠️ Unknown"
        return f"{layer_name}: 🔴 Fake" if fake_status else f"{layer_name}: 🟢 Real"
    
    if layer_name == "credibility":
        fake_status = layer_result.get("is_fake", None)
        if fake_status is None:
            return f"{layer_name}: ⚠️ Unknown"
        return f"{layer_name}: 🔴 Fake" if fake_status else f"{layer_name}: 🟢 Real"
    
    if layer_name == "claimbuster":
        if not layer_result:
            return f"{layer_name}: ⚠️ No Results"
        # If we have multiple results, average the fakeness
        fake_count = sum(1 for r in layer_result if r.get("classification", "").startswith("🔴"))
        if fake_count > len(layer_result) / 2:
            return f"{layer_name}: 🔴 Fake"
        return f"{layer_name}: 🟢 Real"
    
    return f"{layer_name}: ⚠️ Unknown"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze_text', methods=['POST'])
def analyze_text():
    data = request.json
    headline = data.get('headline', '')
    
    if not headline:
        return jsonify({"error": "Please enter a headline."}), 400
    
    # Analyze with CredCheck
    detection_result = fake_news_detector(headline)
    
    # Initialize our response structure
    result = {
        "headline": headline,
        "layers": {
            "credibility": detection_result.get("layers", {}).get("credibility", {}),
            "deepseek": detection_result.get("layers", {}).get("deepseek", {}),
            "claimbuster": []
        },
        "layer_classifications": {}
    }
    
    # Add classifications for the first two layers
    result["layer_classifications"]["credibility"] = get_layer_classification(
        result["layers"]["credibility"], "credibility")
    result["layer_classifications"]["deepseek"] = get_layer_classification(
        result["layers"]["deepseek"], "deepseek")
    
    # Always add ClaimBuster layer now (not just if first two layers say fake)
    try:
        if not is_english(headline):
            translated_headline = translation(headline)
            result["translated_text"] = translated_headline
        else:
            translated_headline = headline
        
        claimbuster_result = check_claim(translated_headline)
        
        if "error" in claimbuster_result:
            result["layers"]["claimbuster_error"] = claimbuster_result["error"]
        else:
            claimbuster_results = []
            for cb_result in claimbuster_result["results"]:
                score = cb_result["score"]
                classification = classify_claim(score)
                claimbuster_results.append({
                    "text": cb_result["text"],
                    "score": score,
                    "classification": classification
                })
            result["layers"]["claimbuster"] = claimbuster_results
            
            # Add classification for ClaimBuster layer
            result["layer_classifications"]["claimbuster"] = get_layer_classification(
                claimbuster_results, "claimbuster")
    except Exception as e:
        logger.error(f"Error with ClaimBuster: {e}")
        result["layers"]["claimbuster_error"] = str(e)
    
    # Now determine fakeness using majority rule
    result["is_fake"] = determine_fakeness_by_majority_rule(result["layers"])
    result["credcheck_classification"] = classify_auth(result["is_fake"])
    
    # Save analysis to database
    try:
        if db:
            db.save_analysis(
                headline=headline,
                is_fake=result["is_fake"],
                credcheck_classification=result["credcheck_classification"],
                claimbuster_results=result["layers"]["claimbuster"],
                source_type="text"
            )
    except Exception as e:
        logger.error(f"Error saving analysis to database: {e}")
    
    return jsonify(result)

@app.route('/analyze_audio', methods=['POST'])
def analyze_audio():
    if 'audio_file' not in request.files:
        return jsonify({"error": "No audio file provided."}), 400
    
    audio_file = request.files['audio_file']
    temp_audio_path = get_temp_path("temp_audio", ".wav")
    audio_file.save(temp_audio_path)
    
    try:
        text = transcribe_audio(temp_audio_path)
    finally:
        if os.path.exists(temp_audio_path):
            os.remove(temp_audio_path)
    
    # Analyze with CredCheck
    detection_result = fake_news_detector(text)
    
    # Initialize our response structure
    result = {
        "transcribed_text": text,
        "layers": {
            "credibility": detection_result.get("layers", {}).get("credibility", {}),
            "deepseek": detection_result.get("layers", {}).get("deepseek", {}),
            "claimbuster": []
        },
        "layer_classifications": {}
    }
    
    # Add classifications for the first two layers
    result["layer_classifications"]["credibility"] = get_layer_classification(
        result["layers"]["credibility"], "credibility")
    result["layer_classifications"]["deepseek"] = get_layer_classification(
        result["layers"]["deepseek"], "deepseek")
    
    # Always add ClaimBuster layer now (not just if first two layers say fake)
    try:
        if not is_english(text):
            translated_text = translation(text)
            result["translated_text"] = translated_text
        else:
            translated_text = text
        
        claimbuster_result = check_claim(translated_text)
        
        if "error" in claimbuster_result:
            result["layers"]["claimbuster_error"] = claimbuster_result["error"]
        else:
            claimbuster_results = []
            for cb_result in claimbuster_result["results"]:
                score = cb_result["score"]
                classification = classify_claim(score)
                claimbuster_results.append({
                    "text": cb_result["text"],
                    "score": score,
                    "classification": classification
                })
            result["layers"]["claimbuster"] = claimbuster_results
            
            # Add classification for ClaimBuster layer
            result["layer_classifications"]["claimbuster"] = get_layer_classification(
                claimbuster_results, "claimbuster")
    except Exception as e:
        logger.error(f"Error with ClaimBuster: {e}")
        result["layers"]["claimbuster_error"] = str(e)
    
    # Now determine fakeness using majority rule
    result["is_fake"] = determine_fakeness_by_majority_rule(result["layers"])
    result["credcheck_classification"] = classify_auth(result["is_fake"])
    
    # Save analysis to database
    try:
        if db:
            db.save_analysis(
                headline=text[:200],  # Use first 200 chars of transcribed text as headline
                is_fake=result["is_fake"],
                credcheck_classification=result["credcheck_classification"],
                claimbuster_results=result["layers"]["claimbuster"],
                source_type="audio"
            )
    except Exception as e:
        logger.error(f"Error saving audio analysis to database: {e}")
    
    return jsonify(result)

@app.route('/analyze_video', methods=['POST'])
def analyze_video():
    if 'video_file' not in request.files:
        return jsonify({"error": "No video file provided."}), 400
    
    video_file = request.files['video_file']
    temp_video_path = get_temp_path("temp_video", ".mp4")
    video_file.save(temp_video_path)
    
    try:
        text = transcribe_and_translate_video(temp_video_path)
    finally:
        if os.path.exists(temp_video_path):
            os.remove(temp_video_path)
    
    # Analyze with CredCheck
    detection_result = fake_news_detector(text)
    
    # Initialize our response structure
    result = {
        "transcribed_text": text,
        "layers": {
            "credibility": detection_result.get("layers", {}).get("credibility", {}),
            "deepseek": detection_result.get("layers", {}).get("deepseek", {}),
            "claimbuster": []
        },
        "layer_classifications": {}
    }
    
    # Add classifications for the first two layers
    result["layer_classifications"]["credibility"] = get_layer_classification(
        result["layers"]["credibility"], "credibility")
    result["layer_classifications"]["deepseek"] = get_layer_classification(
        result["layers"]["deepseek"], "deepseek")
    
    # Always add ClaimBuster layer now (not just if first two layers say fake)
    try:
        if not is_english(text):
            translated_text = translation(text)
            result["translated_text"] = translated_text
        else:
            translated_text = text
        
        claimbuster_result = check_claim(translated_text)
        
        if "error" in claimbuster_result:
            result["layers"]["claimbuster_error"] = claimbuster_result["error"]
        else:
            claimbuster_results = []
            for cb_result in claimbuster_result["results"]:
                score = cb_result["score"]
                classification = classify_claim(score)
                claimbuster_results.append({
                    "text": cb_result["text"],
                    "score": score,
                    "classification": classification
                })
            result["layers"]["claimbuster"] = claimbuster_results
            
            # Add classification for ClaimBuster layer
            result["layer_classifications"]["claimbuster"] = get_layer_classification(
                claimbuster_results, "claimbuster")
    except Exception as e:
        logger.error(f"Error with ClaimBuster: {e}")
        result["layers"]["claimbuster_error"] = str(e)
    
    # Now determine fakeness using majority rule
    result["is_fake"] = determine_fakeness_by_majority_rule(result["layers"])
    result["credcheck_classification"] = classify_auth(result["is_fake"])
    
    # Save analysis to database
    try:
        if db:
            db.save_analysis(
                headline=text[:200],  # Use first 200 chars of transcribed text as headline
                is_fake=result["is_fake"],
                credcheck_classification=result["credcheck_classification"],
                claimbuster_results=result["layers"]["claimbuster"],
                source_type="video"
            )
    except Exception as e:
        logger.error(f"Error saving video analysis to database: {e}")
    
    return jsonify(result)

@app.route('/fetch_headlines', methods=['GET'])
def get_headlines():
    headlines = fetch_headlines()
    
    if isinstance(headlines, list):
        return jsonify({"headlines": headlines})
    else:
        return jsonify({"error": headlines.get("error", "Unknown error")}), 400

@app.route('/analyze_headline', methods=['GET'])
def analyze_headline():
    try:
        headline = request.args.get('headline', '')
        
        if not headline:
            return jsonify({"error": "No headline provided."}), 400
        
        # Analyze with CredCheck
        detection_result = fake_news_detector(headline)
        
        # Initialize our response structure
        result = {
            "headline": headline,
            "layers": {
                "credibility": detection_result.get("layers", {}).get("credibility", {}),
                "deepseek": detection_result.get("layers", {}).get("deepseek", {}),
                "claimbuster": []
            },
            "layer_classifications": {}
        }
        
        # Add classifications for the first two layers
        result["layer_classifications"]["credibility"] = get_layer_classification(
            result["layers"]["credibility"], "credibility")
        result["layer_classifications"]["deepseek"] = get_layer_classification(
            result["layers"]["deepseek"], "deepseek")
        
        # Always add ClaimBuster layer now (not just if first two layers say fake)
        try:
            if not is_english(headline):
                translated_headline = translation(headline)
                result["translated_text"] = translated_headline
            else:
                translated_headline = headline
            
            claimbuster_result = check_claim(translated_headline)
            
            if "error" in claimbuster_result:
                result["layers"]["claimbuster_error"] = claimbuster_result["error"]
            else:
                claimbuster_results = []
                for cb_result in claimbuster_result["results"]:
                    score = cb_result["score"]
                    classification = classify_claim(score)
                    claimbuster_results.append({
                        "text": cb_result["text"],
                        "score": score,
                        "classification": classification
                    })
                result["layers"]["claimbuster"] = claimbuster_results
                
                # Add classification for ClaimBuster layer
                result["layer_classifications"]["claimbuster"] = get_layer_classification(
                    claimbuster_results, "claimbuster")
        except Exception as e:
            logger.error(f"Error with ClaimBuster: {e}")
            result["layers"]["claimbuster_error"] = str(e)
        
        # Now determine fakeness using majority rule
        result["is_fake"] = determine_fakeness_by_majority_rule(result["layers"])
        result["credcheck_classification"] = classify_auth(result["is_fake"])
        
        # Save analysis to database
        try:
            if db:
                db.save_analysis(
                    headline=headline,
                    is_fake=result["is_fake"],
                    credcheck_classification=result["credcheck_classification"],
                    claimbuster_results=result["layers"]["claimbuster"],
                    source_type="headline"
                )
        except Exception as e:
            logger.error(f"Error saving headline analysis to database: {e}")
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error analyzing headline: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_recent_analyses', methods=['GET'])
def get_recent_analyses():
    """Get recent news analyses from the database."""
    try:
        if not db:
            return jsonify({"error": "Database is not available"}), 500
            
        limit = request.args.get('limit', default=10, type=int)
        analyses = db.get_recent_analyses(limit)
        return jsonify({"analyses": analyses})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/get_statistics', methods=['GET'])
def get_statistics():
    """Get statistics about analyzed news."""
    try:
        if not db:
            # Return mock data if database is not available
            return jsonify({
                "total_count": 0,
                "real_count": 0,
                "fake_count": 0,
                "real_percentage": 0,
                "fake_percentage": 0,
                "avg_credibility": 0,
                "recent_analyses": []
            })
            
        stats = db.get_statistics()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/update_keys', methods=['POST'])
def update_keys():
    data = request.json
    
    if 'google_search_api_key' in data:
        os.environ['GOOGLE_SEARCH_API_KEY'] = data['google_search_api_key']
    
    if 'google_search_engine_id' in data:
        os.environ['GOOGLE_SEARCH_ENGINE_ID'] = data['google_search_engine_id']
    
    if 'google_language_api_key' in data:
        os.environ['GOOGLE_LANGUAGE_API_KEY'] = data['google_language_api_key']
    
    if 'claimbuster_api_key' in data:
        os.environ['CLAIMBUSTER_API_KEY'] = data['claimbuster_api_key']
    
    if 'news_api_key' in data:
        os.environ['NEWS_API_KEY'] = data['news_api_key']
    
    return jsonify({"message": "API keys updated successfully"})

@app.route('/analyze_image', methods=['POST'])
def analyze_image():
    if 'image_file' not in request.files:
        return jsonify({"error": "No image file provided."}), 400
    
    image_file = request.files['image_file']
    temp_image_path = get_temp_path("temp_image", ".jpg")
    image_file.save(temp_image_path)
    
    try:
        extracted_text = extract_text_from_image(temp_image_path)
    finally:
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)
    
    if extracted_text.startswith("Error:"):
        return jsonify({"error": extracted_text}), 400
    
    # Analyze with CredCheck
    detection_result = fake_news_detector(extracted_text)
    
    # Initialize our response structure
    result = {
        "extracted_text": extracted_text,
        "layers": {
            "credibility": detection_result.get("layers", {}).get("credibility", {}),
            "deepseek": detection_result.get("layers", {}).get("deepseek", {}),
            "claimbuster": []
        },
        "layer_classifications": {}
    }
    
    # Add classifications for the first two layers
    result["layer_classifications"]["credibility"] = get_layer_classification(
        result["layers"]["credibility"], "credibility")
    result["layer_classifications"]["deepseek"] = get_layer_classification(
        result["layers"]["deepseek"], "deepseek")
    
    # Always add ClaimBuster layer now (not just if first two layers say fake)
    try:
        if not is_english(extracted_text):
            translated_text = translation(extracted_text)
            result["translated_text"] = translated_text
        else:
            translated_text = extracted_text
        
        claimbuster_result = check_claim(translated_text)
        
        if "error" in claimbuster_result:
            result["layers"]["claimbuster_error"] = claimbuster_result["error"]
        else:
            claimbuster_results = []
            for cb_result in claimbuster_result["results"]:
                score = cb_result["score"]
                classification = classify_claim(score)
                claimbuster_results.append({
                    "text": cb_result["text"],
                    "score": score,
                    "classification": classification
                })
            result["layers"]["claimbuster"] = claimbuster_results
            
            # Add classification for ClaimBuster layer
            result["layer_classifications"]["claimbuster"] = get_layer_classification(
                claimbuster_results, "claimbuster")
    except Exception as e:
        logger.error(f"Error with ClaimBuster: {e}")
        result["layers"]["claimbuster_error"] = str(e)
    
    # Now determine fakeness using majority rule
    result["is_fake"] = determine_fakeness_by_majority_rule(result["layers"])
    result["credcheck_classification"] = classify_auth(result["is_fake"])
    
    # Save analysis to database
    try:
        if db:
            db.save_analysis(
                headline=extracted_text[:200],  # Use first 200 chars of extracted text as headline
                is_fake=result["is_fake"],
                credcheck_classification=result["credcheck_classification"],
                claimbuster_results=result["layers"]["claimbuster"],
                source_type="image"
            )
    except Exception as e:
        logger.error(f"Error saving image analysis to database: {e}")
    
    return jsonify(result)

@app.route('/analyze', methods=['POST'])
def analyze():
    data = request.get_json()
    if not data or 'headline' not in data:
        return jsonify({'error': 'No headline provided'}), 400
    
    headline = data['headline']
    result = analyze_fake_news(headline)
    return jsonify(result)

@app.route('/get_real_time_news', methods=['GET'])
def get_real_time_news():
    """
    Get the most recent real-time news articles
    """
    try:
        limit = int(request.args.get('limit', 10))
        
        # Get recent articles from the monitor
        articles = news_monitor.get_recent_articles(limit=limit)
        
        # Prepare response
        response = {
            "articles": articles,
            "count": len(articles)
        }
        
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error fetching real-time news: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/analyze_real_time_article', methods=['POST'])
def analyze_real_time_article():
    """
    Analyze a specific real-time article
    """
    try:
        data = request.json
        article_id = data.get('article_id')
        
        if not article_id:
            return jsonify({"error": "Article ID is required"}), 400
            
        # Find the article
        articles = news_monitor.get_recent_articles(limit=30)
        article = next((a for a in articles if a['id'] == article_id), None)
        
        if not article:
            return jsonify({"error": "Article not found"}), 404
            
        # If already analyzed, return existing results
        if article.get('analyzed'):
            return jsonify({
                "article_id": article_id,
                "title": article.get('title', ''),
                "is_fake": article.get('is_fake', False),
                "credcheck_classification": classify_auth(article.get('is_fake', False))
            })
            
        # Run our fake news detection on the article title
        detection_result = fake_news_detector(article['title'])
        
        # Initialize our layers structure
        layers = {
            "credibility": detection_result.get("layers", {}).get("credibility", {}),
            "deepseek": detection_result.get("layers", {}).get("deepseek", {}),
            "claimbuster": []
        }
        
        # Add ClaimBuster analysis
        try:
            headline = article['title']
            if not is_english(headline):
                translated_headline = translation(headline)
            else:
                translated_headline = headline
            
            claimbuster_result = check_claim(translated_headline)
            
            if "error" not in claimbuster_result:
                claimbuster_results = []
                for cb_result in claimbuster_result["results"]:
                    score = cb_result["score"]
                    classification = classify_claim(score)
                    claimbuster_results.append({
                        "text": cb_result["text"],
                        "score": score,
                        "classification": classification
                    })
                layers["claimbuster"] = claimbuster_results
        except Exception as e:
            logger.error(f"Error with ClaimBuster for real-time article: {e}")
        
        # Now determine fakeness using majority rule
        is_fake = determine_fakeness_by_majority_rule(layers)
        
        # Update the article in the monitor
        score = None
        if 'credibility' in detection_result.get('layers', {}):
            score = detection_result['layers']['credibility'].get('score')
        
        news_monitor.add_credibility_score(article_id, is_fake, score)
        
        # Save the analysis to the database
        if db:
            db.save_analysis(
                headline=article['title'],
                is_fake=is_fake,
                credcheck_classification=classify_auth(is_fake),
                claimbuster_results=layers["claimbuster"],
                source_type="real-time"
            )
            
        # Prepare the simplified response (only overall result, no layers)
        result = {
            "article_id": article_id,
            "title": article.get('title', ''),
            "is_fake": is_fake,
            "credcheck_classification": classify_auth(is_fake)
        }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error analyzing real-time article: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_video_feed', methods=['GET'])
def get_video_feed():
    try:
        print("Starting video feed processing")
        # Run the video fetching script
        subprocess.run(['python', 'realTimeVideo.py'], check=True)
        print("Successfully ran realTimeVideo.py")
        
        # Find the generated caption files
        caption_files = glob.glob('*.txt')
        print(f"Found {len(caption_files)} caption files")
        
        # Store results
        results = []
        
        # Process up to 5 videos instead of just one
        count = 0
        for caption_file in caption_files:
            if count >= 5:  # Limit to 5 videos
                break
                
            video_id = caption_file.replace('.txt', '')
            print(f"Processing video ID: {video_id}")
            
            # Read the captions
            with open(caption_file, 'r', encoding='utf-8') as f:
                captions = f.read()
            
            if len(captions) < 50:  # Skip if captions are too short
                print(f"Skipping video {video_id} - captions too short")
                continue
                
            # Analyze the captions using only the deepseek layer
            analysis_result = fake_news_detector(captions)
            print(f"Analyzed video {video_id}")
            
            # Create a layers structure similar to the other routes
            layers = {
                "deepseek": analysis_result.get("layers", {}).get("deepseek", {})
            }
            
            # For video feed, we're only using deepseek, so use its result directly
            deepseek_layer = layers["deepseek"]
            is_fake = deepseek_layer.get("is_fake", True)  # Default to fake if missing
            is_reliable = not is_fake
            deepseek_score = deepseek_layer.get("score", 0.0)
            
            # Add to results - don't include captions in the response
            results.append({
                'video_id': video_id,
                'thumbnail_url': f'https://img.youtube.com/vi/{video_id}/maxresdefault.jpg',
                'is_reliable': is_reliable,
                'deepseek_score': deepseek_score
            })
            
            # No database saving - removed to fix errors
            
            count += 1
            
        # Clean up the caption files
        for caption_file in caption_files:
            try:
                os.remove(caption_file)
                print(f"Removed caption file: {caption_file}")
            except Exception as e:
                print(f"Error removing caption file {caption_file}: {str(e)}")
                
        print(f"Returning {len(results)} videos")
        return jsonify({"videos": results})
    except Exception as e:
        print(f"Error in get_video_feed: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/get_live_broadcast', methods=['GET'])
def get_live_broadcast():
    try:
        # Get the latest live broadcast results
        live_broadcast_results = get_live_analysis_results()
        
        # Update the response format to include the YouTube URL
        return jsonify({
            "youtube_url": os.environ.get('YOUTUBE_URL', DEFAULT_YOUTUBE_URL),
            "results": live_broadcast_results
        })
    except Exception as e:
        print(f"Error in get_live_broadcast: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Start the live video analysis in the background when the app starts
live_analysis_thread = None

if __name__ == '__main__':
    # Initialize live analysis thread before starting the app
    live_analysis_thread = None
    print("[+] Starting live video analysis in background")
    live_analysis_thread = start_live_video_process_in_background()
    print("[+] Live video analysis started")
    
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False) 