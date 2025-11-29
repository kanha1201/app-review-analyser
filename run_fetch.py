"""Run the review fetch task."""
import logging
import sys

# Check for required packages
try:
    from sqlalchemy import create_engine, func
    from sqlalchemy.orm import sessionmaker
    from src.tasks.fetch_reviews import ReviewFetchTask
    from src.database.models import Review
    from config.settings import get_settings
except ImportError as e:
    print("=" * 70)
    print("ERROR: Missing required packages")
    print("=" * 70)
    print("Please install required packages:")
    print("  pip install sqlalchemy psycopg2-binary google-play-scraper app-store-scraper beautifulsoup4 pydantic-settings python-dotenv")
    print(f"\nMissing: {e}")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)
settings = get_settings()

if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("Fetching Reviews from App Store and Google Play Store")
    logger.info("=" * 70)
    
    try:
        task = ReviewFetchTask()
        stats = task.execute()
        
        logger.info("\n" + "=" * 70)
        logger.info("FETCH SUMMARY")
        logger.info("=" * 70)
        logger.info(f"App Store: Fetched {stats['app_store']['fetched']}, Created {stats['app_store']['created']}")
        logger.info(f"Google Play: Fetched {stats['google_play']['fetched']}, Created {stats['google_play']['created']}")
        logger.info(f"Total New Reviews Created: {stats['total_created']}")
        logger.info("=" * 70)
        
        # Check total reviews in database
        session = task.SessionLocal()
        total_count = session.query(func.count(Review.id)).scalar()
        app_store_count = session.query(func.count(Review.id)).filter(Review.platform == 'app_store').scalar()
        google_play_count = session.query(func.count(Review.id)).filter(Review.platform == 'google_play').scalar()
        
        logger.info(f"\nTotal Reviews in Database: {total_count}")
        logger.info(f"  - App Store: {app_store_count}")
        logger.info(f"  - Google Play: {google_play_count}")
        logger.info("=" * 70)
        
        session.close()
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
