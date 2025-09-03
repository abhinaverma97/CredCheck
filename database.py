import sqlite3
import json
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_path=None):
        # Use provided path, or environment variable, or default to local file
        self.db_path = db_path or os.environ.get('DATABASE_URL') or 'news_analysis.db'
        
        # Handle PostgreSQL URLs from Render, but fallback to SQLite for simplicity
        if self.db_path.startswith('postgres://'):
            # For this demo, we'll still use SQLite, but in a production app
            # you would want to use a proper PostgreSQL client here
            self.db_path = os.path.join(os.path.dirname(__file__), 'news_analysis.db')
            logger.info(f"Using SQLite database at {self.db_path} instead of PostgreSQL")
        
        self._create_tables()

    def _create_tables(self):
        """Create the necessary tables if they don't exist."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                headline TEXT NOT NULL,
                is_fake BOOLEAN NOT NULL,
                credcheck_classification TEXT NOT NULL,
                claimbuster_results TEXT,
                source_type TEXT NOT NULL,
                analyzed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            ''')
            
            conn.commit()
            conn.close()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {e}")
            raise

    def save_analysis(self, headline, is_fake, credcheck_classification, claimbuster_results, source_type):
        """Save a news analysis to the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Generate current timestamp
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                "INSERT INTO news_analyses (headline, is_fake, credcheck_classification, claimbuster_results, source_type, analyzed_at) VALUES (?, ?, ?, ?, ?, ?)",
                (headline, is_fake, credcheck_classification, json.dumps(claimbuster_results), source_type, current_time)
            )
            
            conn.commit()
            conn.close()
            logger.info(f"Successfully saved analysis for headline: {headline[:50]}...")
        except Exception as e:
            logger.error(f"Error saving analysis to database: {e}")
            raise

    def get_recent_analyses(self, limit=10):
        """Get recent news analyses from the database."""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT * FROM news_analyses ORDER BY analyzed_at DESC LIMIT ?",
                (limit,)
            )
            
            rows = cursor.fetchall()
            analyses = []
            
            for row in rows:
                analysis = dict(row)
                analysis['claimbuster_results'] = json.loads(analysis['claimbuster_results'])
                analyses.append(analysis)
            
            conn.close()
            return analyses
        except Exception as e:
            logger.error(f"Error getting recent analyses: {e}")
            return []

    def get_statistics(self):
        """Get statistics about analyzed news."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get counts with proper error handling
            try:
                cursor.execute("SELECT COUNT(*) FROM news_analyses")
                total_count = cursor.fetchone()[0]
                
                if total_count == 0:
                    # Return empty stats if no data
                    return {
                        'total_count': 0,
                        'real_count': 0,
                        'fake_count': 0,
                        'real_percentage': 0,
                        'fake_percentage': 0,
                        'avg_credibility': 0,
                        'recent_analyses': []
                    }
                
                cursor.execute("SELECT COUNT(*) FROM news_analyses WHERE is_fake = 0")
                real_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(*) FROM news_analyses WHERE is_fake = 1")
                fake_count = cursor.fetchone()[0]
                
                # Verify counts add up
                if real_count + fake_count != total_count:
                    logger.warning(f"Count mismatch: total={total_count}, real={real_count}, fake={fake_count}")
                    # Recalculate total to ensure consistency
                    total_count = real_count + fake_count
                
                # Calculate percentages
                real_percentage = (real_count / total_count * 100) if total_count > 0 else 0
                fake_percentage = (fake_count / total_count * 100) if total_count > 0 else 0
                
                # Get average credibility score from claimbuster results
                cursor.execute("SELECT claimbuster_results FROM news_analyses")
                all_results = cursor.fetchall()
                
                total_score = 0
                score_count = 0
                
                for result in all_results:
                    try:
                        claimbuster_results = json.loads(result[0])
                        for claim in claimbuster_results:
                            if 'score' in claim:
                                total_score += claim['score']
                                score_count += 1
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON in claimbuster_results: {result[0]}")
                        continue
                
                avg_credibility = (total_score / score_count) if score_count > 0 else 0
                
                # Get recent analyses for charts
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM news_analyses ORDER BY analyzed_at DESC LIMIT 10")
                rows = cursor.fetchall()
                recent_analyses = []
                
                for row in rows:
                    analysis = dict(row)
                    analysis['claimbuster_results'] = json.loads(analysis['claimbuster_results'])
                    recent_analyses.append(analysis)
                
                conn.close()
                
                stats = {
                    'total_count': total_count,
                    'real_count': real_count,
                    'fake_count': fake_count,
                    'real_percentage': real_percentage,
                    'fake_percentage': fake_percentage,
                    'avg_credibility': avg_credibility * 100,  # Convert to percentage
                    'recent_analyses': recent_analyses
                }
                
                logger.info(f"Statistics calculated: total={total_count}, real={real_count}, fake={fake_count}")
                return stats
                
            except sqlite3.Error as e:
                logger.error(f"Database error while getting statistics: {e}")
                raise
                
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                'total_count': 0,
                'real_count': 0,
                'fake_count': 0,
                'real_percentage': 0,
                'fake_percentage': 0,
                'avg_credibility': 0,
                'recent_analyses': []
            } 