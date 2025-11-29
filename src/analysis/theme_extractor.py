"""Theme extraction and classification service."""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func
from src.llm.gemini_client import GeminiClient
from src.database.models import Review, Theme, ReviewTheme
from src.database.repository import ReviewRepository
import logging
import uuid

logger = logging.getLogger(__name__)


class ThemeExtractor:
    """Extract themes and classify reviews."""
    
    def __init__(self, session: Session):
        self.session = session
        self.repository = ReviewRepository(session)
        self.gemini_client = GeminiClient()
        self.default_theme_name = "General Feedback"
    
    def extract_themes_from_reviews(self, reviews: List[Review], max_themes: int = 5) -> List[Theme]:
        """
        Extract top themes from reviews using LLM.
        
        Args:
            reviews: List of Review objects
            max_themes: Maximum number of themes (default: 5)
        
        Returns:
            List of Theme objects
        """
        logger.info(f"Extracting themes from {len(reviews)} reviews")
        
        # Prepare review data for LLM
        review_data = []
        for review in reviews:
            review_data.append({
                'review_text': review.review_text,
                'cleaned_text': review.cleaned_text,
                'rating': review.rating
            })
        
        # Call LLM to extract themes
        try:
            result = self.gemini_client.extract_themes(review_data, max_themes=max_themes)
            themes_data = result.get("themes", [])
        except Exception as e:
            logger.error(f"Error extracting themes: {e}")
            # Fallback: create default theme
            return [self._get_or_create_default_theme()]
        
        # Create or get Theme objects
        themes = []
        for theme_data in themes_data:
            theme_name = theme_data.get("name", "").strip()
            if not theme_name:
                continue
            
            # Check if theme already exists
            existing_theme = self.session.query(Theme).filter(
                Theme.name == theme_name
            ).first()
            
            if existing_theme:
                themes.append(existing_theme)
            else:
                # Create new theme
                theme = Theme(
                    name=theme_name,
                    description=theme_data.get("description", "")
                )
                self.session.add(theme)
                themes.append(theme)
        
        self.session.commit()
        
        if not themes:
            # Fallback to default theme
            themes = [self._get_or_create_default_theme()]
        
        logger.info(f"Created/found {len(themes)} themes")
        return themes
    
    def classify_reviews_into_themes(
        self,
        reviews: List[Review],
        themes: List[Theme],
        batch_size: int = 10
    ) -> Dict[str, int]:
        """
        Classify reviews into themes.
        
        Args:
            reviews: List of Review objects to classify
            themes: List of Theme objects
            batch_size: Number of reviews to process per LLM call
        
        Returns:
            Dictionary mapping theme names to counts
        """
        logger.info(f"Classifying {len(reviews)} reviews into {len(themes)} themes")
        
        # Prepare themes data for LLM
        themes_data = [
            {"name": theme.name, "description": theme.description or ""}
            for theme in themes
        ]
        
        # Process reviews in batches
        theme_counts = {theme.name: 0 for theme in themes}
        unclassified_count = 0
        
        import time
        
        for i in range(0, len(reviews), batch_size):
            batch = reviews[i:i + batch_size]
            batch_num = i//batch_size + 1
            logger.info(f"Processing batch {batch_num} ({len(batch)} reviews)")
            
            # Rate limiting: Free tier allows 15 requests/minute
            # Add delay between batches to stay under limit (4+ seconds between batches)
            if batch_num > 1:
                delay = 4.5  # 4.5 seconds = ~13 requests/minute (safe margin)
                logger.debug(f"Waiting {delay}s before next batch (rate limiting)")
                time.sleep(delay)
            
            # Prepare review data
            review_data = []
            for review in batch:
                review_data.append({
                    'id': str(review.id),
                    'review_text': review.review_text,
                    'cleaned_text': review.cleaned_text,
                    'rating': review.rating
                })
            
            try:
                # Classify batch
                classifications = self.gemini_client.classify_reviews(
                    review_data,
                    themes_data
                )
                
                # Process classifications
                for classification in classifications:
                    review_id_str = classification.get("review_id", "")
                    theme_name = classification.get("theme_name", "").strip()
                    reason = classification.get("reason", "")
                    
                    # Find review
                    try:
                        review_id = uuid.UUID(review_id_str)
                        review = self.session.get(Review, review_id)
                        
                        if not review:
                            logger.warning(f"Review {review_id_str} not found")
                            continue
                        
                        # Find theme
                        theme = next((t for t in themes if t.name == theme_name), None)
                        
                        if not theme:
                            # Invalid theme - use default
                            logger.warning(f"Invalid theme '{theme_name}', using default")
                            theme = self._get_or_create_default_theme()
                            theme_name = theme.name
                        
                        # Check if already classified
                        existing = self.session.query(ReviewTheme).filter(
                            ReviewTheme.review_id == review.id
                        ).first()
                        
                        if existing:
                            # Update existing
                            existing.theme_id = theme.id
                        else:
                            # Create new classification
                            review_theme = ReviewTheme(
                                review_id=review.id,
                                theme_id=theme.id,
                                confidence_score=0.8  # Default confidence
                            )
                            self.session.add(review_theme)
                        
                        theme_counts[theme_name] = theme_counts.get(theme_name, 0) + 1
                        
                    except (ValueError, Exception) as e:
                        logger.warning(f"Error processing classification for {review_id_str}: {e}")
                        unclassified_count += 1
                        continue
                
                self.session.commit()
                
            except Exception as e:
                logger.error(f"Error classifying batch: {e}")
                # Mark reviews as unclassified
                for review in batch:
                    unclassified_count += 1
                continue
        
        logger.info(f"Classification complete. Theme counts: {theme_counts}")
        if unclassified_count > 0:
            logger.warning(f"{unclassified_count} reviews could not be classified")
        
        return theme_counts
    
    def get_top_themes_by_count(
        self,
        start_date: datetime,
        end_date: datetime,
        top_n: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get top themes by review count for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            top_n: Number of top themes to return
        
        Returns:
            List of theme dictionaries with counts
        """
        # Query theme counts
        theme_counts = self.session.query(
            Theme.name,
            Theme.description,
            func.count(ReviewTheme.id).label('count')
        ).join(
            ReviewTheme, Theme.id == ReviewTheme.theme_id
        ).join(
            Review, ReviewTheme.review_id == Review.id
        ).filter(
            Review.review_date >= start_date,
            Review.review_date <= end_date
        ).group_by(
            Theme.id, Theme.name, Theme.description
        ).order_by(
            func.count(ReviewTheme.id).desc()
        ).limit(top_n).all()
        
        result = []
        for name, description, count in theme_counts:
            result.append({
                'name': name,
                'description': description or '',
                'count': count
            })
        
        return result
    
    def _get_or_create_default_theme(self) -> Theme:
        """Get or create default theme for unclassified reviews."""
        default_theme = self.session.query(Theme).filter(
            Theme.name == self.default_theme_name
        ).first()
        
        if not default_theme:
            default_theme = Theme(
                name=self.default_theme_name,
                description="General user feedback and app experience"
            )
            self.session.add(default_theme)
            self.session.commit()
        
        return default_theme

