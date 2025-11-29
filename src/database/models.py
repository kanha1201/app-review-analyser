"""Database models for reviews and related entities."""
from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey, JSON, Float, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

Base = declarative_base()


class Review(Base):
    """Review model storing individual app reviews."""
    __tablename__ = "reviews"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    platform = Column(String(20), nullable=False)  # 'app_store' or 'google_play'
    rating = Column(Integer, nullable=True)  # 1-5
    title = Column(Text, nullable=True)  # Review title/heading
    review_text = Column(Text, nullable=False)  # Review body text
    review_date = Column(DateTime, nullable=False)  # When review was posted
    app_version = Column(String(50), nullable=True)  # App version if available
    raw_data = Column(JSON, nullable=True)  # Original raw data for audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    processed_at = Column(DateTime, nullable=True)  # When review was processed for themes
    cleaned_text = Column(Text, nullable=True)  # Text after PII removal and cleaning
    
    # Relationships
    review_themes = relationship("ReviewTheme", back_populates="review", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index("idx_reviews_platform_date", "platform", "review_date"),
        Index("idx_reviews_date", "review_date"),
        Index("idx_reviews_processed", "processed_at"),
    )
    
    def __repr__(self):
        return f"<Review(id={self.id}, platform={self.platform}, rating={self.rating}, date={self.review_date})>"


class Theme(Base):
    """Theme model for categorizing reviews."""
    __tablename__ = "themes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    review_themes = relationship("ReviewTheme", back_populates="theme", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Theme(id={self.id}, name={self.name})>"


class ReviewTheme(Base):
    """Many-to-many relationship between reviews and themes."""
    __tablename__ = "review_themes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    review_id = Column(UUID(as_uuid=True), ForeignKey("reviews.id"), nullable=False)
    theme_id = Column(UUID(as_uuid=True), ForeignKey("themes.id"), nullable=False)
    confidence_score = Column(Float, nullable=True)  # LLM confidence in theme assignment
    
    # Relationships
    review = relationship("Review", back_populates="review_themes")
    theme = relationship("Theme", back_populates="review_themes")
    
    # Indexes
    __table_args__ = (
        Index("idx_review_themes_review", "review_id"),
        Index("idx_review_themes_theme", "theme_id"),
    )
    
    def __repr__(self):
        return f"<ReviewTheme(review_id={self.review_id}, theme_id={self.theme_id})>"


class WeeklyReport(Base):
    """Weekly report model storing generated reports."""
    __tablename__ = "weekly_reports"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    week_start_date = Column(DateTime, nullable=False)
    week_end_date = Column(DateTime, nullable=False)
    report_content = Column(JSON, nullable=False)  # Structured report data
    email_sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Indexes
    __table_args__ = (
        Index("idx_weekly_reports_dates", "week_start_date", "week_end_date"),
    )
    
    def __repr__(self):
        return f"<WeeklyReport(id={self.id}, week_start={self.week_start_date}, week_end={self.week_end_date})>"

