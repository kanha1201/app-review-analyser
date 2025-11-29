"""Google Gemini LLM client using direct HTTP API calls (no package required)."""
import json
import logging
from typing import List, Dict, Any, Optional
from config.settings import get_settings

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False
    requests = None

logger = logging.getLogger(__name__)
settings = get_settings()


class GeminiClientHTTP:
    """Gemini client using direct HTTP API calls."""
    
    GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
    
    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize Gemini HTTP client.
        
        Args:
            api_key: Google API key (default: from settings)
            model: Model name (default: from settings)
        """
        if not HAS_REQUESTS:
            raise ImportError(
                "requests package is required. Install with: pip install requests"
            )
        
        self.api_key = api_key or settings.google_api_key
        model_name = model or settings.gemini_model
        
        if not self.api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY in .env file")
        
        # Map model names to correct API format
        # Remove "models/" prefix if present
        if model_name.startswith("models/"):
            model_name = model_name[7:]
        
        # Use gemini-2.0-flash-lite as default if old model names are used (to avoid rate limits)
        if model_name in ["gemini-1.5-pro", "gemini-pro", "gemini-1.5-flash", "gemini-2.0-flash"]:
            model_name = "gemini-2.0-flash-lite"
            logger.info(f"Model {model} not available or rate-limited, using {model_name} instead")
        
        self.model_name = model_name
        self.api_url = f"{self.GEMINI_API_BASE}/models/{model_name}:generateContent"
        logger.info(f"Using Gemini model: {model_name}")
    
    def _make_request(self, prompt: str, response_format: str = "json") -> Dict[str, Any]:
        """
        Make HTTP request to Gemini API.
        
        Args:
            prompt: Prompt text
            response_format: Expected response format ("json" or "text")
        
        Returns:
            API response dictionary
        """
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "temperature": settings.gemini_temperature,
                "topP": 0.95,
                "maxOutputTokens": settings.gemini_max_tokens,
            }
        }
        
        # Add response format if JSON is requested
        if response_format == "json":
            payload["generationConfig"]["responseMimeType"] = "application/json"
        
        params = {"key": self.api_key}
        
        # Retry logic with exponential backoff for rate limits
        max_retries = 3
        base_delay = 5  # Start with 5 seconds
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    self.api_url,
                    json=payload,
                    params=params,
                    timeout=60
                )
                
                # Handle rate limiting (429)
                if response.status_code == 429:
                    error_data = response.json().get("error", {})
                    retry_after = error_data.get("message", "")
                    
                    # Extract retry time from message if available
                    import re
                    retry_match = re.search(r"retry in ([\d.]+)s", retry_after.lower())
                    if retry_match:
                        wait_time = float(retry_match.group(1)) + 2  # Add 2 seconds buffer
                    else:
                        wait_time = base_delay * (2 ** attempt)  # Exponential backoff
                    
                    if attempt < max_retries - 1:
                        logger.warning(f"Rate limit hit (429). Waiting {wait_time:.1f}s before retry {attempt + 1}/{max_retries}")
                        import time
                        time.sleep(wait_time)
                        continue
                    else:
                        response.raise_for_status()
                
                response.raise_for_status()
                
                result = response.json()
                
                # Extract text from response
                if "candidates" in result and len(result["candidates"]) > 0:
                    candidate = result["candidates"][0]
                    if "content" in candidate and "parts" in candidate["content"]:
                        text = candidate["content"]["parts"][0].get("text", "")
                        return {"text": text, "raw": result}
                
                raise ValueError("Unexpected API response format")
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1 and hasattr(e, 'response') and e.response is not None and e.response.status_code == 429:
                    # Will retry in next iteration
                    continue
                logger.error(f"API request failed: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logger.error(f"Response: {e.response.text[:500]}")
                if attempt == max_retries - 1:
                    raise
            except Exception as e:
                logger.error(f"Error processing API response: {e}")
                if attempt == max_retries - 1:
                    raise
        
        raise Exception("Max retries exceeded")
    
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
            response = self._make_request(prompt, response_format="json")
            text = response["text"].strip()
            
            # Remove markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            # Parse JSON response
            result = json.loads(text)
            
            # Validate and clean themes
            themes = result.get("themes", [])
            if len(themes) > max_themes:
                themes = themes[:max_themes]
            
            logger.info(f"Extracted {len(themes)} themes from reviews")
            return {"themes": themes}
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON response: {e}")
            logger.error(f"Response text: {text[:500]}")
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
            response = self._make_request(prompt, response_format="json")
            text = response["text"].strip()
            
            # Remove markdown code blocks if present
            if text.startswith("```json"):
                text = text[7:]
            if text.startswith("```"):
                text = text[3:]
            if text.endswith("```"):
                text = text[:-3]
            text = text.strip()
            
            # Parse JSON response
            result = json.loads(text)
            classifications = result.get("classifications", [])
            
            logger.info(f"Classified {len(classifications)} reviews into themes")
            return classifications
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse classification JSON: {e}")
            logger.error(f"Response text: {text[:500]}")
            raise
        except Exception as e:
            logger.error(f"Error classifying reviews: {e}")
            raise

