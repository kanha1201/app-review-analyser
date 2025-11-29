"""Weekly report generator for app review insights."""
import json
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from src.database.models import Review, Theme, ReviewTheme, WeeklyReport
from src.llm.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class WeeklyReportGenerator:
    """Generates weekly one-page reports from classified reviews."""
    
    def __init__(self, session: Session, gemini_client: GeminiClient):
        self.session = session
        self.gemini_client = gemini_client
        self.chunk_size = 20  # Reviews per chunk for summarization
    
    def _call_gemini(self, prompt: str) -> str:
        """Helper method to call Gemini API with proper error handling."""
        # Use HTTP client if available, otherwise use official package
        if hasattr(self.gemini_client, 'use_http') and self.gemini_client.use_http:
            response_text = self.gemini_client.http_client._make_request(
                prompt,
                response_format="json"
            )["text"]
        else:
            response = self.gemini_client.model.generate_content(
                prompt,
                generation_config={"response_mime_type": "application/json"}
            )
            response_text = response.text
        
        # Remove markdown code blocks if present
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        return response_text
    
    def get_reviews_for_week(
        self,
        week_start: datetime,
        week_end: datetime,
        top_n_themes: int = 3
    ) -> Dict[str, List[Review]]:
        """
        Get reviews for a week, grouped by theme.
        Returns top N themes by review count.
        
        Args:
            week_start: Start of the week
            week_end: End of the week
            top_n_themes: Number of top themes to include
            
        Returns:
            Dictionary mapping theme names to lists of reviews
        """
        # Get all reviews in date range with themes
        reviews_query = (
            self.session.query(Review, Theme)
            .join(ReviewTheme, Review.id == ReviewTheme.review_id)
            .join(Theme, ReviewTheme.theme_id == Theme.id)
            .filter(
                and_(
                    Review.review_date >= week_start,
                    Review.review_date <= week_end
                )
            )
        )
        
        reviews_with_themes = reviews_query.all()
        
        # Group by theme
        theme_reviews: Dict[str, List[Review]] = {}
        theme_counts: Dict[str, int] = {}
        
        for review, theme in reviews_with_themes:
            theme_name = theme.name
            if theme_name not in theme_reviews:
                theme_reviews[theme_name] = []
            theme_reviews[theme_name].append(review)
            theme_counts[theme_name] = theme_counts.get(theme_name, 0) + 1
        
        # Sort themes by count and take top N
        sorted_themes = sorted(
            theme_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:top_n_themes]
        
        # Return only top N themes
        top_themes_dict = {
            theme_name: theme_reviews[theme_name]
            for theme_name, _ in sorted_themes
        }
        
        logger.info(
            f"Found {len(reviews_with_themes)} reviews for week "
            f"{week_start.date()} to {week_end.date()}"
        )
        logger.info(
            f"Top {top_n_themes} themes: "
            f"{', '.join([f'{name} ({len(reviews)} reviews)' for name, reviews in top_themes_dict.items()])}"
        )
        
        return top_themes_dict
    
    def summarize_theme_chunk(
        self,
        theme_name: str,
        reviews: List[Review]
    ) -> Dict[str, Any]:
        """
        Summarize a chunk of reviews for a theme.
        Extracts key points and candidate quotes.
        
        Args:
            theme_name: Name of the theme
            reviews: List of Review objects
            
        Returns:
            Dictionary with key_points and candidate_quotes
        """
        if not reviews:
            return {"key_points": [], "candidate_quotes": []}
        
        # Prepare review texts
        review_texts = []
        for review in reviews:
            text = review.cleaned_text or review.review_text
            if text and len(text.strip()) > 0:
                review_texts.append(text[:500])  # Limit length
        
        if not review_texts:
            return {"key_points": [], "candidate_quotes": []}
        
        reviews_text = "\n\n---\n\n".join([
            f"Review {i+1}: {text}"
            for i, text in enumerate(review_texts)
        ])
        
        prompt = f"""You are summarizing user reviews for a fintech app.

Theme: {theme_name}

Reviews (already cleaned, no direct PII):
{reviews_text}

Tasks:
1. Extract 3–5 key points about this theme in a neutral, factual tone.
2. Identify up to 3 short, vivid quotes that capture the sentiment.
   - Do NOT include names, usernames, emails, or IDs.
   - If a quote contains PII, rewrite it to keep meaning but remove the PII.
   - Quotes should be 1-2 lines each, impactful and representative.

3. Return JSON:
{{
  "theme": "{theme_name}",
  "key_points": ["point 1", "point 2", "..."],
  "candidate_quotes": ["quote 1", "quote 2", "quote 3"]
}}

Keep everything concise. Avoid marketing fluff. Focus on what users are actually saying."""
        
        try:
            response_text = self._call_gemini(prompt)
            result = json.loads(response_text)
            return {
                "key_points": result.get("key_points", []),
                "candidate_quotes": result.get("candidate_quotes", [])
            }
        except Exception as e:
            logger.error(f"Error summarizing theme chunk for {theme_name}: {e}")
            # Fallback: extract simple key points
            return {
                "key_points": [f"{len(reviews)} reviews mention {theme_name.lower()}"],
                "candidate_quotes": []
            }
    
    def summarize_theme(
        self,
        theme_name: str,
        reviews: List[Review]
    ) -> Dict[str, Any]:
        """
        Summarize all reviews for a theme by chunking.
        
        Args:
            theme_name: Name of the theme
            reviews: List of Review objects
            
        Returns:
            Dictionary with aggregated key_points and candidate_quotes
        """
        if not reviews:
            return {"key_points": [], "candidate_quotes": []}
        
        # Chunk reviews
        all_key_points = []
        all_quotes = []
        
        for i in range(0, len(reviews), self.chunk_size):
            chunk = reviews[i:i + self.chunk_size]
            chunk_summary = self.summarize_theme_chunk(theme_name, chunk)
            all_key_points.extend(chunk_summary.get("key_points", []))
            all_quotes.extend(chunk_summary.get("candidate_quotes", []))
        
        # Deduplicate and limit
        unique_key_points = list(dict.fromkeys(all_key_points))[:5]  # Max 5 key points
        unique_quotes = list(dict.fromkeys(all_quotes))[:5]  # Max 5 quotes
        
        return {
            "theme": theme_name,
            "key_points": unique_key_points,
            "candidate_quotes": unique_quotes
        }
    
    def generate_weekly_pulse(
        self,
        week_start: datetime,
        week_end: datetime,
        theme_summaries: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate final weekly pulse from theme summaries.
        
        Args:
            week_start: Start of the week
            week_end: End of the week
            theme_summaries: List of theme summary dictionaries
            
        Returns:
            Dictionary with weekly pulse content
        """
        # Prepare input JSON
        summaries_json = json.dumps(theme_summaries, indent=2)
        
        week_start_str = week_start.strftime("%B %d, %Y")
        week_end_str = week_end.strftime("%B %d, %Y")
        
        prompt = f"""You are creating a weekly product pulse for internal stakeholders
(Product/Growth, Support, Leadership).

Input:
- Time window: {week_start_str} to {week_end_str}
- Candidate themes with key points and quotes:
{summaries_json}

Constraints:
- Select the Top 3 themes that matter most based on frequency & impact.
- Produce:
  1) A short title for the pulse (max 10 words).
  2) A one-paragraph overview (max 60 words).
  3) A bullet list of the Top 3 themes:
     - For each, 1 sentence with sentiment + key insight.
  4) 3 short quotes (1–2 lines each), clearly marked with theme.
  5) 3 specific action ideas (bullets), each linked to a theme.

