"""Scheduler for automated weekly pipeline execution."""
import logging
from datetime import datetime, time
from typing import Optional
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from src.orchestrator.weekly_pipeline import WeeklyPipeline
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class PipelineScheduler:
    """Schedules and runs the weekly pipeline automatically."""
    
    def __init__(
        self,
        api_key: str = None,
        skip_email: bool = False
    ):
        """
        Initialize the scheduler.
        
        Args:
            api_key: Google API key (default: from settings)
            skip_email: If True, skip email sending in scheduled runs
        """
        self.scheduler = BlockingScheduler()
        self.api_key = api_key or settings.google_api_key
        self.skip_email = skip_email
        
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is required for scheduled execution.")
    
    def schedule_weekly_run(
        self,
        day: str = None,
        hour: int = None,
        minute: int = None,
        timezone: str = None
    ):
        """
        Schedule weekly pipeline execution.
        
        Args:
            day: Day of week (default: from settings, e.g., "Monday")
            hour: Hour (default: from settings, e.g., 9)
            minute: Minute (default: from settings, e.g., 0)
            timezone: Timezone (default: from settings, e.g., "Asia/Kolkata")
        """
        day = day or settings.review_fetch_day
        time_str = settings.review_fetch_time.split(":")
        hour = hour or int(time_str[0])
        minute = minute or int(time_str[1]) if len(time_str) > 1 else 0
        timezone = timezone or settings.review_fetch_timezone
        
        # Map day name to cron day
        day_map = {
            "Monday": "mon",
            "Tuesday": "tue",
            "Wednesday": "wed",
            "Thursday": "thu",
            "Friday": "fri",
            "Saturday": "sat",
            "Sunday": "sun"
        }
        cron_day = day_map.get(day.capitalize(), "mon")
        
        logger.info(f"Scheduling weekly pipeline execution:")
        logger.info(f"  Day: {day}")
        logger.info(f"  Time: {hour:02d}:{minute:02d}")
        logger.info(f"  Timezone: {timezone}")
        
        def run_pipeline_job():
            """Job function to run the pipeline."""
            logger.info("=" * 70)
            logger.info(f"SCHEDULED PIPELINE EXECUTION - {datetime.now()}")
            logger.info("=" * 70)
            try:
                pipeline = WeeklyPipeline(api_key=self.api_key, skip_email=self.skip_email)
                results = pipeline.execute()
                if results.get("success"):
                    logger.info("Scheduled pipeline execution completed successfully")
                else:
                    logger.error("Scheduled pipeline execution completed with errors")
            except Exception as e:
                logger.error(f"Scheduled pipeline execution failed: {e}")
                import traceback
                logger.error(traceback.format_exc())
        
        # Schedule the job
        trigger = CronTrigger(
            day_of_week=cron_day,
            hour=hour,
            minute=minute,
            timezone=timezone
        )
        
        self.scheduler.add_job(
            run_pipeline_job,
            trigger=trigger,
            id='weekly_review_pipeline',
            name='Weekly Review Insights Pipeline',
            replace_existing=True
        )
        
        logger.info("Pipeline scheduled successfully")
    
    def start(self):
        """Start the scheduler (blocks until stopped)."""
        logger.info("Starting scheduler...")
        logger.info("Press Ctrl+C to stop")
        try:
            self.scheduler.start()
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
            raise
    
    def stop(self):
        """Stop the scheduler."""
        logger.info("Stopping scheduler...")
        self.scheduler.shutdown()


def run_scheduler(
    api_key: str = None,
    skip_email: bool = False,
    day: str = None,
    hour: int = None,
    minute: int = None,
    timezone: str = None
):
    """
    Run the scheduler with specified configuration.
    
    Args:
        api_key: Google API key
        skip_email: Skip email sending
        day: Day of week
        hour: Hour
        minute: Minute
        timezone: Timezone
    """
    scheduler = PipelineScheduler(api_key=api_key, skip_email=skip_email)
    scheduler.schedule_weekly_run(day=day, hour=hour, minute=minute, timezone=timezone)
    scheduler.start()

