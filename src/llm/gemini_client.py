"""Google Gemini LLM client for theme extraction and classification."""
# Try to use official package first, fallback to HTTP client
try:
    import google.generativeai as genai
    HAS_GEMINI_PACKAGE = True
except ImportError:
    HAS_GEMINI_PACKAGE = False
    genai = None

from typing import List, Dict, Any, Optional
import json
import logging
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Import HTTP fallback
try:
    from src.llm.gemini_client_http import GeminiClientHTTP
    HAS_HTTP_CLIENT = True
except ImportError:
    HAS_HTTP_CLIENT = False


class GeminiClient:
    """Client for interacting with Google Gemini API."""
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Gemini client.
        
        Uses official package if available, otherwise falls back to HTTP client.
        
        Args:
            api_key: Google API key (default: from settings)
            model: Model name (default: from settings)
        """
        self.api_key = api_key or settings.google_api_key
        self.model_name = model or settings.gemini_model
        
        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY in .env file")
        
        # Try to use official package, fallback to HTTP client
        if HAS_GEMINI_PACKAGE:
            logger.info("Using google-generativeai package")
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                generation_config={
                    "temperature": settings.gemini_temperature,
                    "top_p": 0.95,
                    "max_output_tokens": settings.gemini_max_tokens,
                }
            )
            self.use_http = False
        elif HAS_HTTP_CLIENT:
            logger.info("Using HTTP client (google-generativeai package not available)")
            self.http_client = GeminiClientHTTP(api_key=self.api_key, model=self.model_name)
            self.use_http = True
        else:
            raise ImportError(
                "Neither google-generativeai package nor requests package is available. "
                "Please install one of: pip install google-generativeai OR pip install requests"
            )
    
    def extract_themes(self, reviews: List[Dict[str, Any]], max_themes: int = 5) -> Dict[str, Any]:
        """
        Extract top themes from reviews using LLM.
        
        Args:
            reviews: List of review dictionaries with 'review_text' and 'rating'
            max_themes: Maximum number of themes to extract (default: 5)
        
        Returns:
            Dictionary with themes and their descriptions
        """
        # Prepare review samples for analysis
        review_samples = []
        for i, review in enumerate(reviews[:100]):  # Use first 100 reviews for theme extraction
            text = review.get('cleaned_text') or review.get('review_text', '')
            rating = review.get('rating', 'N/A')
            review_samples.append(f"Review {i+1} (Rating: {rating}/5): {text[:200]}")
        
        reviews_text = "\n\n".join(review_samples)
        
        prompt = f"""You are analyzing app reviews for a fintech investment app. Analyze the following reviews and identify the top {max_themes} themes that users are discussing.

Reviews:
{reviews_text}

Instructions:
1. Identify exactly {max_themes} themes based on what users are actually talking about
2. Themes should be specific to the app's features and user concerns (e.g., "Order Execution Issues", "Login Problems", "Portfolio Tracking", etc.)
3. Do NOT use generic themes like "App Experience" or "Easy to Use" unless they are truly the main themes
4. For each theme, provide:
   - Theme name (2-4 words, specific and actionable)
   - Brief description (1-2 sentences explaining what this theme covers)
   - Example keywords or phrases users mention

Return ONLY valid JSON in this exact format:
{{
  "themes": [
    {{
      "name": "Theme Name",
      "description": "Brief description of what this theme covers",
      "keywords": ["keyword1", "keyword2"]
    }},
    ...
  ]
}}

Do not include any markdown formatting, only JSON."""

        try:
            if self.use_http:
                # Use HTTP client
                return self.http_client.extract_themes(reviews, max_themes)
            
            # Use official package
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                }
            )
            
            # Parse JSON response
            result = json.loads(response.text)
            
            # Validate and clean themes
            themes = result.get("themes", [])
            if len(themes) > max_themes:
                themes = themes[:max_themes]
            
            logger.info(f"Extracted {len(themes)} themes from reviews")
            return {"themes": themes}
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            if not self.use_http and hasattr(self, 'response'):
                logger.error(f"Response: {response.text[:500]}")
            raise
        except Exception as e:
            logger.error(f"Error extracting themes: {e}")
            raise
    
    def classify_reviews(
        self,
        reviews: List[Dict[str, Any]],
        themes: List[Dict[str, str]]
    ) -> List[Dict[str, Any]]:
        """
        Classify reviews into themes.
        
        Args:
            reviews: List of review dictionaries with 'id', 'review_text', 'cleaned_text'
            themes: List of theme dictionaries with 'name' and 'description'
        
        Returns:
            List of classification results with review_id, theme_name, reason
        """
        if not reviews or not themes:
            return []
        
        # Prepare themes list for prompt
        themes_list = []
        for i, theme in enumerate(themes, 1):
            themes_list.append(f"{i}. {theme['name']} - {theme.get('description', '')}")
        
        themes_text = "\n".join(themes_list)
        
        # Prepare reviews batch
        reviews_batch = []
        for review in reviews:
            review_id = str(review.get('id', ''))
            text = review.get('cleaned_text') or review.get('review_text', '')
            rating = review.get('rating', 'N/A')
            reviews_batch.append(f"Review ID: {review_id}\nRating: {rating}/5\nText: {text}")
        
        reviews_text = "\n\n---\n\n".join(reviews_batch)
        
        prompt = f"""You are tagging user reviews into exactly one of the following themes.

Allowed themes:
{themes_text}

For each review below, assign it to exactly ONE theme that best matches the main concern or topic discussed.

Reviews:
{reviews_text}

Return ONLY valid JSON in this exact format:
{{
  "classifications": [
    {{
      "review_id": "review_id_here",
      "theme_name": "Exact theme name from the list above",
      "reason": "One sentence explaining why this theme was chosen (no PII)"
    }},
    ...
  ]
}}

Important:
- Each review must be assigned to exactly ONE theme
- Theme name must match exactly one from the allowed themes list
- If a review doesn't clearly fit any theme, choose the closest match
- Do not include any markdown formatting, only JSON."""

        try:
            if self.use_http:
                # Use HTTP client
                return self.http_client.classify_reviews(reviews, themes)
            
            # Use official package
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                }
            )
            
            # Parse JSON response
            result = json.loads(response.text)
            classifications = result.get("classifications", [])
            
            logger.info(f"Classified {len(classifications)} reviews into themes")
            return classifications
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse classification JSON: {e}")
            logger.error(f"Response: {response.text[:500]}")
            raise
        except Exception as e:
            logger.error(f"Error classifying reviews: {e}")
            raise

