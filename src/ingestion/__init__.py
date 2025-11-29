"""Ingestion package for fetching reviews."""
from src.ingestion.app_store_fetcher import AppStoreFetcher
from src.ingestion.google_play_fetcher import GooglePlayFetcher
from src.ingestion.review_processor import ReviewProcessor

__all__ = ["AppStoreFetcher", "GooglePlayFetcher", "ReviewProcessor"]

