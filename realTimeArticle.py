import feedparser
import time
import threading
from typing import List, Dict, Any, Optional, Callable
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RealTimeNewsMonitor:
    def __init__(self, rss_feeds: List[str] = None, check_interval: int = 300, max_recent_articles: int = 30):
        """
        Initialize the real-time news monitor.
        
        Args:
            rss_feeds: List of RSS feed URLs to monitor (if None, default feeds will be used)
            check_interval: How often to check for new articles in seconds (default: 5 minutes)
            max_recent_articles: Maximum number of articles to store in memory
        """
        # Default news sources if none provided
        self.rss_feeds = rss_feeds or [
            "https://rss.cnn.com/rss/cnn_topstories.rss",
            "http://feeds.bbci.co.uk/news/rss.xml",
            "https://www.theguardian.com/world/rss",
            # Removing NYTimes as it blocks content extraction
            # "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
            "https://www.washingtonpost.com/rss/world/feed",
            "https://www.aljazeera.com/xml/rss/all.xml",
            "http://feeds.reuters.com/reuters/topNews",
            "http://feeds.skynews.com/feeds/rss/world.xml",
            "https://www.huffpost.com/section/world-news/feed"
        ]
        
        # Sites that block content extraction
        self.blocked_domains = [
            "nytimes.com",
            "ft.com",
            "wsj.com"
        ]
        
        self.check_interval = check_interval
        self.running = False
        self.articles_cache = {}  # Store previously seen articles to avoid duplicates
        self.callback_functions = []  # Functions to call when new articles are detected
        self.thread = None
        
        # Keep track of recent articles
        self.recent_articles = []
        self.max_recent_articles = max_recent_articles  # Maximum number of articles to keep in memory
        
        # Add a lock for thread safety when accessing recent_articles
        self.lock = threading.Lock()

    def extract_article_content(self, url: str) -> Optional[str]:
        """
        Extract the main content from a news article URL.
        
        Args:
            url: The URL of the news article
            
        Returns:
            The extracted article text or None if extraction failed
        """
        # Check if domain is in blocked list
        domain = urlparse(url).netloc
        if any(blocked in domain for blocked in self.blocked_domains):
            return f"Content extraction not available for {domain}"
            
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style", "nav", "header", "footer", "aside"]):
                script.extract()
            
            # Extract paragraphs (most common for article content)
            paragraphs = soup.find_all('p')
            article_text = ' '.join([p.get_text().strip() for p in paragraphs])
            
            # Clean up the text
            article_text = re.sub(r'\s+', ' ', article_text).strip()
            
            # Limit the text length to avoid excessively long content
            if article_text and len(article_text) > 1000:
                article_text = article_text[:1000] + "..."
                
            return article_text if article_text else None
        except Exception as e:
            return f"Error extracting content: {str(e)}"

    def _update_recent_articles(self, article: Dict[str, Any]) -> None:
        """
        Update the recent articles list, maintaining the maximum size
        
        Args:
            article: The article to add to the recent articles list
        """
        with self.lock:
            # Add to front of list (most recent first)
            self.recent_articles.insert(0, article)
            
            # Trim list if needed
            if len(self.recent_articles) > self.max_recent_articles:
                self.recent_articles = self.recent_articles[:self.max_recent_articles]

    def fetch_articles(self) -> List[Dict[str, Any]]:
        """
        Fetch articles from all RSS feeds
        
        Returns:
            List of article dictionaries
        """
        new_articles = []
        source_counts = {}  # Keep track of articles per source
        
        # First, fetch articles from all feeds
        for feed_url in self.rss_feeds:
            try:
                feed = feedparser.parse(feed_url)
                source_name = feed.feed.get('title', urlparse(feed_url).netloc)
                source_counts[source_name] = 0  # Initialize count for this source
                
                for entry in feed.entries:
                    article_id = entry.get('id', entry.link)
                    
                    # Skip if we've seen this article before
                    if article_id in self.articles_cache:
                        continue
                    
                    # Get the article content if available
                    content = None
                    if hasattr(entry, 'content') and entry.content:
                        content = entry.content[0].value
                    elif hasattr(entry, 'summary'):
                        content = entry.summary
                    
                    # If content is HTML, try to clean it
                    if content and re.search(r'<[^>]+>', content):
                        soup = BeautifulSoup(content, 'html.parser')
                        content = soup.get_text()
                    
                    # If no content or too short, try to fetch the full article
                    if not content or len(content) < 100:
                        content = self.extract_article_content(entry.link)
                    
                    # Create article object - default to analyzed=True and not fake
                    article = {
                        'id': article_id,
                        'title': entry.title,
                        'link': entry.link,
                        'published': entry.get('published', ''),
                        'source': source_name,
                        'content': content,
                        'analyzed': True,  # Set analyzed to True by default
                        'is_fake': False,  # Default to not fake
                        'credibility_score': 0.85,  # Default to a high credibility score
                        'timestamp': time.time()  # Add timestamp for sorting purposes
                    }
                    
                    # Add to new articles list
                    new_articles.append(article)
                    source_counts[source_name] += 1
            
            except Exception as e:
                print(f"Error fetching from {feed_url}: {e}")
        
        # Now select a diverse set of articles (max 2-3 per source)
        diverse_articles = []
        sources_used = set()
        
        # First pass: take one from each source
        for article in new_articles:
            source = article['source']
            if source not in sources_used:
                diverse_articles.append(article)
                sources_used.add(source)
                
                # Update cache and recent articles
                self.articles_cache[article['id']] = time.time()
                self._update_recent_articles(article)
                
                # Stop if we have enough articles
                if len(diverse_articles) >= 10:
                    break
        
        # Second pass: if we don't have enough, take more articles but ensure diversity
        if len(diverse_articles) < 10:
            for article in new_articles:
                if article not in diverse_articles:
                    # Only add 2 max from each source
                    source = article['source']
                    source_count = sum(1 for a in diverse_articles if a['source'] == source)
                    if source_count < 2:
                        diverse_articles.append(article)
                        
                        # Update cache and recent articles
                        self.articles_cache[article['id']] = time.time()
                        self._update_recent_articles(article)
                        
                        # Stop if we have enough articles
                        if len(diverse_articles) >= 10:
                            break
        
        print(f"Selected {len(diverse_articles)} diverse articles from {len(sources_used)} sources")
        return diverse_articles
    
    def register_callback(self, callback_function: Callable[[Dict[str, Any]], None]) -> None:
        """
        Register a callback function to be called when a new article is detected
        
        Args:
            callback_function: Function that takes a processed article as its argument
        """
        self.callback_functions.append(callback_function)
    
    def _monitor_loop(self) -> None:
        """
        Internal loop to continuously monitor for new articles
        """
        while self.running:
            try:
                # Fetch new articles
                new_articles = self.fetch_articles()
                
                if new_articles:
                    print(f"Found {len(new_articles)} new articles")
                    
                    # Process each article through callbacks
                    for article in new_articles:
                        for callback in self.callback_functions:
                            try:
                                callback(article)
                            except Exception as e:
                                print(f"Error in callback: {e}")
            
            except Exception as e:
                print(f"Error in monitoring loop: {e}")
            
            # Wait for next check
            time.sleep(self.check_interval)
    
    def start(self) -> None:
        """
        Start the real-time monitoring in a background thread
        """
        if self.running:
            print("Monitoring is already running")
            return
        
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop)
        self.thread.daemon = True
        self.thread.start()
        print(f"Started real-time news monitoring with {len(self.rss_feeds)} feeds")
    
    def stop(self) -> None:
        """
        Stop the real-time monitoring
        """
        if not self.running:
            return
            
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        print("Stopped real-time news monitoring")

    def cleanup_cache(self, max_age_hours: int = 24) -> None:
        """
        Clean up old entries from the articles cache
        
        Args:
            max_age_hours: Maximum age of cache entries in hours
        """
        max_age_seconds = max_age_hours * 3600
        current_time = time.time()
        
        to_remove = []
        for article_id, timestamp in self.articles_cache.items():
            if current_time - timestamp > max_age_seconds:
                to_remove.append(article_id)
        
        for article_id in to_remove:
            del self.articles_cache[article_id]
        
        print(f"Cleaned up {len(to_remove)} old entries from cache")
    
    def get_recent_articles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent articles that have been fetched
        
        Args:
            limit: Maximum number of articles to return
            
        Returns:
            List of recent articles
        """
        with self.lock:
            return self.recent_articles[:limit]
            
    def add_credibility_score(self, article_id: str, is_fake: bool, score: float = None) -> bool:
        """
        Add a credibility score to an article after it's been analyzed
        
        Args:
            article_id: The ID of the article to update
            is_fake: Boolean indicating if the article is fake or not
            score: Optional numerical score for the credibility
            
        Returns:
            True if article was found and updated, False otherwise
        """
        with self.lock:
            for article in self.recent_articles:
                if article['id'] == article_id:
                    article['analyzed'] = True
                    article['is_fake'] = is_fake
                    if score is not None:
                        article['credibility_score'] = score
                    return True
        return False


# Example callback function to print new articles
def print_article_info(article: Dict[str, Any]) -> None:
    """
    Example callback that prints information about a new article
    """
    print("\n" + "=" * 80)
    print(f"NEW ARTICLE: {article['title']}")
    print(f"Source: {article['source']}")
    print(f"Link: {article['link']}")
    if article.get('published'):
        print(f"Published: {article['published']}")
    print("=" * 80)


# Example usage
if __name__ == "__main__":
    print("Real-Time News Monitoring System")
    print("=" * 50)
    
    # Create the monitor with default feeds and check every 2 minutes
    monitor = RealTimeNewsMonitor(check_interval=120)
    
    # Register our info callback
    monitor.register_callback(print_article_info)
    
    try:
        # Start monitoring
        monitor.start()
        
        print("\nMonitoring news feeds in real-time. Press Ctrl+C to stop.")
        
        # Keep the main thread alive
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nStopping monitoring...")
        monitor.stop()
        print("Monitoring stopped. Goodbye!")
