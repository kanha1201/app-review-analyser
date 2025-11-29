"""Main entry point for running the complete weekly pipeline."""
import logging
import sys
import os
from datetime import datetime, timedelta
from src.orchestrator.weekly_pipeline import WeeklyPipeline, run_pipeline
from config.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)
settings = get_settings()


def main():
    """Main function to run the pipeline."""
    logger.info("=" * 70)
    logger.info("WEEKLY REVIEW INSIGHTS PIPELINE")
    logger.info("=" * 70)
    
    google_api_key = os.getenv("GOOGLE_API_KEY") or settings.google_api_key
    
    if not google_api_key or len(google_api_key) < 10:
        logger.error("GOOGLE_API_KEY not set or invalid")
        logger.error("Please set it in .env file: GOOGLE_API_KEY=your-api-key")
        sys.exit(1)
    
    # Parse command line arguments
    week_start = None
    week_end = None
    skip_email = "--skip-email" in sys.argv or "-s" in sys.argv
    force_refresh = "--force-refresh" in sys.argv or "-f" in sys.argv
    
    if len(sys.argv) > 1:
        args = [arg for arg in sys.argv[1:] if arg not in ["--skip-email", "-s", "--force-refresh", "-f"]]
        if len(args) >= 2:
            try:
                # Format: YYYY-MM-DD
                week_start = datetime.strptime(args[0], "%Y-%m-%d")
                week_end = datetime.strptime(args[1], "%Y-%m-%d")
            except ValueError:
                logger.error("Invalid date format. Use: YYYY-MM-DD")
                sys.exit(1)
    
    try:
        results = run_pipeline(
            week_start=week_start,
            week_end=week_end,
            api_key=google_api_key,
            skip_email=skip_email,
            force_refresh=force_refresh
        )
        
        if results.get("success"):
            logger.info("\n✓ Pipeline completed successfully!")
            sys.exit(0)
        else:
            logger.error("\n✗ Pipeline completed with errors")
            if results.get("errors"):
                for error in results["errors"]:
                    logger.error(f"  - {error}")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"\n✗ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

