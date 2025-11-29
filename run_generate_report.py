"""Entry point for generating weekly reports."""
import logging
import sys
import os
from datetime import datetime, timedelta
from src.tasks.generate_weekly_report import GenerateWeeklyReportTask
from config.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)
settings = get_settings()


def print_report(report: dict):
    """Pretty print the weekly report."""
    print("\n" + "=" * 70)
    print("WEEKLY PRODUCT PULSE")
    print("=" * 70)
    print(f"\nTitle: {report.get('title', 'N/A')}")
    print(f"\nOverview:")
    print(f"  {report.get('overview', 'N/A')}")
    
    print(f"\nTop Themes:")
    for i, theme in enumerate(report.get('themes', []), 1):
        print(f"  {i}. {theme.get('name', 'N/A')}")
        print(f"     {theme.get('summary', 'N/A')}")
    
    print(f"\nUser Quotes:")
    for i, quote in enumerate(report.get('quotes', []), 1):
        theme_name = quote.get('theme', 'Unknown Theme')
        quote_text = quote.get('text', 'N/A')
        print(f"  {i}. [{theme_name}] \"{quote_text}\"")
    
    print(f"\nAction Ideas:")
    for i, action in enumerate(report.get('actions', []), 1):
        theme_name = action.get('theme', 'Unknown Theme')
        action_text = action.get('text', 'N/A')
        print(f"  {i}. [{theme_name}] {action_text}")
    
    print("\n" + "=" * 70)
    
    # Word count
    text_parts = [
        report.get("title", ""),
        report.get("overview", ""),
        " ".join([t.get("summary", "") for t in report.get("themes", [])]),
        " ".join([q.get("text", "") for q in report.get("quotes", [])]),
        " ".join([a.get("text", "") for a in report.get("actions", [])])
    ]
    word_count = len(" ".join(text_parts).split())
    print(f"Word Count: {word_count} / 250")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("Weekly Report Generation")
    logger.info("=" * 70)
    
    google_api_key = os.getenv("GOOGLE_API_KEY") or settings.google_api_key
    
    if not google_api_key or len(google_api_key) < 10:
        logger.error("GOOGLE_API_KEY not set or invalid")
        logger.error("Please set it in .env file: GOOGLE_API_KEY=your-api-key")
        sys.exit(1)
    
    # Parse command line arguments for week dates (optional)
    week_start = None
    week_end = None
    
    if len(sys.argv) > 1:
        try:
            # Format: YYYY-MM-DD
            week_start = datetime.strptime(sys.argv[1], "%Y-%m-%d")
            if len(sys.argv) > 2:
                week_end = datetime.strptime(sys.argv[2], "%Y-%m-%d")
            else:
                week_end = week_start + timedelta(days=6)
        except ValueError:
            logger.error("Invalid date format. Use: YYYY-MM-DD")
            sys.exit(1)
    
    try:
        task = GenerateWeeklyReportTask(api_key=google_api_key)
        report = task.execute(week_start=week_start, week_end=week_end)
        
        print_report(report)
        
        logger.info("Weekly report generated successfully!")
        
    except Exception as e:
        logger.error(f"Failed to generate weekly report: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

