"""Task for fetching reviews from both stores."""
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.ingestion import AppStoreFetcher, GooglePlayFetcher, ReviewProcessor
from src.database.repository import ReviewRepository
from config.settings import get_settings
import logging

logger = logging.getLogger(__name__)
settings = get_settings()


class ReviewFetchTask:
    """Task to fetch reviews from App Store and Google Play Store."""
    
    def __init__(self, database_url: str = None):
        # Use SQLite if PostgreSQL URL is not configured properly
        db_url = database_url or settings.database_url
        if db_url.startswith('postgresql://') and 'localhost' in db_url:
            # Try SQLite as fallback for testing
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
        from src.database.models import Base
        Base.metadata.create_all(self.engine)
        
        # Initialize fetchers
        self.app_store_fetcher = AppStoreFetcher()
        self.google_play_fetcher = GooglePlayFetcher()
        self.processor = ReviewProcessor()
    
    def execute(
        self,
        weeks_min: int = None,
        weeks_max: int = None,
        force_refresh: bool = False
    ) -> dict:
        """
        Execute the review fetching task.
        
        Args:
            weeks_min: Minimum weeks to look back
            weeks_max: Maximum weeks to look back
            force_refresh: If True, refetch all reviews even if they exist
        
        Returns:
            Dictionary with fetch statistics
        """
        logger.info("Starting review fetch task")
        
        weeks_min = weeks_min or settings.review_weeks_lookback_min
        weeks_max = weeks_max or settings.review_weeks_lookback_max
        
        stats = {
            'app_store': {'fetched': 0, 'created': 0, 'errors': 0},
            'google_play': {'fetched': 0, 'created': 0, 'errors': 0},
            'start_time': datetime.now().isoformat()
        }
        
        session = self.SessionLocal()
        repository = ReviewRepository(session)
        
        try:
            # Fetch App Store reviews
            try:
                logger.info("Fetching App Store reviews...")
                app_store_reviews = self.app_store_fetcher.fetch_reviews(
                    days_back=weeks_max * 7
                )
                stats['app_store']['fetched'] = len(app_store_reviews)
                
                # Process reviews
                processed_app_store = self.processor.process_reviews(
                    app_store_reviews,
                    weeks_min=weeks_min,
                    weeks_max=weeks_max
                )
                
                # Store reviews
                created_count = repository.bulk_create_reviews(processed_app_store)
                stats['app_store']['created'] = created_count
                logger.info(f"Created {created_count} new App Store reviews")
                
            except Exception as e:
                logger.error(f"Error fetching App Store reviews: {e}")
                stats['app_store']['errors'] = 1
            
            # Fetch Google Play reviews
            try:
                logger.info("Fetching Google Play reviews...")
                google_play_reviews = self.google_play_fetcher.fetch_reviews(
                    days_back=weeks_max * 7
                )
                stats['google_play']['fetched'] = len(google_play_reviews)
                
                # Process reviews
                processed_google_play = self.processor.process_reviews(
                    google_play_reviews,
                    weeks_min=weeks_min,
                    weeks_max=weeks_max
                )
                
                # Store reviews
                created_count = repository.bulk_create_reviews(processed_google_play)
                stats['google_play']['created'] = created_count
                logger.info(f"Created {created_count} new Google Play reviews")
                
            except Exception as e:
                logger.error(f"Error fetching Google Play reviews: {e}")
                stats['google_play']['errors'] = 1
            
            stats['end_time'] = datetime.now().isoformat()
            stats['total_created'] = stats['app_store']['created'] + stats['google_play']['created']
            
            logger.info(f"Review fetch task completed. Created {stats['total_created']} new reviews")
            
        except Exception as e:
            logger.error(f"Error in review fetch task: {e}")
            raise
        finally:
            session.close()
        
        return stats


def run_fetch_task():
    """Entry point for running the fetch task."""
    task = ReviewFetchTask()
    return task.execute()

