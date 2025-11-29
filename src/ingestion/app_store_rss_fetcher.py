"""Alternative App Store review fetcher using RSS feed."""
import urllib.request
import xml.etree.ElementTree as ET
from typing import List, Dict
from datetime import datetime
import logging
import re

logger = logging.getLogger(__name__)


class AppStoreRSSFetcher:
    """Fetch App Store reviews using RSS feed (fallback method)."""
    
    def __init__(self, app_id: str = "1404871703", country: str = "in"):
        self.app_id = app_id
        self.country = country
    
    def fetch_reviews(self, max_reviews: int = 500) -> List[Dict]:
        """
        Fetch reviews from App Store RSS feed.
        
        Args:
            max_reviews: Maximum number of reviews to fetch
        
        Returns:
            List of review dictionaries
        """
        reviews = []
        
        try:
            # App Store RSS feed URL
            base_url = f"https://itunes.apple.com/{self.country}/rss/customerreviews/page=1/id={self.app_id}/sortby=mostrecent/xml"
            
            logger.info(f"Fetching App Store reviews from RSS feed: {base_url}")
            
            req = urllib.request.Request(base_url)
            req.add_header('User-Agent', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                xml_data = response.read().decode('utf-8')
            
            # Parse XML
            root = ET.fromstring(xml_data)
            
            # Namespace handling
            ns = {
                'atom': 'http://www.w3.org/2005/Atom',
                'im': 'http://itunes.apple.com/rss'
            }
            
            # Find all entry elements
            entries = root.findall('.//atom:entry', ns)
            
            logger.info(f"Found {len(entries)} entries in RSS feed")
            
            for entry in entries[:max_reviews]:
                try:
                    # Extract review data
                    title_elem = entry.find('atom:title', ns)
                    content_elem = entry.find('atom:content', ns)
                    rating_elem = entry.find('.//im:rating', ns)
                    date_elem = entry.find('atom:updated', ns)
                    version_elem = entry.find('.//im:version', ns)
                    
                    if content_elem is None or (content_elem.text is None or not content_elem.text.strip()):
                        continue
                    
                    review_text = content_elem.text.strip()
                    title = title_elem.text if title_elem is not None and title_elem.text else None
                    rating = int(rating_elem.text) if rating_elem is not None and rating_elem.text else None
                    
                    # Parse date
                    date_str = date_elem.text if date_elem is not None else None
                    if date_str:
                        # ISO 8601 format: 2025-11-22T10:30:00-07:00
                        try:
                            review_date = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                            # Convert to timezone-naive datetime (UTC)
                            if review_date.tzinfo:
                                review_date = review_date.astimezone().replace(tzinfo=None)
                        except Exception as e:
                            logger.warning(f"Date parsing error: {e}, using current date")
                            review_date = datetime.now()
                    else:
                        review_date = datetime.now()
                    
                    app_version = version_elem.text if version_elem is not None and version_elem.text else None
                    
                    reviews.append({
                        'platform': 'app_store',
                        'rating': rating,
                        'title': title,
                        'review_text': review_text,
                        'review_date': review_date,
                        'app_version': app_version,
                        'raw_data': {}
                    })
                    
                except Exception as e:
                    logger.warning(f"Error parsing review entry: {e}")
                    continue
            
            logger.info(f"Fetched {len(reviews)} App Store reviews from RSS feed")
            return reviews
            
        except Exception as e:
            logger.error(f"Error fetching App Store RSS reviews: {e}")
            return []

