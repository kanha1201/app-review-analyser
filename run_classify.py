"""Run theme classification task."""
import logging
import sys

try:
    from src.tasks.classify_themes import ThemeClassificationTask
    from config.settings import get_settings
except ImportError as e:
    print("=" * 70)
    print("ERROR: Missing required packages")
    print("=" * 70)
    print(f"Error: {e}")
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
    import os
    
    logger.info("=" * 70)
    logger.info("Theme Extraction and Classification")
    logger.info("=" * 70)
    
    # Check API key from environment or settings
    api_key = os.getenv('GOOGLE_API_KEY') or settings.google_api_key
    
    if not api_key or len(api_key.strip()) < 10:
        logger.error("GOOGLE_API_KEY not set or invalid")
        logger.error("Please set it in one of these ways:")
        logger.error("1. Add to .env file: GOOGLE_API_KEY=your-api-key")
        logger.error("2. Set environment variable: export GOOGLE_API_KEY=your-api-key")
        logger.error("3. Pass as argument: GOOGLE_API_KEY=your-api-key python3 run_classify.py")
        sys.exit(1)
    
    # Override settings with environment variable if provided
    if os.getenv('GOOGLE_API_KEY'):
        settings.google_api_key = api_key
    
    try:
        task = ThemeClassificationTask()
        stats = task.execute()
        
        logger.info("\n" + "=" * 70)
        logger.info("CLASSIFICATION SUMMARY")
        logger.info("=" * 70)
        logger.info(f"Themes Extracted: {stats['themes_extracted']}")
        logger.info(f"Reviews Classified: {stats['reviews_classified']}")
        logger.info("\nTheme Counts:")
        for theme_name, count in stats.get('theme_counts', {}).items():
            logger.info(f"  - {theme_name}: {count} reviews")
        
        if 'top_themes' in stats:
            logger.info("\nTop Themes:")
            for i, theme in enumerate(stats['top_themes'], 1):
                logger.info(f"  {i}. {theme['name']}: {theme['count']} reviews")
                logger.info(f"     {theme['description']}")
        
        logger.info("=" * 70)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

