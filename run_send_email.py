"""Entry point for sending weekly report emails."""
import logging
import sys
import os
from datetime import datetime, timedelta
from src.tasks.send_weekly_email import SendWeeklyEmailTask
from config.settings import get_settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)
settings = get_settings()


def print_email(email_content: dict):
    """Pretty print the email."""
    print("\n" + "=" * 70)
    print("EMAIL DRAFT")
    print("=" * 70)
    print(f"\nTo: {', '.join(settings.email_recipient_list)}")
    print(f"Subject: {email_content['email_subject']}")
    print("\n" + "-" * 70)
    print(email_content['email_body'])
    print("-" * 70)
    print(f"\nWord Count: {len(email_content['email_body'].split())} words")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    logger.info("=" * 70)
    logger.info("Weekly Report Email Sender")
    logger.info("=" * 70)
    
    google_api_key = os.getenv("GOOGLE_API_KEY") or settings.google_api_key
    
    if not google_api_key or len(google_api_key) < 10:
        logger.error("GOOGLE_API_KEY not set or invalid")
        logger.error("Please set it in .env file: GOOGLE_API_KEY=your-api-key")
        sys.exit(1)
    
    # Check for dry-run flag
    dry_run = "--dry-run" in sys.argv or "-d" in sys.argv
    
    # Parse command line arguments
    week_start = None
    week_end = None
    report_id = None
    
    if len(sys.argv) > 1 and sys.argv[1] not in ["--dry-run", "-d"]:
        if len(sys.argv) >= 3:
            try:
                # Format: YYYY-MM-DD
                week_start = datetime.strptime(sys.argv[1], "%Y-%m-%d")
                week_end = datetime.strptime(sys.argv[2], "%Y-%m-%d")
            except ValueError:
                # Try as report ID
                report_id = sys.argv[1]
        else:
            report_id = sys.argv[1]
    
    try:
        task = SendWeeklyEmailTask(api_key=google_api_key)
        result = task.execute(
            week_start=week_start,
            week_end=week_end,
            report_id=report_id,
            dry_run=dry_run
        )
        
        print_email(result)
        
        if dry_run:
            logger.info("DRY RUN completed - email was not sent")
        elif result.get("send_status", {}).get("success"):
            logger.info("Email sent successfully!")
            logger.info(f"Sent at: {result.get('send_status', {}).get('sent_at')}")
        else:
            logger.error("Email sending failed")
            logger.error(f"Error: {result.get('send_status', {}).get('error')}")
            sys.exit(1)
        
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

