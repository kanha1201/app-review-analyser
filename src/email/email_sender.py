"""Email sender for weekly reports."""
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional, Any
from datetime import datetime
from config.settings import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailSender:
    """Sends emails via SMTP."""
    
    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        from_email: Optional[str] = None
    ):
        self.smtp_host = smtp_host or getattr(settings, 'smtp_host', 'smtp.gmail.com')
        self.smtp_port = smtp_port or getattr(settings, 'smtp_port', 587)
        self.smtp_user = smtp_user or getattr(settings, 'smtp_user', None)
        self.smtp_password = smtp_password or getattr(settings, 'smtp_password', None)
        self.from_email = from_email or settings.email_from
    
    def send_email(
        self,
        to_emails: List[str],
        subject: str,
        body: str,
        cc_emails: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send email via SMTP.
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject
            body: Email body (plain text)
            cc_emails: Optional CC recipients
            
        Returns:
            Dictionary with send status and metadata
        """
        if not self.smtp_user or not self.smtp_password:
            logger.warning("SMTP credentials not configured. Email will not be sent.")
            return {
                "success": False,
                "error": "SMTP credentials not configured",
                "sent_at": None
            }
        
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.from_email
            msg['To'] = ', '.join(to_emails)
            
            if cc_emails:
                msg['Cc'] = ', '.join(cc_emails)
            
            # Add plain text body
            text_part = MIMEText(body, 'plain')
            msg.attach(text_part)
            
            # Connect to SMTP server
            logger.info(f"Connecting to SMTP server: {self.smtp_host}:{self.smtp_port}")
            server = smtplib.SMTP(self.smtp_host, self.smtp_port)
            server.starttls()
            server.login(self.smtp_user, self.smtp_password)
            
            # Send email
            all_recipients = to_emails + (cc_emails or [])
            server.send_message(msg, to_addrs=all_recipients)
            server.quit()
            
            logger.info(f"Email sent successfully to {len(all_recipients)} recipients")
            
            return {
                "success": True,
                "sent_at": datetime.utcnow().isoformat(),
                "recipients": all_recipients,
                "subject": subject
            }
            
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {
                "success": False,
                "error": str(e),
                "sent_at": None
            }
    
    def send_weekly_report_email(
        self,
        email_content: Dict[str, str],
        recipients: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Send weekly report email.
        
        Args:
            email_content: Dictionary with 'subject' and 'body' keys
            recipients: List of email addresses (default: from settings)
            
        Returns:
            Send status dictionary
        """
        recipients = recipients or settings.email_recipient_list
        
        if not recipients:
            logger.warning("No email recipients configured")
            return {
                "success": False,
                "error": "No recipients configured"
            }
        
        return self.send_email(
            to_emails=recipients,
            subject=email_content["subject"],
            body=email_content["body"]
        )

