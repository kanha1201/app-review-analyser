"""Configuration management for the application."""
from pydantic_settings import BaseSettings
from typing import List
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Database
    database_url: str = "postgresql://user:password@localhost:5432/reviews_db"
    
    # App Store Configuration
    app_store_app_id: str = "1404871703"
    app_store_country: str = "in"
    
    # Google Play Store Configuration
    google_play_app_id: str = "com.nextbillion.groww"
    google_play_country: str = "in"
    
    # Scheduling Configuration
    review_fetch_interval_hours: int = 168  # 1 week in hours
    review_fetch_day: str = "Monday"
    review_fetch_time: str = "09:00"
    review_fetch_timezone: str = "Asia/Kolkata"
    review_weeks_lookback_min: int = 8
    review_weeks_lookback_max: int = 12
    
    # LLM - Gemini Configuration
    google_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash-lite"  # Using lite model to avoid rate limits
    gemini_temperature: float = 0.3
    gemini_max_tokens: int = 4096
    
    # Email Configuration
    sendgrid_api_key: str = ""
    email_from: str = "noreply@groww.in"
    email_recipients: str = "product@groww.in,support@groww.in,leadership@groww.in"
    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 587
    smtp_user: str = ""  # Gmail address or SMTP username
    smtp_password: str = ""  # Gmail app password or SMTP password
    
    # Logging
    log_level: str = "INFO"
    
    @property
    def email_recipient_list(self) -> List[str]:
        """Parse email recipients string into list."""
        return [email.strip() for email in self.email_recipients.split(",") if email.strip()]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()

