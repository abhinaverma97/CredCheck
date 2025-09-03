import os
from googleapiclient.discovery import build
import isodate
from youtube_transcript_api import YouTubeTranscriptApi
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get API key from environment variable
API_KEY = os.environ.get('YOUTUBE_API_KEY', '')
# Check if API key is available
if not API_KEY:
    print("Warning: YouTube API key is missing. Please add YOUTUBE_API_KEY to your .env file.")

CHANNEL_ID = "UC16niRr50-MSBwiO3YDb3RA"  # Replace with the news channel's ID
MAX_DURATION = 4 * 60  # 4 minutes in seconds
NUM_REQUIRED_VIDEOS = 5  # The number of valid videos needed

def get_uploads_playlist_id(channel_id):
    """Fetches the Uploads Playlist ID for a given channel."""
    youtube = build("youtube", "v3", developerKey=API_KEY)
    response = youtube.channels().list(
        part="contentDetails",
        id=channel_id
    ).execute()
    return response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

def get_videos_from_playlist(playlist_id, page_token=None):
    """Fetches videos from a playlist, with pagination support."""
    youtube = build("youtube", "v3", developerKey=API_KEY)
    request = youtube.playlistItems().list(
        part="snippet",
        playlistId=playlist_id,
        maxResults=10,  # Fetching more videos in case we need to filter many
        pageToken=page_token
    )
    return request.execute()

def get_video_duration(video_id):
    """Gets the duration of a video in seconds."""
    youtube = build("youtube", "v3", developerKey=API_KEY)
    response = youtube.videos().list(
        part="contentDetails",
        id=video_id
    ).execute()
    duration_iso = response["items"][0]["contentDetails"]["duration"]
    return isodate.parse_duration(duration_iso).total_seconds()

def has_english_captions(video_id):
    """Checks if a video has English captions available."""
    try:
        # This will raise an exception if no transcript is available
        transcripts = YouTubeTranscriptApi.list_transcripts(video_id)
        
        # Check if English is among the available languages
        for transcript in transcripts:
            if transcript.language_code == 'en' or transcript.language_code.startswith('en-'):
                return True
                
        return False
    except Exception as e:
        print(f"⚠ Error checking captions for {video_id}: {e}")
        return False

def download_caption(video_id, title):
    """Downloads and saves the English captions as a simple text file using YouTubeTranscriptApi."""
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en'])
        
        # Format the transcript as simple text
        caption_text = ""
        for entry in transcript:
            caption_text += entry['text'] + " "  # Just add the text with a space
        
        # Clean up any double spaces
        caption_text = caption_text.replace("  ", " ")
        
        # Save to a text file
        filename = f"{video_id}.txt"
        with open(filename, "w", encoding="utf-8") as file:
            file.write(caption_text)
        
        print(f"📜 Captions saved as simple text: {filename}")
        return True
    except Exception as e:
        print(f"⚠ Error downloading captions for {video_id}: {e}")
        return False

# Fetch the uploads playlist ID
playlist_id = get_uploads_playlist_id(CHANNEL_ID)

valid_videos = []
page_token = None

while len(valid_videos) < NUM_REQUIRED_VIDEOS:
    response = get_videos_from_playlist(playlist_id, page_token)
    
    for item in response["items"]:
        if len(valid_videos) >= NUM_REQUIRED_VIDEOS:
            break  # Stop if we already have enough videos

        video_id = item["snippet"]["resourceId"]["videoId"]
        title = item["snippet"]["title"]
        
        try:
            duration = get_video_duration(video_id)
            if duration <= MAX_DURATION:
                if has_english_captions(video_id):
                    valid_videos.append((video_id, title, duration))
                    print(f"✅ Found: {title} ({video_id}) - {int(duration)} sec")
                else:
                    print(f"❌ Skipping (No English captions): {title} ({video_id}) - {int(duration)} sec")
            else:
                print(f"⏩ Skipping (Too long): {title} ({video_id}) - {int(duration)} sec")
        except Exception as e:
            print(f"⚠ Error processing video {video_id}: {e}")

    # Check if there are more videos in the playlist
    page_token = response.get("nextPageToken")
    if not page_token:
        print("⚠ No more videos available in the playlist!")
        break  # Stop if no more videos are available

# Download captions for valid videos
print("\n🎯 Downloading captions for valid videos:")
for video_id, title, duration in valid_videos:
    print(f"📥 Downloading captions for: {title} ({video_id})")
    download_caption(video_id, title)