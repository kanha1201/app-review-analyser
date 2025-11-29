"""Task for theme extraction and classification."""
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Review, Base
from src.analysis.theme_extractor import ThemeExtractor
from config.settings import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class ThemeClassificationTask:
    """Task to extract themes and classify reviews."""
    
    def __init__(self, database_url: str = None):
        # Use SQLite if PostgreSQL URL is not configured properly
        db_url = database_url or settings.database_url
        if db_url.startswith('postgresql://') and 'localhost' in db_url:
            try:
                from sqlalchemy import inspect
                engine = create_engine(db_url)
                inspect(engine)
            except:
                db_url = 'sqlite:///reviews.db'
        elif not db_url or db_url == 'postgresql://user:password@localhost:5432/reviews_db':
            db_url = 'sqlite:///reviews.db'
        
        self.database_url = db_url
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        # Create tables if they don't exist
        Base.metadata.create_all(self.engine)
    
    def execute(
        self,
        weeks_min: int = None,
        weeks_max: int = None,
        max_themes: int = 5
    ) -> dict:
        """
        Execute theme extraction and classification.
        
        Args:
            weeks_min: Minimum weeks to look back
            weeks_max: Maximum weeks to look back
            max_themes: Maximum number of themes (default: 5)
        
        Returns:
            Dictionary with classification statistics
        """
        logger.info("Starting theme extraction and classification task")
        
        weeks_min = weeks_min or settings.review_weeks_lookback_min
        weeks_max = weeks_max or settings.review_weeks_lookback_max
        
        # Calculate date range
        end_date = datetime.now() - timedelta(weeks=1)  # Up to last week
        start_date = datetime.now() - timedelta(weeks=weeks_max)
        
        session = self.SessionLocal()
        extractor = ThemeExtractor(session)
        
        stats = {
            'start_time': datetime.now().isoformat(),
            'themes_extracted': 0,
            'reviews_classified': 0,
            'theme_counts': {}
        }
        
        try:
            # Get unprocessed reviews
            logger.info(f"Fetching reviews from {start_date.date()} to {end_date.date()}")
            reviews = session.query(Review).filter(
                Review.review_date >= start_date,
                Review.review_date <= end_date,
                Review.processed_at.is_(None)  # Only unprocessed reviews
            ).all()
            
            if not reviews:
                logger.info("No unprocessed reviews found")
                # Get all reviews for theme extraction
                reviews = session.query(Review).filter(
                    Review.review_date >= start_date,
                    Review.review_date <= end_date
                ).limit(500).all()  # Use sample for theme extraction
            
            logger.info(f"Found {len(reviews)} reviews to process")
            
            if not reviews:
                logger.warning("No reviews found in date range")
                return stats
            
            # Step 1: Extract themes
            logger.info("Step 1: Extracting themes from reviews...")
            themes = extractor.extract_themes_from_reviews(reviews, max_themes=max_themes)
            stats['themes_extracted'] = len(themes)
            
            logger.info(f"Extracted themes: {[t.name for t in themes]}")
            
            # Step 2: Classify all reviews into themes
            logger.info("Step 2: Classifying reviews into themes...")
            all_reviews = session.query(Review).filter(
                Review.review_date >= start_date,
                Review.review_date <= end_date
            ).all()
            
            theme_counts = extractor.classify_reviews_into_themes(
                all_reviews,
                themes,
                batch_size=10
            )
            
            stats['theme_counts'] = theme_counts
            stats['reviews_classified'] = sum(theme_counts.values())
            
            # Mark reviews as processed
            for review in all_reviews:
                review.processed_at = datetime.now()
            
            session.commit()
            
            # Step 3: Get top themes by count
            logger.info("Step 3: Getting top themes by count...")
            top_themes = extractor.get_top_themes_by_count(start_date, end_date, top_n=max_themes)
            stats['top_themes'] = top_themes
            
            stats['end_time'] = datetime.now().isoformat()
            
            logger.info("Theme classification completed successfully")
            logger.info(f"Theme counts: {theme_counts}")
            
        except Exception as e:
            logger.error(f"Error in theme classification task: {e}")
            import traceback
            traceback.print_exc()
            raise
        finally:
            session.close()
        
        return stats


def run_classify_task():
    """Entry point for running the classification task."""
    task = ThemeClassificationTask()
    return task.execute()

