"""Main entry point for the application."""
import logging
import sys
from config.settings import get_settings
from src.tasks.fetch_reviews import ReviewFetchTask
from src.scheduler import ReviewScheduler

settings = get_settings()

# Setup logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='App Review Insights Analyser')
    parser.add_argument(
        '--mode',
        choices=['fetch', 'scheduler'],
        default='fetch',
        help='Run mode: fetch (one-time) or scheduler (continuous)'
    )
    parser.add_argument(
        '--weeks-min',
        type=int,
        default=None,
        help='Minimum weeks to look back'
    )
    parser.add_argument(
        '--weeks-max',
        type=int,
        default=None,
        help='Maximum weeks to look back'
    )
    
    args = parser.parse_args()
    
    if args.mode == 'fetch':
        logger.info("Running one-time review fetch...")
        task = ReviewFetchTask()
        stats = task.execute(
            weeks_min=args.weeks_min,
            weeks_max=args.weeks_max
        )
        logger.info(f"Fetch completed: {stats}")
        print(f"\nFetch Statistics:")
        print(f"  App Store: {stats['app_store']['created']} new reviews")
        print(f"  Google Play: {stats['google_play']['created']} new reviews")
        print(f"  Total: {stats['total_created']} new reviews")
    
    elif args.mode == 'scheduler':
        logger.info("Starting scheduler...")
        scheduler = ReviewScheduler()
        scheduler.start()


if __name__ == "__main__":
    main()

