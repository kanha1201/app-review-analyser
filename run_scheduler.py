"""Entry point for running the scheduled pipeline."""
import logging
import sys
import os
from src.scheduler.pipeline_scheduler import run_scheduler
from config.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)
settings = get_settings()


def main():
    """Main function to start the scheduler."""
    logger.info("=" * 70)
    logger.info("WEEKLY REVIEW INSIGHTS PIPELINE SCHEDULER")
    logger.info("=" * 70)
    
    google_api_key = os.getenv("GOOGLE_API_KEY") or settings.google_api_key
    
    if not google_api_key or len(google_api_key) < 10:
        logger.error("GOOGLE_API_KEY not set or invalid")
        logger.error("Please set it in .env file: GOOGLE_API_KEY=your-api-key")
        sys.exit(1)
    
    skip_email = "--skip-email" in sys.argv or "-s" in sys.argv
    
    logger.info("Starting scheduler...")
    logger.info(f"Configuration:")
    logger.info(f"  Day: {settings.review_fetch_day}")
    logger.info(f"  Time: {settings.review_fetch_time}")
    logger.info(f"  Timezone: {settings.review_fetch_timezone}")
    if skip_email:
        logger.info(f"  Email: DISABLED (skip-email flag)")
    else:
        logger.info(f"  Email: ENABLED")
    logger.info("=" * 70)
    
    try:
        run_scheduler(
            api_key=google_api_key,
            skip_email=skip_email
        )
    except KeyboardInterrupt:
        logger.info("\nScheduler stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Scheduler failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

