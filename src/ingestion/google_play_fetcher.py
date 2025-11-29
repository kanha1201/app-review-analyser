"""Google Play Store review fetcher."""
from google_play_scraper import app, reviews, Sort
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from config.settings import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class GooglePlayFetcher:
    """Fetcher for Google Play Store reviews."""
    
    def __init__(self, app_id: Optional[str] = None, country: Optional[str] = None):
        self.app_id = app_id or settings.google_play_app_id
        self.country = country or settings.google_play_country
    
    def fetch_reviews(
        self,
        days_back: int = 84,
        max_reviews: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch reviews from Google Play Store.
        
        Args:
            days_back: Number of days to look back (default: 84 for 12 weeks)
            max_reviews: Maximum number of reviews to fetch (None for all)
        
        Returns:
            List of review dictionaries
        """
        try:
            logger.info(f"Fetching Google Play reviews for app_id={self.app_id}, country={self.country}")
            
            reviews_list = []
            continuation_token = None
            cutoff_date = datetime.now() - timedelta(days=days_back)
            max_fetch = max_reviews or 5000
            fetched_count = 0
            
            while fetched_count < max_fetch:
                # Fetch batch of reviews
                result, continuation_token = reviews(
                    self.app_id,
                    lang='en',  # Language
                    country=self.country,
                    sort=Sort.NEWEST,  # Sort by newest first
                    count=200,  # Fetch 200 at a time
                    continuation_token=continuation_token
                )
                
                if not result:
                    break
                
                for review in result:
                    try:
                        # Parse review date
                        review_date = self._parse_timestamp(review.get('at'))
                        
                        # Skip if review is too old
                        if review_date < cutoff_date:
                            # Since we're sorting by newest, we can break early
                            continuation_token = None
                            break
                        
                        review_dict = {
                            'platform': 'google_play',
                            'rating': review.get('score'),
                            'title': None,  # Google Play doesn't have separate titles
                            'review_text': review.get('content', ''),
                            'review_date': review_date,
                            'app_version': review.get('appVersion'),
                            'raw_data': {
                                'reply_content': review.get('replyContent'),
                                'reply_at': review.get('repliedAt'),
                                'thumbs_up': review.get('thumbsUpCount'),
                                'id': review.get('reviewId'),
                            }
                        }
                        
                        reviews_list.append(review_dict)
                        fetched_count += 1
                        
                        if fetched_count >= max_fetch:
                            break
                            
                    except Exception as e:
                        logger.warning(f"Error processing Google Play review: {e}")
                        continue
                
                # Break if no more reviews
                if not continuation_token:
                    break
            
            logger.info(f"Fetched {len(reviews_list)} Google Play reviews")
            return reviews_list
            
        except Exception as e:
            logger.error(f"Error fetching Google Play reviews: {e}")
            raise
    
    def _parse_timestamp(self, timestamp) -> datetime:
        """Parse timestamp to datetime."""
        if isinstance(timestamp, datetime):
            return timestamp
        if isinstance(timestamp, (int, float)):
            # Assume Unix timestamp in milliseconds
            if timestamp > 1e10:
                timestamp = timestamp / 1000  # Convert milliseconds to seconds
            return datetime.fromtimestamp(timestamp)
        # Default to current date if parsing fails
        logger.warning(f"Could not parse timestamp: {timestamp}, using current date")
        return datetime.now()
    
    def fetch_reviews_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """
        Fetch reviews within a specific date range.
        
        Args:
            start_date: Start date for filtering
            end_date: End date for filtering
        
        Returns:
            List of review dictionaries within date range
        """
        # Calculate days back from end_date
        days_back = (datetime.now() - start_date).days + 7  # Add buffer
        all_reviews = self.fetch_reviews(days_back=days_back)
        
        # Filter by date range
        filtered_reviews = [
            review for review in all_reviews
            if start_date <= review['review_date'] <= end_date
        ]
        
        return filtered_reviews

