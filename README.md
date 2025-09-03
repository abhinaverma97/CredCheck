# CredCheck - Multilayered Fake News Detection System

![CredCheck Logo](static/images/img1.png)

CredCheck is an advanced fake news detection platform featuring a unique multilayered verification system that examines content through multiple independent analysis methods for comprehensive credibility assessment.

## 🔍 Core Features

- **Layered Verification System**: Three independent verification methods to ensure thorough analysis:
  - **Layer 1**: Credibility check against trusted sources
  - **Layer 2**: AI analysis using DeepSeek's advanced model
  - **Layer 3**: ClaimBuster fact-checking for suspicious content

- **Multiple Content Formats**:
  - Text headlines and articles
  - Images (with text extraction)
  - Audio files (with transcription)
  - Video content (with transcription)

- **Real-Time News Monitoring**: Automatically fetch and analyze news from diverse sources in real-time

- **Realtime Headlines Analysis**: Fetch and analyze current top news headlines

- **Real-Time Video Analysis**: Live video stream analysis with frame-by-frame credibility assessment from YouTube and other sources

- **Comprehensive Dashboard**: Analytics showing the distribution of real vs. fake news

- **Responsive Design**: Modern dark-themed UI that works on all devices

## 🛠️ Technology Stack

### Backend
- **Framework**: Flask (Python)
- **AI Models**: BERT embeddings, DeepSeek AI, Whisper (for audio/video transcription)
- **Text Processing**: Whisper (for audio/video), Tesseract OCR (for images)
- **Video Processing**: yt-dlp, ffmpeg, YouTubeTranscriptApi
- **RSS Processing**: FeedParser, BeautifulSoup4
- **External APIs**: Google Search, ClaimBuster, NewsAPI, YouTube Data API, Google Generative AI

### Frontend
- **UI**: HTML5, CSS3, JavaScript
- **Data Visualization**: Chart.js
- **Design**: Modern dark theme with intuitive layered result display

## 📋 Verification Layers Explained

### Layer 1: Credibility Check
Searches for the headline across trusted news sources, evaluating:
- Presence in reputable sources
- Semantic similarity with verified content
- BERT embeddings for content similarity analysis

### Layer 2: AI Analysis
Uses DeepSeek's AI model to:
- Analyze the credibility based on content patterns
- Identify hallmarks of misinformation
- Provide verdict with explanation

### Layer 3: ClaimBuster (for suspicious content)
When earlier layers flag content as potentially fake:
- Breaks down content into fact-checkable claims
- Scores each claim for factual accuracy

## 🚀 Setup Instructions

### Prerequisites
- Python 3.8+
- Tesseract OCR (for image analysis)
- ffmpeg (for video processing)
- API keys (see below)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/credcheck.git
   cd credcheck
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Set up environment variables (create a `.env` file):
   ```
   # API Keys
   GOOGLE_SEARCH_API_KEY=your_api_key
   GOOGLE_SEARCH_ENGINE_ID=your_search_engine_id
   GOOGLE_LANGUAGE_API_KEY=your_language_api_key
   DEEPSEEK_API_KEY=your_deepseek_api_key
   CLAIMBUSTER_API_KEY=your_claimbuster_api_key
   CLAIMBUSTER_ENDPOINT=your_claimbuster_endpoint
   NEWS_API_KEY=your_newsapi_key
   YOUTUBE_API_KEY=your_youtube_api_key
   
   # Configuration
   DATABASE_URL=news_analysis.db
   TESSERACT_CMD=path_to_tesseract_if_needed
   PORT=5000
   ```

5. Install external dependencies:
   - **Tesseract OCR**: 
     - Windows: Download from [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
     - Linux: `sudo apt-get install tesseract-ocr`
     - macOS: `brew install tesseract`
   
   - **ffmpeg**:
     - Windows: Download from [ffmpeg.org](https://ffmpeg.org/download.html)
     - Linux: `sudo apt-get install ffmpeg`
     - macOS: `brew install ffmpeg`

6. Run the application:
   ```bash
   python app.py
   ```

7. Open your browser and navigate to:
   ```
   http://127.0.0.1:5000/
   ```

## 📊 Project Structure

```
.
├── app.py                  # Main Flask application
├── cred_check.py           # Core fake news detection logic
├── claimbuster_check.py    # ClaimBuster API integration
├── audio_to_text.py        # Audio transcription module
├── video_to_text.py        # Video transcription module
├── LiveVideoFeed.py        # Real-time video analysis
├── img_to_text.py          # Image text extraction module
├── convert_to_english.py   # Translation utilities
├── top_headlines.py        # News API integration
├── realTimeArticle.py      # Real-time news monitoring
├── realTimeVideo.py        # YouTube video caption analysis
├── database.py             # Database operations
├── requirements.txt        # Project dependencies
├── static/                 # Static files
│   ├── css/                
│   │   └── style.css       # Modern dark-themed styling
│   ├── js/                 
│   │   └── script.js       # Frontend JavaScript
│   └── images/             # Image assets
└── templates/              
    └── index.html          # Main HTML template
```

## 🔑 API Keys Setup

To fully utilize CredCheck, you'll need to set up the following API keys:

1. **Google Search API + Custom Search Engine ID**:
   - Visit [Google Cloud Console](https://console.cloud.google.com/)
   - Enable Custom Search API
   - Create API credentials
   - Set up a Custom Search Engine at [cse.google.com](https://cse.google.com/cse/all)

2. **DeepSeek API**:
   - Sign up at [OpenRouter](https://openrouter.ai/)
   - Generate an API key with access to DeepSeek models

3. **ClaimBuster API**:
   - Request access at [idir.uta.edu/claimbuster](https://idir.uta.edu/claimbuster/)

4. **NewsAPI**:
   - Register at [newsapi.org](https://newsapi.org/)

5. **YouTube API**:
   - Set up at [Google Cloud Console](https://console.cloud.google.com/)
   - Enable YouTube Data API v3

6. **Google Language API (for Gemini)**:
   - Set up at [Google AI Studio](https://ai.google.dev/)
   - Create an API key for Gemini models

## 📱 Usage Guide

### Analyzing Individual Content

1. **Select Input Type**:
   - Choose between Text, Image, Audio, or Video

2. **Provide Content**:
   - For text: Enter a headline or news snippet
   - For other formats: Upload the relevant file

3. **View Analysis Results**:
   - Overall classification (Real or Fake)
   - Detailed results from each verification layer
   - Explanations for each layer's verdict

### Real-Time News Feed

1. Navigate to the "Real-Time News Feed" tab in the "Real Time News Analysis" section
2. The system automatically fetches and analyzes news from diverse sources
3. Articles are displayed with their credibility status (Real or Fake)
4. News feed updates hourly with fresh content from multiple reliable sources

### Realtime Headlines Analysis

1. Click on "Fetch Top Headlines"
2. The system will retrieve current headlines and analyze each one
3. View the comprehensive analysis for each headline with details from each verification layer

### Real-Time Video Analysis

1. Navigate to the "Real-Time Video" section
2. The system fetches recent videos from configured news channels
3. Videos are transcribed and analyzed for credibility
4. Results show potential misinformation with timestamps
5. View detailed analysis of each segment with supporting evidence

### Dashboard Analytics

Scroll down to see:
- Distribution of real vs. fake news
- Recent analysis history
- Trend analysis over time

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

*CredCheck - Empowering users to verify the truth behind the headlines*

