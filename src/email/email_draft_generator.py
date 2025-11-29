"""Email draft generator for weekly reports."""
import json
import logging
from typing import Dict, Any
from datetime import datetime
from src.llm.gemini_client import GeminiClient

logger = logging.getLogger(__name__)


class EmailDraftGenerator:
    """Generates email drafts from weekly pulse reports."""
    
    def __init__(self, gemini_client: GeminiClient, product_name: str = "review-scraper"):
        self.gemini_client = gemini_client
        self.product_name = product_name
    
    def _call_gemini(self, prompt: str) -> str:
        """Helper method to call Gemini API."""
        # Use HTTP client if available, otherwise use official package
        if hasattr(self.gemini_client, 'use_http') and self.gemini_client.use_http:
            response_text = self.gemini_client.http_client._make_request(
                prompt,
                response_format="text"
            )["text"]
        else:
            response = self.gemini_client.model.generate_content(prompt)
            response_text = response.text
        
        # Remove markdown code blocks if present
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()
        
        return response_text
    
    def generate_subject_line(
        self,
        week_start: datetime,
        week_end: datetime
    ) -> str:
        """
        Generate email subject line.
        
        Args:
            week_start: Start of the week
            week_end: End of the week
            
        Returns:
            Subject line string
        """
        week_start_str = week_start.strftime("%b %d")
        week_end_str = week_end.strftime("%b %d, %Y")
        subject = f"Weekly Product Pulse – {self.product_name} ({week_start_str}–{week_end_str})"
        return subject
    
    def generate_email_body(
        self,
        weekly_pulse: Dict[str, Any],
        week_start: datetime,
        week_end: datetime
    ) -> str:
        """
        Generate email body from weekly pulse.
        
        Args:
            weekly_pulse: Weekly pulse report dictionary
            week_start: Start of the week
            week_end: End of the week
            
        Returns:
            Email body text
        """
        week_start_str = week_start.strftime("%B %d")
        week_end_str = week_end.strftime("%B %d, %Y")
        
        # Prepare weekly pulse JSON for prompt
        pulse_json = json.dumps(weekly_pulse, indent=2)
        
        prompt = f"""You are drafting an internal weekly email sharing the latest product pulse.

Audience:
- Product & Growth: want to see what to fix or double down on.
- Support: wants to know what to acknowledge and celebrate.
- Leadership: wants a quick pulse, key risks, and wins.

Input (weekly note JSON):
{pulse_json}

Tasks:
- Write an email body only (no subject line).
- Structure:
  1) 2–3 line intro explaining the time window and the product/program ({self.product_name}).
  2) Embed the weekly pulse note in a clean, scannable format:
     - Title
     - Overview
     - Bulleted Top 3 themes
     - Bulleted 3 quotes
     - Bulleted 3 action ideas
  3) End with a short closing line and invite replies.

Constraints:
- Professional, neutral tone with a hint of warmth.
- No names, emails, or IDs. If present in quotes, anonymize generically
  (e.g., "a learner", "one participant", "a user").
- Keep the whole email under 350 words.
- Use plain text formatting (no HTML, no markdown).
- Use simple bullets (- or *) for lists.

Output plain text only (no HTML, no markdown code blocks)."""
        
        try:
            email_body = self._call_gemini(prompt)
            logger.info("Email body generated successfully")
            return email_body.strip()
        except Exception as e:
            logger.error(f"Error generating email body: {e}")
            # Fallback to template-based email
            return self._generate_fallback_email(weekly_pulse, week_start_str, week_end_str)
    
    def _generate_fallback_email(
        self,
        weekly_pulse: Dict[str, Any],
        week_start_str: str,
        week_end_str: str
    ) -> str:
        """Generate a simple template-based email as fallback."""
        title = weekly_pulse.get("title", "Weekly Product Pulse")
        overview = weekly_pulse.get("overview", "")
        themes = weekly_pulse.get("themes", [])
        quotes = weekly_pulse.get("quotes", [])
        actions = weekly_pulse.get("actions", [])
        
        email = f"""Hi Team,

Here's the weekly product pulse for {self.product_name} covering {week_start_str} to {week_end_str}.

{title}

{overview}

Top Themes:
"""
        for theme in themes:
            email += f"- {theme.get('name', '')}: {theme.get('summary', '')}\n"
        
        email += "\nUser Quotes:\n"
        for quote in quotes:
            theme_name = quote.get('theme', 'Unknown')
            quote_text = quote.get('text', '')
            email += f"- [{theme_name}] \"{quote_text}\"\n"
        
        email += "\nAction Ideas:\n"
        for action in actions:
            theme_name = action.get('theme', 'Unknown')
            action_text = action.get('text', '')
            email += f"- [{theme_name}] {action_text}\n"
        
        email += "\nPlease share any questions or feedback.\n\nBest regards,\nProduct Insights Team"
        
        return email
    
    def scrub_pii(self, text: str) -> str:
        """
        Remove PII patterns from email text.
        
        Args:
            text: Email text to scrub
            
        Returns:
            Scrubbed text
        """
        import re
        
        # Email patterns
        text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL_REMOVED]', text)
        
        # Phone patterns (including Indian)
        text = re.sub(r'(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', '[PHONE_REMOVED]', text)
        text = re.sub(r'(\+91[-.\s]?)?[6-9]\d{9}', '[PHONE_REMOVED]', text)
        
        # URLs
        text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '[URL_REMOVED]', text)
        
        return text
    
    def generate_email(
        self,
        weekly_pulse: Dict[str, Any],
        week_start: datetime,
        week_end: datetime
    ) -> Dict[str, str]:
        """
        Generate complete email (subject + body).
        
        Args:
            weekly_pulse: Weekly pulse report dictionary
            week_start: Start of the week
            week_end: End of the week
            
        Returns:
            Dictionary with 'subject' and 'body' keys
        """
        subject = self.generate_subject_line(week_start, week_end)
        body = self.generate_email_body(weekly_pulse, week_start, week_end)
        
        # Final PII scrub
        body = self.scrub_pii(body)
        
        # Word count check
        word_count = len(body.split())
        if word_count > 350:
            logger.warning(f"Email body is {word_count} words, compressing...")
            body = self._compress_email(body)
        
        return {
            "subject": subject,
            "body": body
        }
    
    def _compress_email(self, body: str) -> str:
        """Compress email body if it exceeds word limit."""
        prompt = f"""Compress this email body to under 350 words while preserving:
- All key information (themes, quotes, actions)
- Professional tone
- Structure and readability

Email body:
{body}

Return the compressed version as plain text."""
        
        try:
            compressed = self._call_gemini(prompt)
            return compressed.strip()
        except Exception as e:
            logger.error(f"Error compressing email: {e}")
            # Simple truncation as last resort
            words = body.split()
            if len(words) > 350:
                truncated = " ".join(words[:350])
                return truncated + "...\n\n[Email truncated due to length]"
            return body

