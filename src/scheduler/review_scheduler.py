"""Scheduler for review fetching tasks."""
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime
from src.tasks.fetch_reviews import ReviewFetchTask
from config.settings import get_settings
import logging
import pytz

logger = logging.getLogger(__name__)
settings = get_settings()


class ReviewScheduler:
    """Scheduler for automated review fetching."""
    
    def __init__(self):
        self.scheduler = BlockingScheduler(timezone=pytz.timezone(settings.review_fetch_timezone))
        self.task = ReviewFetchTask()
    
    def setup_schedule(self):
        """Setup the scheduled job based on configuration."""
        # Parse day and time from settings
        day = settings.review_fetch_day.lower()
        time_str = settings.review_fetch_time
        
        # Map day names to cron day numbers (Monday=0, Sunday=6)
        day_map = {
            'monday': 0, 'tuesday': 1, 'wednesday': 2, 'thursday': 3,
            'friday': 4, 'saturday': 5, 'sunday': 6
        }
        
        day_of_week = day_map.get(day, 0)  # Default to Monday
        
        # Parse time (format: HH:MM)
        try:
            hour, minute = map(int, time_str.split(':'))
        except ValueError:
            logger.warning(f"Invalid time format: {time_str}, using 09:00")
            hour, minute = 9, 0
        
        # Create cron trigger
        trigger = CronTrigger(
            day_of_week=day_of_week,
            hour=hour,
            minute=minute,
            timezone=settings.review_fetch_timezone
        )
        
        # Add job
        self.scheduler.add_job(
            func=self._run_fetch_task,
            trigger=trigger,
            id='fetch_reviews',
            name='Fetch Reviews from App Store and Google Play',
            replace_existing=True
        )
        
        logger.info(
            f"Scheduled review fetch task: Every {day.capitalize()} at {time_str} "
            f"({settings.review_fetch_timezone})"
        )
    
    def _run_fetch_task(self):
        """Wrapper for running the fetch task."""
        try:
            logger.info("Scheduled review fetch task started")
            stats = self.task.execute()
            logger.info(f"Review fetch completed: {stats}")
        except Exception as e:
            logger.error(f"Error in scheduled review fetch task: {e}")
    
    def start(self):
        """Start the scheduler."""
        self.setup_schedule()
        logger.info("Starting review fetch scheduler...")
        try:
            self.scheduler.start()
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
    
    def run_once(self):
        """Run the fetch task once immediately (for testing)."""
        logger.info("Running review fetch task once...")
        return self.task.execute()


if __name__ == "__main__":
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    scheduler = ReviewScheduler()
    
    # For testing, run once
    # scheduler.run_once()
    
    # For production, start scheduler
    scheduler.start()

