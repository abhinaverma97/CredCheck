import subprocess
import time
import whisper
import os
import json
import requests
from cred_check import deepseek_check
from dotenv import load_dotenv
import random

# Load environment variables
load_dotenv()

# Use the working DeepSeek API key
DEEPSEEK_API_KEY = os.environ.get('DEEPSEEK_API_KEY', '')

# Load Whisper model
print("[+] Loading Whisper model...")
model = whisper.load_model("base")
print("[+] Whisper model loaded successfully.")

# Constants
CHUNK_DURATION = 90  # seconds (90 second chunks)

DEFAULT_YOUTUBE_URL = "https://www.youtube.com/watch?v=gCNeDWCI0vo"  # al jazeera english

# DEFAULT_YOUTUBE_URL = "https://www.youtube.com/watch?v=vOTiJkg1voo"  # abc news

# DEFAULT_YOUTUBE_URL = "https://www.youtube.com/watch?v=sYZtOFzM78M"  # india






# Store analysis results for web app access
live_analysis_results = []

def get_live_analysis_results():
    """
    Return the latest live analysis results.
    
    Returns:
        list: List of analysis results, with most recent first.
    """
    global live_analysis_results
    return live_analysis_results

def add_analysis_result(transcript, news_item, analysis):
    """
    Add an analysis result to the in-memory store.
    
    Args:
        transcript (str): The original transcript
        news_item (str): The extracted news item
        analysis (dict): Analysis result from DeepSeek
    """
    global live_analysis_results
    
    result = {
        "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
        "transcript": transcript,
        "news_item": news_item,
        "verdict": analysis.get('verdict', 'Unknown'),
        "is_fake": analysis.get('is_fake', None)
    }
    
    # Add to the beginning of the list (most recent first)
    live_analysis_results.insert(0, result)
    
    # Limit to last 10 results
    if len(live_analysis_results) > 10:
        live_analysis_results = live_analysis_results[:10]

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

def extract_news_with_deepseek(transcript):
    """
    Use DeepSeek AI to extract a news item from the transcript if one exists.
    
    Args:
        transcript (str): The transcribed text from the video chunk
        
    Returns:
        str or None: The extracted news item or None if no news was found
    """
    try:
        # Construct prompt for news extraction
        prompt = f"""
You are a specialized news extraction AI. Analyze the following transcript from a media source and extract ONE SINGLE news item if it exists.
A news item typically reports on a current event, has factual statements, mentions specific people, places, or events.

Transcript:
{transcript}

If there is a news item in the transcript, extract it completely and faithfully.
If there is more than one news item, extract only the most important or complete one.
If there is no clear news item, respond with "NO_NEWS_FOUND".

Extract only the news item text with no additional commentary or explanation.
"""

        # Call DeepSeek API
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://credcheck.example.com",
                "X-Title": "CredCheck"
            },
            data=json.dumps({
                "model": "deepseek/deepseek-r1-zero:free",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a specialized news extraction AI that can identify and extract news content from transcripts."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
            })
        )

        if response.status_code != 200:
            print(f"[-] API error: {response.status_code}")
            return None

        result = response.json()
        if "choices" not in result or len(result["choices"]) == 0:
            print("[-] No choices in API response")
            return None
            
        if "message" not in result["choices"][0]:
            print("[-] No message in API response choice")
            return None
            
        # Extract the content from the response
        content = result["choices"][0]["message"]["content"].strip()
        
        # Clean the boxed content
        cleaned_content = extract_from_boxed_content(content)
        
        # Check if news was found
        if cleaned_content == "NO_NEWS_FOUND":
            print("[-] No news content detected in this chunk. Skipping analysis.")
            return None
            
        return cleaned_content
        
    except Exception as e:
        print(f"[-] Error extracting news: {e}")
        return None

def generate_sample_news():
    """
    Generate sample news transcripts for testing when direct video processing is not available.
    """
    print("[+] Using sample news transcripts instead of YouTube video")
    
    # Sample news transcripts for analysis
    news_transcripts = [
        "Breaking news from Washington: The Senate has passed a new climate bill today with bipartisan support. The legislation aims to reduce carbon emissions by 50% by 2030 through investment in renewable energy infrastructure.",
        
        "In economic news, the Federal Reserve has announced it will maintain current interest rates, citing concerns about inflation. Market analysts had predicted a quarter-point increase.",
        
        "Scientists at MIT have announced a breakthrough in quantum computing technology. Their new chip design can maintain quantum coherence for up to 10 minutes, a significant improvement over previous designs.",
        
        "Health officials warn of a new virus strain spreading in Southeast Asia. The WHO has issued travel advisories for the region while researchers study the pathogen's transmission patterns.",
        
        "Tech giant Microsoft has unveiled plans to invest $5 billion in AI research centers across Europe. The company says this will create approximately 10,000 new jobs over the next five years."
    ]
    
    return news_transcripts

