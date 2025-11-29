"""Language detection utility using standard library only."""
import re
from typing import Optional


class LanguageDetector:
    """Detect if text is in English using heuristics."""
    
    # Common English words for validation
    COMMON_ENGLISH_WORDS = {
        'the', 'be', 'to', 'of', 'and', 'a', 'in', 'that', 'have', 'i',
        'it', 'for', 'not', 'on', 'with', 'he', 'as', 'you', 'do', 'at',
        'this', 'but', 'his', 'by', 'from', 'they', 'we', 'say', 'her', 'she',
        'or', 'an', 'will', 'my', 'one', 'all', 'would', 'there', 'their',
        'what', 'so', 'up', 'out', 'if', 'about', 'who', 'get', 'which', 'go',
        'me', 'when', 'make', 'can', 'like', 'time', 'no', 'just', 'him', 'know',
        'take', 'people', 'into', 'year', 'your', 'good', 'some', 'could', 'them',
        'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'its', 'over',
        'think', 'also', 'back', 'after', 'use', 'two', 'how', 'our', 'work', 'first',
        'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day',
        'most', 'us', 'app', 'good', 'great', 'very', 'much', 'more', 'best', 'easy',
        'love', 'like', 'nice', 'excellent', 'amazing', 'awesome', 'perfect', 'wonderful'
    }
    
    # Non-English character ranges (Unicode)
    DEVANAGARI_RANGE = re.compile(r'[\u0900-\u097F]')  # Hindi, Marathi, etc.
    CHINESE_RANGE = re.compile(r'[\u4E00-\u9FFF]')  # Chinese characters
    ARABIC_RANGE = re.compile(r'[\u0600-\u06FF]')  # Arabic
    THAI_RANGE = re.compile(r'[\u0E00-\u0E7F]')  # Thai
    
    @classmethod
    def is_english(cls, text: str, min_confidence: float = 0.5) -> bool:
        """
        Detect if text is in English.
        
        Args:
            text: Text to check
            min_confidence: Minimum confidence threshold (0.0-1.0)
        
        Returns:
            True if text appears to be English
        """
        if not text or not text.strip():
            return False
        
        text_lower = text.lower()
        words = re.findall(r'\b[a-z]+\b', text_lower)
        
        if not words:
            return False
        
        # Check for non-English scripts
        if (cls.DEVANAGARI_RANGE.search(text) or
            cls.CHINESE_RANGE.search(text) or
            cls.ARABIC_RANGE.search(text) or
            cls.THAI_RANGE.search(text)):
            return False
        
        # Check ratio of common English words
        english_word_count = sum(1 for word in words if word in cls.COMMON_ENGLISH_WORDS)
        total_words = len(words)
        
        if total_words == 0:
            return False
        
        english_ratio = english_word_count / total_words
        
        # Also check if text is mostly ASCII (English uses ASCII)
        ascii_chars = sum(1 for c in text if ord(c) < 128)
        ascii_ratio = ascii_chars / len(text) if text else 0
        
        # Combined confidence
        confidence = (english_ratio * 0.6) + (ascii_ratio * 0.4)
        
        return confidence >= min_confidence
    
    @classmethod
    def count_words(cls, text: str) -> int:
        """Count words in text."""
        if not text:
            return 0
        words = re.findall(r'\b\w+\b', text)
        return len(words)

