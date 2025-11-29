"""Main orchestrator for the weekly review insights pipeline."""
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base
from src.tasks.fetch_reviews import ReviewFetchTask
from src.tasks.classify_themes import ThemeClassificationTask
from src.tasks.generate_weekly_report import GenerateWeeklyReportTask
from src.tasks.send_weekly_email import SendWeeklyEmailTask
from config.settings import get_settings
import os

logger = logging.getLogger(__name__)
settings = get_settings()


class WeeklyPipeline:
    """Orchestrates the complete weekly review insights pipeline."""
    
    def __init__(
        self,
        database_url: str = None,
        api_key: str = None,
        skip_email: bool = False
    ):
        """
        Initialize the pipeline.
        
        Args:
            database_url: Database URL (default: SQLite)
            api_key: Google API key for Gemini
            skip_email: If True, skip email sending step
        """
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
        
        self.skip_email = skip_email
        
        # Initialize tasks
        self.fetch_task = ReviewFetchTask(database_url=self.database_url)
        self.classify_task = ThemeClassificationTask(database_url=self.database_url)
        # Note: classify_task uses GeminiClient internally, which reads API key from settings
        # We'll ensure API key is set in environment for it to work
        if self.api_key:
            os.environ['GOOGLE_API_KEY'] = self.api_key
        
        self.report_task = GenerateWeeklyReportTask(api_key=self.api_key)
        self.email_task = SendWeeklyEmailTask(api_key=self.api_key)
    
    def execute(
        self,
        week_start: datetime = None,
        week_end: datetime = None,
        force_refresh: bool = False
    ) -> Dict[str, Any]:
        """
        Execute the complete pipeline.
        
        Args:
            week_start: Start of the week (default: last week Monday)
            week_end: End of the week (default: last week Sunday)
            force_refresh: If True, re-fetch reviews even if already fetched
            
        Returns:
            Dictionary with execution results and statistics
        """
        results = {
            "started_at": datetime.utcnow().isoformat(),
            "steps": {},
            "errors": [],
            "success": False
        }
        
        # Calculate week dates if not provided
        if not week_start or not week_end:
            today = datetime.now()
            # Find last Monday
            days_since_monday = (today.weekday()) % 7
            last_monday = today - timedelta(days=days_since_monday + 7)
            week_start = last_monday.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)
        
        results["week_start"] = week_start.isoformat()
        results["week_end"] = week_end.isoformat()
        
        logger.info("=" * 70)
        logger.info("WEEKLY REVIEW INSIGHTS PIPELINE")
        logger.info("=" * 70)
        logger.info(f"Week: {week_start.date()} to {week_end.date()}")
        logger.info("=" * 70)
        
        try:
            # Step 1: Fetch Reviews
            logger.info("\n[STEP 1/4] Fetching reviews from App Store and Google Play Store...")
            try:
                fetch_stats = self.fetch_task.execute(
                    weeks_min=settings.review_weeks_lookback_min,
                    weeks_max=settings.review_weeks_lookback_max,
                    force_refresh=force_refresh
                )
                results["steps"]["fetch_reviews"] = {
                    "success": True,
                    "stats": fetch_stats
                }
                logger.info(f"✓ Fetched {fetch_stats.get('total_created', 0)} new reviews")
            except Exception as e:
                logger.error(f"✗ Step 1 failed: {e}")
                results["steps"]["fetch_reviews"] = {
                    "success": False,
                    "error": str(e)
                }
                results["errors"].append(f"Fetch reviews: {e}")
                # Continue pipeline even if fetch fails (might have existing reviews)
            
            # Step 2: Classify Themes
            logger.info("\n[STEP 2/4] Classifying reviews into themes...")
            try:
                classify_stats = self.classify_task.execute()
                results["steps"]["classify_themes"] = {
                    "success": True,
                    "stats": classify_stats
                }
                logger.info(f"✓ Classified {classify_stats.get('reviews_classified', 0)} reviews into {classify_stats.get('themes_discovered', 0)} themes")
            except Exception as e:
                logger.error(f"✗ Step 2 failed: {e}")
                results["steps"]["classify_themes"] = {
                    "success": False,
                    "error": str(e)
                }
                results["errors"].append(f"Classify themes: {e}")
                # Stop pipeline if classification fails
                results["completed_at"] = datetime.utcnow().isoformat()
                return results
            
            # Step 3: Generate Weekly Report
            logger.info("\n[STEP 3/4] Generating weekly report...")
            try:
                report = self.report_task.execute(
                    week_start=week_start,
                    week_end=week_end,
                    save_to_db=True
                )
                report_id = report.get("id") if "id" in report else None
                results["steps"]["generate_report"] = {
                    "success": True,
                    "report_id": report_id,
                    "word_count": len(" ".join([
                        report.get("title", ""),
                        report.get("overview", ""),
                        " ".join([t.get("summary", "") for t in report.get("themes", [])]),
                        " ".join([q.get("text", "") for q in report.get("quotes", [])]),
                        " ".join([a.get("text", "") for a in report.get("actions", [])])
                    ]).split())
                }
                logger.info(f"✓ Generated weekly report (ID: {report_id})")
            except Exception as e:
                logger.error(f"✗ Step 3 failed: {e}")
                results["steps"]["generate_report"] = {
                    "success": False,
                    "error": str(e)
                }
                results["errors"].append(f"Generate report: {e}")
                # Stop pipeline if report generation fails
                results["completed_at"] = datetime.utcnow().isoformat()
                return results
            
            # Step 4: Send Email
            if not self.skip_email:
                logger.info("\n[STEP 4/4] Sending weekly email...")
                try:
                    email_result = self.email_task.execute(
                        week_start=week_start,
                        week_end=week_end,
                        dry_run=False
                    )
                    send_status = email_result.get("send_status", {})
                    results["steps"]["send_email"] = {
                        "success": send_status.get("success", False),
                        "sent_at": send_status.get("sent_at"),
                        "recipients": send_status.get("recipients", [])
                    }
                    if send_status.get("success"):
                        logger.info(f"✓ Email sent successfully to {len(send_status.get('recipients', []))} recipients")
                    else:
                        logger.warning(f"⚠ Email sending failed: {send_status.get('error')}")
                except Exception as e:
                    logger.error(f"✗ Step 4 failed: {e}")
                    results["steps"]["send_email"] = {
                        "success": False,
                        "error": str(e)
                    }
                    results["errors"].append(f"Send email: {e}")
                    # Don't fail pipeline if email fails
            else:
                logger.info("\n[STEP 4/4] Skipping email (skip_email=True)")
                results["steps"]["send_email"] = {
                    "success": True,
                    "skipped": True
                }
            
            # Pipeline completed successfully
            results["success"] = True
            results["completed_at"] = datetime.utcnow().isoformat()
            
            logger.info("\n" + "=" * 70)
            logger.info("PIPELINE COMPLETED SUCCESSFULLY")
            logger.info("=" * 70)
            
            # Print summary
            self._print_summary(results)
            
        except Exception as e:
            logger.error(f"\n✗ Pipeline failed with error: {e}")
            results["success"] = False
            results["errors"].append(f"Pipeline execution: {e}")
            results["completed_at"] = datetime.utcnow().isoformat()
            import traceback
            logger.error(traceback.format_exc())
        
        return results
    
    def _print_summary(self, results: Dict[str, Any]):
        """Print execution summary."""
        logger.info("\nExecution Summary:")
        logger.info(f"  Week: {results.get('week_start', 'N/A')} to {results.get('week_end', 'N/A')}")
        
        for step_name, step_result in results.get("steps", {}).items():
            status = "✓" if step_result.get("success") else "✗"
            logger.info(f"  {status} {step_name.replace('_', ' ').title()}")
            if not step_result.get("success") and "error" in step_result:
                logger.info(f"    Error: {step_result['error']}")
        
        if results.get("errors"):
            logger.warning(f"\n⚠ {len(results['errors'])} error(s) occurred during execution")
        else:
            logger.info("\n✓ All steps completed without errors")


def run_pipeline(
    week_start: datetime = None,
    week_end: datetime = None,
    api_key: str = None,
    skip_email: bool = False,
    force_refresh: bool = False
) -> Dict[str, Any]:
    """
    Run the complete weekly pipeline.
    
    Args:
        week_start: Start of the week (default: last week Monday)
        week_end: End of the week (default: last week Sunday)
        api_key: Google API key (default: from settings)
        skip_email: If True, skip email sending
        force_refresh: If True, re-fetch reviews
        
    Returns:
        Execution results dictionary
    """
    pipeline = WeeklyPipeline(api_key=api_key, skip_email=skip_email)
    return pipeline.execute(week_start=week_start, week_end=week_end, force_refresh=force_refresh)

