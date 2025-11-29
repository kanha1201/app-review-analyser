"""PII removal and text cleaning utilities."""
import re
from typing import Optional

# Try to import optional dependencies
try:
    import emoji
    HAS_EMOJI = True
except ImportError:
    HAS_EMOJI = False

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False


class PIIRemover:
    """Remove PII and clean text from reviews."""
    
    # Regex patterns for PII detection
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    PHONE_PATTERN = re.compile(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
    INDIAN_PHONE_PATTERN = re.compile(r'(\+91[-.\s]?)?[6-9]\d{9}')
    URL_PATTERN = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
    
    @classmethod
    def remove_emails(cls, text: str) -> str:
        """Remove email addresses from text."""
        return cls.EMAIL_PATTERN.sub('[EMAIL_REMOVED]', text)
    
    @classmethod
    def remove_phones(cls, text: str) -> str:
        """Remove phone numbers from text."""
        text = cls.PHONE_PATTERN.sub('[PHONE_REMOVED]', text)
        text = cls.INDIAN_PHONE_PATTERN.sub('[PHONE_REMOVED]', text)
        return text
    
    @classmethod
    def remove_urls(cls, text: str) -> str:
        """Remove URLs from text."""
        return cls.URL_PATTERN.sub('[URL_REMOVED]', text)
    
    @classmethod
    def remove_emojis(cls, text: str) -> str:
        """Remove emojis from text."""
        if HAS_EMOJI:
            return emoji.replace_emoji(text, replace='')
        else:
            # Basic emoji removal using regex (Unicode ranges)
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"  # emoticons
                "\U0001F300-\U0001F5FF"  # symbols & pictographs
                "\U0001F680-\U0001F6FF"  # transport & map symbols
                "\U0001F1E0-\U0001F1FF"  # flags
                "\U00002702-\U000027B0"
                "\U000024C2-\U0001F251"
                "]+", flags=re.UNICODE
            )
            return emoji_pattern.sub('', text)
    
    @classmethod
    def strip_html(cls, text: str) -> str:
        """Remove HTML tags from text."""
        if not text:
            return text
        if HAS_BS4:
            soup = BeautifulSoup(text, 'html.parser')
            return soup.get_text(separator=' ', strip=True)
        else:
            # Basic HTML tag removal using regex
            html_pattern = re.compile('<.*?>')
            return html_pattern.sub('', text)
    
    @classmethod
    def normalize_whitespace(cls, text: str) -> str:
        """Normalize whitespace in text."""
        # Replace multiple spaces with single space
        text = re.sub(r'\s+', ' ', text)
        # Replace multiple newlines with single newline
        text = re.sub(r'\n+', '\n', text)
        return text.strip()
    
    @classmethod
    def normalize_quotes(cls, text: str) -> str:
        """Normalize different quote types to standard quotes."""
        # Replace curly quotes with straight quotes
        text = text.replace('"', '"').replace('"', '"')
        text = text.replace(''', "'").replace(''', "'")
        return text
    
    @classmethod
    def clean_text(cls, text: str, remove_emojis_flag: bool = True) -> str:
        """
        Complete text cleaning pipeline.
        
        Args:
            text: Raw text to clean
            remove_emojis_flag: Whether to remove emojis (default: True)
        
        Returns:
            Cleaned text with PII removed
        """
        if not text:
            return ""
        
        # Step 1: Remove HTML tags
        text = cls.strip_html(text)
        
        # Step 2: Remove PII
        text = cls.remove_emails(text)
        text = cls.remove_phones(text)
        text = cls.remove_urls(text)
        
        # Step 3: Remove emojis (optional)
        if remove_emojis_flag:
            text = cls.remove_emojis(text)
        
        # Step 4: Normalize quotes
        text = cls.normalize_quotes(text)
        
        # Step 5: Normalize whitespace
        text = cls.normalize_whitespace(text)
        
        return text
    
    @classmethod
    def contains_pii(cls, text: str) -> bool:
        """Check if text contains potential PII."""
        if cls.EMAIL_PATTERN.search(text):
            return True
        if cls.PHONE_PATTERN.search(text) or cls.INDIAN_PHONE_PATTERN.search(text):
            return True
        return False