Style & limits:
- Total length: ≤250 words.
- Use clear bullets and sub-bullets where needed.
- Executive-friendly, neutral tone. Do not overpraise.
- No names, emails, IDs, or any PII.

Output in this JSON structure:
{{
  "title": "...",
  "overview": "...",
  "themes": [
    {{"name": "...", "summary": "..."}},
    ...
  ],
  "quotes": [
    {{"text": "...", "theme": "..."}},
    ...
  ],
  "actions": [
    {{"text": "...", "theme": "..."}},
    ...
  ]
}}"""
        
        try:
            response_text = self._call_gemini(prompt)
            result = json.loads(response_text)
            
            # Ensure we have exactly 3 themes, 3 quotes, 3 actions
            if len(result.get("themes", [])) > 3:
                result["themes"] = result["themes"][:3]
            if len(result.get("quotes", [])) > 3:
                result["quotes"] = result["quotes"][:3]
            if len(result.get("actions", [])) > 3:
                result["actions"] = result["actions"][:3]
            
            return result
        except Exception as e:
            logger.error(f"Error generating weekly pulse: {e}")
            raise
    
    def compress_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Compress report to ≤250 words if needed.
        
        Args:
            report: Report dictionary
            
        Returns:
            Compressed report dictionary
        """
        # Calculate word count
        text_parts = [
            report.get("title", ""),
            report.get("overview", ""),
            " ".join([t.get("summary", "") for t in report.get("themes", [])]),
            " ".join([q.get("text", "") for q in report.get("quotes", [])]),
            " ".join([a.get("text", "") for a in report.get("actions", [])])
        ]
        total_text = " ".join(text_parts)
        word_count = len(total_text.split())
        
        if word_count <= 250:
            return report
        
        logger.info(f"Report is {word_count} words, compressing to ≤250 words")
        
        report_json = json.dumps(report, indent=2)
        prompt = f"""Compress this note to at most 250 words, preserving:
- 3 themes, 3 quotes, 3 actions.
- Bullet-based, scannable structure.
- No PII.

Current note:
{report_json}

Return the compressed version in the same JSON structure."""
        
        try:
            response_text = self._call_gemini(prompt)
            compressed = json.loads(response_text)
            return compressed
        except Exception as e:
            logger.error(f"Error compressing report: {e}")
            return report  # Return original if compression fails
    
    def generate_report(
        self,
        week_start: datetime,
        week_end: datetime
    ) -> Dict[str, Any]:
        """
        Generate complete weekly report.
        
        Args:
            week_start: Start of the week
            week_end: End of the week
            
        Returns:
            Complete report dictionary
        """
        logger.info(f"Generating weekly report for {week_start.date()} to {week_end.date()}")
        
        # Step 1: Get reviews for week, top 3 themes
        theme_reviews = self.get_reviews_for_week(week_start, week_end, top_n_themes=3)
        
        if not theme_reviews:
            logger.warning("No reviews found for this week")
            return {
                "title": "No Reviews This Week",
                "overview": "No reviews were found for the specified week.",
                "themes": [],
                "quotes": [],
                "actions": []
            }
        
        # Step 2: Summarize each theme
        theme_summaries = []
        import time
        
        for theme_name, reviews in theme_reviews.items():
            logger.info(f"Summarizing theme: {theme_name} ({len(reviews)} reviews)")
            summary = self.summarize_theme(theme_name, reviews)
            theme_summaries.append(summary)
            # Rate limiting delay
            time.sleep(4.5)
        
        # Step 3: Generate weekly pulse
        logger.info("Generating final weekly pulse...")
        report = self.generate_weekly_pulse(week_start, week_end, theme_summaries)
        
        # Step 4: Compress if needed
        report = self.compress_report(report)
        
        # Add metadata
        report["week_start"] = week_start.isoformat()
        report["week_end"] = week_end.isoformat()
        report["generated_at"] = datetime.utcnow().isoformat()
        
        logger.info("Weekly report generated successfully")
        return report
    
    def save_report(self, report: Dict[str, Any]) -> WeeklyReport:
        """
        Save report to database.
        
        Args:
            report: Report dictionary
            
        Returns:
            WeeklyReport object
        """
        week_start = datetime.fromisoformat(report["week_start"])
        week_end = datetime.fromisoformat(report["week_end"])
        
        weekly_report = WeeklyReport(
            week_start_date=week_start,
            week_end_date=week_end,
            report_content=report
        )
        
        self.session.add(weekly_report)
        self.session.commit()
        self.session.refresh(weekly_report)
        
        logger.info(f"Saved weekly report: {weekly_report.id}")
        return weekly_report

