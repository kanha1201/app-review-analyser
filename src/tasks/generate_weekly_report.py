"""Task to generate weekly reports."""
import logging
from datetime import datetime, timedelta
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base
from src.llm.gemini_client import GeminiClient
from src.reporting.weekly_report_generator import WeeklyReportGenerator
from config.settings import get_settings
import os

logger = logging.getLogger(__name__)
settings = get_settings()


class GenerateWeeklyReportTask:
    """Task to generate weekly reports from classified reviews."""
    
    def __init__(self, database_url: str = None, api_key: str = None):
        # Force SQLite for local development/testing
        sqlite_db_path = os.path.join(os.getcwd(), 'reviews.db')
        self.database_url = database_url or f"sqlite:///{sqlite_db_path}"
        logger.info(f"Using database for report generation: {self.database_url}")
        
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        Base.metadata.create_all(self.engine)
        
        self.api_key = api_key or settings.google_api_key
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is required for LLM operations.")
        
        self.gemini_client = GeminiClient(api_key=self.api_key)
    
    def execute(
        self,
        week_start: datetime = None,
        week_end: datetime = None,
        save_to_db: bool = True
    ) -> dict:
        """
        Generate weekly report.
        
        Args:
            week_start: Start of the week (default: last week Monday)
            week_end: End of the week (default: last week Sunday)
            save_to_db: Whether to save report to database
            
        Returns:
            Generated report dictionary
        """
        session = self.SessionLocal()
        
        try:
            # Default to last week if not specified
            if not week_start or not week_end:
                today = datetime.now()
                # Find last Monday
                days_since_monday = (today.weekday()) % 7
                last_monday = today - timedelta(days=days_since_monday + 7)
                week_start = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
                week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
            
            logger.info(f"Generating weekly report for {week_start.date()} to {week_end.date()}")
            
            generator = WeeklyReportGenerator(
                session=session,
                gemini_client=self.gemini_client
            )
            
            report = generator.generate_report(week_start, week_end)
            
            if save_to_db:
                saved_report = generator.save_report(report)
                report["id"] = str(saved_report.id)
                logger.info("Report saved to database")
            
            return report
            
        except Exception as e:
            logger.error(f"Error generating weekly report: {e}")
            session.rollback()
            raise
        finally:
            session.close()


def run_generate_report(
    week_start: datetime = None,
    week_end: datetime = None,
    api_key: str = None
):
    """Run the weekly report generation task."""
    task = GenerateWeeklyReportTask(api_key=api_key)
    return task.execute(week_start=week_start, week_end=week_end)

