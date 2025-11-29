"""Database repository for review operations."""
from sqlalchemy.orm import Session
from sqlalchemy import select, and_
from typing import List, Optional, Dict
from datetime import datetime
from src.database.models import Review, Theme, ReviewTheme, WeeklyReport
from config.settings import get_settings
import uuid

settings = get_settings()


class ReviewRepository:
    """Repository for review database operations."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def create_review(self, review_data: Dict) -> Review:
        """Create a new review record."""
        review = Review(**review_data)
        self.session.add(review)
        return review
    
    def get_review_by_platform_and_date(
        self, 
        platform: str, 
        review_date: datetime,
        review_text_hash: Optional[str] = None
    ) -> Optional[Review]:
        """Check if review already exists (deduplication)."""
        query = select(Review).where(
            and_(
                Review.platform == platform,
                Review.review_date == review_date
            )
        )
        if review_text_hash:
            # Could add hash field for better deduplication
            pass
        result = self.session.execute(query)
        return result.scalar_one_or_none()
    
    def get_reviews_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime,
        platform: Optional[str] = None
    ) -> List[Review]:
        """Get reviews within a date range."""
        query = select(Review).where(
            and_(
                Review.review_date >= start_date,
                Review.review_date <= end_date
            )
        )
        if platform:
            query = query.where(Review.platform == platform)
        
        query = query.order_by(Review.review_date.desc())
        result = self.session.execute(query)
        return list(result.scalars().all())
    
    def get_unprocessed_reviews(self) -> List[Review]:
        """Get reviews that haven't been processed for themes."""
        query = select(Review).where(Review.processed_at.is_(None))
        result = self.session.execute(query)
        return list(result.scalars().all())
    
    def mark_review_processed(self, review_id: uuid.UUID):
        """Mark a review as processed."""
        review = self.session.get(Review, review_id)
        if review:
            review.processed_at = datetime.utcnow()
    
    def commit(self):
        """Commit the current transaction."""
        self.session.commit()
    
    def bulk_create_reviews(self, reviews_data: List[Dict]) -> int:
        """Bulk create reviews with deduplication."""
        import json
        from datetime import datetime
        
        created_count = 0
        for review_data in reviews_data:
            # Check if review already exists
            existing = self.get_review_by_platform_and_date(
                platform=review_data["platform"],
                review_date=review_data["review_date"]
            )
            if not existing:
                # Convert datetime objects in raw_data to strings for JSON serialization
                if "raw_data" in review_data and review_data["raw_data"]:
                    raw_data = review_data["raw_data"].copy()
                    for key, value in raw_data.items():
                        if isinstance(value, datetime):
                            raw_data[key] = value.isoformat()
                    review_data["raw_data"] = raw_data
                
                self.create_review(review_data)
                created_count += 1
        
        if created_count > 0:
            self.commit()
        return created_count

