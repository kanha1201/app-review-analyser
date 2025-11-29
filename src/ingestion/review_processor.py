"""Review processor for cleaning and filtering reviews."""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from src.utils.pii_remover import PIIRemover
from src.utils.language_detector import LanguageDetector
from config.settings import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class ReviewProcessor:
    """Process and clean reviews before storage."""
    
    def __init__(self, min_words: int = 4, english_only: bool = True):
        """
        Initialize review processor.
        
        Args:
            min_words: Minimum word count (default: 4, meaning > 3 words)
            english_only: Filter non-English reviews (default: True)
        """
        self.pii_remover = PIIRemover()
        self.language_detector = LanguageDetector()
        self.min_words = min_words
        self.english_only = english_only
    
    def process_reviews(
        self,
        reviews: List[Dict],
        weeks_min: Optional[int] = None,
        weeks_max: Optional[int] = None
    ) -> List[Dict]:
        """
        Process reviews: filter by date range and clean text.
        
        Args:
            reviews: List of raw review dictionaries
            weeks_min: Minimum weeks to look back (default: from settings)
            weeks_max: Maximum weeks to look back (default: from settings)
        
        Returns:
            List of processed review dictionaries
        """
        weeks_min = weeks_min or settings.review_weeks_lookback_min
        weeks_max = weeks_max or settings.review_weeks_lookback_max
        
        # Calculate date range
        end_date = datetime.now() - timedelta(weeks=1)  # Up to last week
        start_date = datetime.now() - timedelta(weeks=weeks_max)
        
        logger.info(f"Processing reviews from {start_date.date()} to {end_date.date()}")
        
        processed_reviews = []
        
        for review in reviews:
            try:
                # Filter by date range
                review_date = review.get('review_date')
                if not isinstance(review_date, datetime):
                    logger.warning(f"Invalid review date: {review_date}")
                    continue
                
                if not (start_date <= review_date <= end_date):
                    continue
                
                # Clean text
                review_text = review.get('review_text', '')
                title = review.get('title', '')
                
                # Filter: Check word count (must have more than min_words)
                word_count = self.language_detector.count_words(review_text)
                if word_count <= self.min_words:
                    logger.debug(f"Skipping review with {word_count} words (min: {self.min_words + 1})")
                    continue
                
                # Filter: Check if English (if english_only is enabled)
                if self.english_only and not self.language_detector.is_english(review_text):
                    logger.debug(f"Skipping non-English review: {review_text[:50]}...")
                    continue
                
                cleaned_text = self.pii_remover.clean_text(review_text)
                cleaned_title = self.pii_remover.clean_text(title) if title else None
                
                # Skip if text is empty after cleaning
                if not cleaned_text.strip():
                    logger.warning("Review text is empty after cleaning, skipping")
                    continue
                
                # Check if PII was detected (for logging)
                if self.pii_remover.contains_pii(review_text):
                    logger.info(f"PII detected and removed from review dated {review_date}")
                
                # Create processed review
                processed_review = {
                    'platform': review.get('platform'),
                    'rating': review.get('rating'),
                    'title': cleaned_title,
                    'review_text': review_text,  # Keep original for reference
                    'cleaned_text': cleaned_text,  # Store cleaned version
                    'review_date': review_date,
                    'app_version': review.get('app_version'),
                    'raw_data': review.get('raw_data', {})
                }
                
                processed_reviews.append(processed_review)
                
            except Exception as e:
                logger.error(f"Error processing review: {e}")
                continue
        
        logger.info(f"Processed {len(processed_reviews)} reviews (filtered from {len(reviews)})")
        return processed_reviews
    
    def filter_by_date_range(
        self,
        reviews: List[Dict],
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """
        Filter reviews by exact date range.
        
        Args:
            reviews: List of review dictionaries
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
        
        Returns:
            Filtered list of reviews
        """
        filtered = [
            review for review in reviews
            if isinstance(review.get('review_date'), datetime)
            and start_date <= review['review_date'] <= end_date
        ]
        return filtered

