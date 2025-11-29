"""App Store review fetcher."""
from app_store_scraper import AppStore
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from config.settings import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()

# Try to import RSS fallback fetcher
try:
    from src.ingestion.app_store_rss_fetcher import AppStoreRSSFetcher
    HAS_RSS_FETCHER = True
except ImportError:
    HAS_RSS_FETCHER = False


class AppStoreFetcher:
    """Fetcher for App Store reviews."""
    
    def __init__(self, app_id: Optional[str] = None, country: Optional[str] = None, app_name: Optional[str] = None):
        self.app_id = app_id or settings.app_store_app_id
        self.country = country or settings.app_store_country
        self.app_name = app_name or "groww"  # App name is required by app-store-scraper
    
    def fetch_reviews(
        self,
        days_back: int = 84,
        max_reviews: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch reviews from App Store.
        
        Args:
            days_back: Number of days to look back (default: 84 for 12 weeks)
            max_reviews: Maximum number of reviews to fetch (None for all)
        
        Returns:
            List of review dictionaries
        """
        try:
            logger.info(f"Fetching App Store reviews for app_id={self.app_id}, country={self.country}")
            
            # Try multiple app name variations if first attempt fails
            app_names_to_try = [
                self.app_name,
                "Groww: Stocks, Mutual Fund, IPO",
                "Groww",
                "groww"
            ]
            
            app = None
            reviews_fetched = False
            
            for app_name_attempt in app_names_to_try:
                try:
                    logger.info(f"Trying app_name: {app_name_attempt}")
                    app = AppStore(
                        country=self.country,
                        app_name=app_name_attempt,
                        app_id=self.app_id
                    )
                    
                    # Fetch reviews with smaller batches to avoid rate limiting
                    batch_size = min(max_reviews or 200, 200)  # Limit to 200 at a time
                    app.review(how_many=batch_size)
                    
                    if app.reviews and len(app.reviews) > 0:
                        reviews_fetched = True
                        logger.info(f"Successfully fetched reviews with app_name: {app_name_attempt}")
                        break
                except Exception as e:
                    logger.warning(f"Failed with app_name '{app_name_attempt}': {e}")
                    continue
            
            if not reviews_fetched or not app or not app.reviews:
                logger.warning("Primary scraper failed. Trying RSS feed fallback...")
                
                # Try RSS feed as fallback
                if HAS_RSS_FETCHER:
                    try:
                        rss_fetcher = AppStoreRSSFetcher(app_id=self.app_id, country=self.country)
                        rss_reviews = rss_fetcher.fetch_reviews(max_reviews=max_reviews or 500)
                        if rss_reviews:
                            logger.info(f"Successfully fetched {len(rss_reviews)} reviews from RSS feed")
                            return rss_reviews
                    except Exception as e:
                        logger.warning(f"RSS feed fallback also failed: {e}")
                
                logger.warning("Could not fetch App Store reviews. This may be due to:")
                logger.warning("1. App Store rate limiting or blocking automated requests")
                logger.warning("2. Network/firewall restrictions")
                logger.warning("3. App Store API changes or app-store-scraper library issues")
                logger.warning("4. App Store may require authentication or have anti-scraping measures")
                logger.info("Continuing with available reviews from other sources...")
                return []
            
            reviews = []
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            for review in app.reviews:
                try:
                    # Parse review date
                    review_date = self._parse_date(review.get('date'))
                    
                    # Skip if review is too old
                    if review_date < cutoff_date:
                        continue
                    
                    review_dict = {
                        'platform': 'app_store',
                        'rating': review.get('rating'),
                        'title': review.get('title', ''),
                        'review_text': review.get('review', ''),
                        'review_date': review_date,
                        'app_version': review.get('appVersion'),
                        'raw_data': {
                            'developer_response': review.get('developerResponse'),
                            'id': review.get('id'),
                        }
                    }
                    
                    reviews.append(review_dict)
                    
                except Exception as e:
                    logger.warning(f"Error processing App Store review: {e}")
                    continue
            
            logger.info(f"Fetched {len(reviews)} App Store reviews")
            return reviews
            
        except Exception as e:
            logger.error(f"Error fetching App Store reviews: {e}")
            raise
    
    def _parse_date(self, date_value) -> datetime:
        """Parse date from various formats."""
        if isinstance(date_value, datetime):
            return date_value
        if isinstance(date_value, str):
            # Try common date formats
            formats = [
                '%Y-%m-%d %H:%M:%S',
                '%Y-%m-%d',
                '%d %b %Y',
                '%B %d, %Y'
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date_value, fmt)
                except ValueError:
                    continue
        # Default to current date if parsing fails
        logger.warning(f"Could not parse date: {date_value}, using current date")
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