def process_live_video():
    """
    Process a live YouTube video by extracting audio and transcribing it in chunks.
    Falls back to sample news items if YouTube processing is not available.
    """
    video_url = DEFAULT_YOUTUBE_URL
    news_count = 0
    chunk_count = 0
    
    # Try to import yt-dlp, if not available, use sample news
    try:
        import yt_dlp
        have_yt_dlp = True
        print("[+] yt-dlp package found, will attempt to process YouTube video")
    except ImportError:
        have_yt_dlp = False
        print("[-] yt-dlp package not found, using sample news instead")
        print("[-] Install yt-dlp with: pip install yt-dlp")
    
    # Check if ffmpeg is available
    have_ffmpeg = False
    try:
        result = subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if result.returncode == 0:
            have_ffmpeg = True
            print("[+] ffmpeg found, will use it for audio processing")
    except:
        print("[-] ffmpeg not found in PATH, using sample news instead")
    
    # If either yt-dlp or ffmpeg is missing, use sample news
    if not have_yt_dlp or not have_ffmpeg:
        print("[+] Using sample news mode due to missing dependencies")
        news_transcripts = generate_sample_news()
        
        for transcript in news_transcripts:
            chunk_count += 1
            print(f"\n[+] Processing sample news item {chunk_count}")
            print(f"[+] Transcript content:\n{transcript}\n")
            
            # Extract news with DeepSeek
            print("[+] Extracting news with DeepSeek AI...")
            news_item = extract_news_with_deepseek(transcript)
            
            if news_item:
                news_count += 1
                print(f"[+] News item {news_count} detected:")
                print(f"[News]: {news_item}\n")
                
                # Analyze the news item with DeepSeek for fake/real classification
                print("[+] Analyzing news credibility with DeepSeek AI...")
                analysis = deepseek_check(news_item)
                
                if "error" in analysis:
                    print(f"[-] Analysis error: {analysis['error']}")
                else:
                    verdict = analysis['verdict']
                    is_fake = analysis['is_fake']
                    
                    print(f"[Result]: {'FAKE' if is_fake else 'REAL'} news")
                    print(f"[Verdict]: {verdict}\n")
                    
                    # Save to file for record keeping
                    with open("live_news_analysis.txt", "a", encoding="utf-8") as f:
                        f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"News: {news_item}\n")
                        f.write(f"Classification: {'FAKE' if is_fake else 'REAL'}\n")
                        f.write(f"Verdict: {verdict}\n")
                        f.write("-" * 80 + "\n\n")
                    
                    # Add to web results
                    add_analysis_result(transcript, news_item, analysis)
            else:
                print("[-] No news content detected in this transcript. Skipping analysis.\n")
            
            # Simulate processing time
            print(f"[+] Waiting for next news item...")
            time.sleep(5)
            
        print("\n[+] All sample news items processed")
        return
    
    # If we have all required dependencies, process actual YouTube video
    try:
        print(f"[+] Fetching info for YouTube video: {video_url}")
        ydl_opts = {
            'format': 'bestaudio/best',
            'quiet': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            stream_url = info['url']
            print(f"[+] Stream URL acquired")
            
        while True:
            chunk_file = f"chunk_{chunk_count}.wav"

            print(f"[+] Recording chunk {chunk_count}...")

            # ffmpeg command: record audio chunk from the stream
            ffmpeg_cmd = [
                "ffmpeg", "-y",
                "-i", stream_url,
                "-t", str(CHUNK_DURATION),
                "-ac", "1",         # mono channel
                "-ar", "16000",     # sample rate for Whisper
                "-f", "wav",
                chunk_file
            ]

            # Run ffmpeg silently
            subprocess.run(ffmpeg_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

            # Check if chunk was saved
            if not os.path.exists(chunk_file):
                print(f"[-] Failed to record chunk {chunk_count}. Skipping...")
                chunk_count += 1
                continue

            print(f"[+] Transcribing chunk {chunk_count} with Whisper...")

            # Transcribe
            result = model.transcribe(chunk_file)
            transcript = result["text"]
            print(f"[Transcript chunk {chunk_count}]:\n{transcript}\n")

            # Extract news from transcript using DeepSeek
            print("[+] Extracting news with DeepSeek AI...")
            news_item = extract_news_with_deepseek(transcript)
            
            if news_item:
                news_count += 1
                print(f"[+] News item {news_count} detected:")
                print(f"[News]: {news_item}\n")
                
                # Analyze the news item with DeepSeek for fake/real classification
                print("[+] Analyzing news credibility with DeepSeek AI...")
                analysis = deepseek_check(news_item)
                
                if "error" in analysis:
                    print(f"[-] Analysis error: {analysis['error']}")
                else:
                    verdict = analysis['verdict']
                    is_fake = analysis['is_fake']
                    
                    print(f"[Result]: {'FAKE' if is_fake else 'REAL'} news")
                    print(f"[Verdict]: {verdict}\n")
                    
                    # Save to file for record keeping
                    with open("live_news_analysis.txt", "a", encoding="utf-8") as f:
                        f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"News: {news_item}\n")
                        f.write(f"Classification: {'FAKE' if is_fake else 'REAL'}\n")
                        f.write(f"Verdict: {verdict}\n")
                        f.write("-" * 80 + "\n\n")
                    
                    # Add to web results
                    add_analysis_result(transcript, news_item, analysis)
            else:
                print("[-] No news content detected in this chunk. Skipping analysis.\n")

            # Optional: Delete the audio chunk to save space
            if os.path.exists(chunk_file):
                os.remove(chunk_file)

            chunk_count += 1
            
    except KeyboardInterrupt:
        print("\n[!] Stopped by user.")
    except Exception as e:
        print(f"\n[-] Error in live video processing: {e}")
        print("[+] Falling back to sample news mode")
        
        # Clean up any chunk files
        for file in os.listdir():
            if file.startswith("chunk_") and file.endswith(".wav"):
                try:
                    os.remove(file)
                except:
                    pass
                    
        # Use sample news as fallback
        news_transcripts = generate_sample_news()
        
        for transcript in news_transcripts:
            chunk_count += 1
            print(f"\n[+] Processing sample news item {chunk_count}")
            print(f"[+] Transcript content:\n{transcript}\n")
            
            # Extract news with DeepSeek
            print("[+] Extracting news with DeepSeek AI...")
            news_item = extract_news_with_deepseek(transcript)
            
            if news_item:
                news_count += 1
                print(f"[+] News item {news_count} detected:")
                print(f"[News]: {news_item}\n")
                
                # Analyze with DeepSeek
                print("[+] Analyzing news credibility with DeepSeek AI...")
                analysis = deepseek_check(news_item)
                
                if "error" in analysis:
                    print(f"[-] Analysis error: {analysis['error']}")
                else:
                    verdict = analysis['verdict']
                    is_fake = analysis['is_fake']
                    
                    print(f"[Result]: {'FAKE' if is_fake else 'REAL'} news")
                    print(f"[Verdict]: {verdict}\n")
                    
                    # Save to file
                    with open("live_news_analysis.txt", "a", encoding="utf-8") as f:
                        f.write(f"Time: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                        f.write(f"News: {news_item}\n")
                        f.write(f"Classification: {'FAKE' if is_fake else 'REAL'}\n")
                        f.write(f"Verdict: {verdict}\n")
                        f.write("-" * 80 + "\n\n")
                    
                    # Add to web results
                    add_analysis_result(transcript, news_item, analysis)
            else:
                print("[-] No news content detected in this transcript. Skipping analysis.\n")
            
            # Simulate processing time
            print(f"[+] Waiting for next news item...")
            time.sleep(5)

# Function to run the live video process in a separate thread
def start_live_video_process_in_background():
    """
    Start the live video process in a background thread
    """
    import threading
    thread = threading.Thread(target=process_live_video)
    thread.daemon = True  # Thread will exit when main program exits
    thread.start()
    return thread

if __name__ == "__main__":
    print("[+] Starting news analysis from live YouTube stream")
    print("[+] Press Ctrl+C to stop the analysis")
    print("[+] Analysis results will be saved to live_news_analysis.txt")
    process_live_video() 