"""Task to send weekly report emails."""
import logging
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, WeeklyReport
from src.llm.gemini_client import GeminiClient
from src.email.email_draft_generator import EmailDraftGenerator
from src.email.email_sender import EmailSender
from config.settings import get_settings
import os
import json

logger = logging.getLogger(__name__)
settings = get_settings()


class SendWeeklyEmailTask:
    """Task to generate and send weekly report emails."""
    
    def __init__(
        self,
        database_url: str = None,
        api_key: str = None,
        product_name: str = "review-scraper"
    ):
        # Force SQLite for local development/testing
        sqlite_db_path = os.path.join(os.getcwd(), 'reviews.db')
        self.database_url = database_url or f"sqlite:///{sqlite_db_path}"
        logger.info(f"Using database: {self.database_url}")
        
        self.engine = create_engine(self.database_url)
        self.SessionLocal = sessionmaker(bind=self.engine)
        
        Base.metadata.create_all(self.engine)
        
        self.api_key = api_key or settings.google_api_key
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY is required for LLM operations.")
        
        self.gemini_client = GeminiClient(api_key=self.api_key)
        self.email_generator = EmailDraftGenerator(
            gemini_client=self.gemini_client,
            product_name=product_name
        )
        self.email_sender = EmailSender()
    
    def execute(
        self,
        week_start: datetime = None,
        week_end: datetime = None,
        report_id: str = None,
        dry_run: bool = False
    ) -> dict:
        """
        Generate and send weekly report email.
        
        Args:
            week_start: Start of the week (optional, will fetch latest report if not provided)
            week_end: End of the week (optional)
            report_id: Specific report ID to send (optional)
            dry_run: If True, generate email but don't send it
            
        Returns:
            Dictionary with email generation and send status
        """
        session = self.SessionLocal()
        
        try:
            # Fetch weekly report
            if report_id:
                report = session.get(WeeklyReport, report_id)
                if not report:
                    raise ValueError(f"Report with ID {report_id} not found")
            elif week_start and week_end:
                # Find report for this week
                report = session.query(WeeklyReport).filter(
                    WeeklyReport.week_start_date == week_start,
                    WeeklyReport.week_end_date == week_end
                ).first()
                if not report:
                    raise ValueError(f"No report found for week {week_start.date()} to {week_end.date()}")
            else:
                # Get most recent report
                report = session.query(WeeklyReport).order_by(
                    WeeklyReport.created_at.desc()
                ).first()
                if not report:
                    raise ValueError("No weekly reports found in database")
            
            logger.info(f"Using report: {report.id} ({report.week_start_date.date()} to {report.week_end_date.date()})")
            
            # Extract weekly pulse from report
            weekly_pulse = report.report_content
            
            # Generate email
            logger.info("Generating email draft...")
            email_content = self.email_generator.generate_email(
                weekly_pulse=weekly_pulse,
                week_start=report.week_start_date,
                week_end=report.week_end_date
            )
            
            logger.info(f"Email generated: Subject='{email_content['subject']}'")
            logger.info(f"Email body length: {len(email_content['body'])} characters")
            logger.info(f"Email word count: {len(email_content['body'].split())} words")
            
            # Send email (or dry run)
            if dry_run:
                logger.info("DRY RUN: Email not sent")
                send_status = {
                    "success": False,
                    "dry_run": True,
                    "message": "Dry run - email not sent"
                }
            else:
                logger.info("Sending email...")
                send_status = self.email_sender.send_weekly_report_email(email_content)
                
                # Update report with email sent timestamp
                if send_status.get("success"):
                    report.email_sent_at = datetime.utcnow()
                    session.commit()
                    logger.info("Report updated with email sent timestamp")
            
            return {
                "report_id": str(report.id),
                "week_start": report.week_start_date.isoformat(),
                "week_end": report.week_end_date.isoformat(),
                "email_subject": email_content["subject"],
                "email_body": email_content["body"],
                "send_status": send_status
            }
            
        except Exception as e:
            logger.error(f"Error sending weekly email: {e}")
            session.rollback()
            raise
        finally:
            session.close()


def run_send_email(
    week_start: datetime = None,
    week_end: datetime = None,
    report_id: str = None,
    api_key: str = None,
    dry_run: bool = False
):
    """Run the weekly email sending task."""
    task = SendWeeklyEmailTask(api_key=api_key)
    return task.execute(
        week_start=week_start,
        week_end=week_end,
        report_id=report_id,
        dry_run=dry_run
    )

