# App Review Insights Analyser

Automated system for analyzing App Store and Google Play Store reviews, generating weekly insights, and sending actionable reports to stakeholders.

## Overview

This system automatically:
1. **Fetches** reviews from App Store and Google Play Store (last 8-12 weeks)
2. **Classifies** reviews into themes using LLM (max 5 themes)
3. **Generates** weekly one-page reports (≤250 words) with top themes, quotes, and actions
4. **Sends** email reports to Product, Support, and Leadership teams

## Sample Outputs

### 📄 Weekly Pulse Note
View the latest weekly product pulse: [`weekly_pulse_note.md`](weekly_pulse_note.md)

This contains:
- Top 3 themes identified from user reviews
- 3 representative user quotes (anonymized)
- 3 actionable insights for product improvement

### 📧 Email Draft
View a sample email draft: [`email_draft.txt`](email_draft.txt)

This shows the formatted email that gets sent to stakeholders with the weekly pulse.

### 📊 Sample Reviews
View sample reviews used for analysis: [`sample_reviews.csv`](sample_reviews.csv)

This CSV contains:
- Sample reviews from both App Store and Google Play Store
- Reviews are cleaned and redacted (PII removed)
- Includes platform, rating, review text, and dates
- Limited to 50 sample reviews for reference

## Features

- ✅ Automated review fetching from both platforms
- ✅ LLM-based theme extraction and classification
- ✅ PII removal and text cleaning
- ✅ English-only filtering
- ✅ Word count filtering (min 4 words)
- ✅ Weekly report generation with compression
- ✅ Email draft generation and sending
- ✅ Scheduled automation support
- ✅ SQLite database for local development
- ✅ Rate limiting and retry logic for API calls

## Quick Start

### 1. Installation

```bash
# Clone the repository
cd "App Review Insights Analyser"

# Install dependencies (if not already installed)
pip install -r requirements.txt
```

### 2. Configuration

Create a `.env` file in the project root:

```bash
# Required: Google Gemini API Key
GOOGLE_API_KEY=your-gemini-api-key

# Optional: Database (defaults to SQLite)
DATABASE_URL=sqlite:///reviews.db

# Optional: Email Configuration
EMAIL_FROM=noreply@groww.in
EMAIL_RECIPIENTS=product@groww.in,support@groww.in,leadership@groww.in

# Optional: SMTP Configuration (for email sending)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Optional: Scheduling
REVIEW_FETCH_DAY=Monday
REVIEW_FETCH_TIME=09:00
REVIEW_FETCH_TIMEZONE=Asia/Kolkata
```

### 3. Run Individual Steps

**Step 1: Fetch Reviews**
```bash
python3 run_fetch.py
```

**Step 2: Classify Themes**
```bash
python3 run_classify.py
```

**Step 3: Generate Weekly Report**
```bash
python3 run_generate_report.py
```

**Step 4: Send Email (Dry Run)**
```bash
python3 run_send_email.py --dry-run
```

### 4. Run Complete Pipeline

**Manual Execution:**
```bash
# Run complete pipeline for last week
python3 run_pipeline.py

# Run for specific week
python3 run_pipeline.py 2025-11-17 2025-11-23

# Skip email sending
python3 run_pipeline.py --skip-email

# Force refresh reviews
python3 run_pipeline.py --force-refresh
```

**Scheduled Execution:**
```bash
# Start scheduler (runs weekly on configured day/time)
python3 run_scheduler.py

# Start scheduler without email
python3 run_scheduler.py --skip-email
```

## Project Structure

```
App Review Insights Analyser/
├── config/
│   └── settings.py              # Configuration management
├── src/
│   ├── database/
│   │   ├── models.py            # Database models
│   │   └── repository.py        # Database operations
│   ├── ingestion/
│   │   ├── app_store_fetcher.py # App Store scraper
│   │   ├── google_play_fetcher.py # Google Play scraper
│   │   └── review_processor.py   # Review filtering/cleaning
│   ├── llm/
│   │   ├── gemini_client.py     # Gemini LLM client
│   │   └── gemini_client_http.py # HTTP fallback client
│   ├── analysis/
│   │   └── theme_extractor.py   # Theme extraction logic
│   ├── reporting/
│   │   └── weekly_report_generator.py # Report generation
│   ├── email/
│   │   ├── email_draft_generator.py # Email draft generation
│   │   └── email_sender.py       # Email sending
│   ├── tasks/
│   │   ├── fetch_reviews.py     # Fetch task
│   │   ├── classify_themes.py   # Classification task
│   │   ├── generate_weekly_report.py # Report task
│   │   └── send_weekly_email.py  # Email task
│   ├── orchestrator/
│   │   └── weekly_pipeline.py   # Main orchestrator
│   └── scheduler/
│       └── pipeline_scheduler.py # Scheduler
├── run_fetch.py                  # Step 1 entry point
├── run_classify.py               # Step 2 entry point
├── run_generate_report.py        # Step 3 entry point
├── run_send_email.py             # Step 4 entry point
├── run_pipeline.py               # Complete pipeline
├── run_scheduler.py              # Scheduler entry point
├── requirements.txt              # Python dependencies
└── reviews.db                    # SQLite database (created automatically)
```

## Usage Examples

### Example 1: Complete Weekly Run

```bash
# Run all steps for last week
python3 run_pipeline.py
```

Output:
```
======================================================================
WEEKLY REVIEW INSIGHTS PIPELINE
======================================================================
Week: 2025-11-17 to 2025-11-23
======================================================================

[STEP 1/4] Fetching reviews from App Store and Google Play Store...
✓ Fetched 45 new reviews

[STEP 2/4] Classifying reviews into themes...
✓ Classified 1128 reviews into 5 themes

[STEP 3/4] Generating weekly report...
✓ Generated weekly report (ID: abc-123-def)

[STEP 4/4] Sending weekly email...
✓ Email sent successfully to 3 recipients

======================================================================
PIPELINE COMPLETED SUCCESSFULLY
======================================================================
```

### Example 2: Test Email Without Sending

```bash
# Generate and preview email
python3 run_send_email.py --dry-run
```

### Example 3: Schedule Weekly Automation

```bash
# Start scheduler (runs every Monday at 9 AM IST)
python3 run_scheduler.py
```

## Configuration Options

### Review Fetching
- `REVIEW_WEEKS_LOOKBACK_MIN`: Minimum weeks to look back (default: 8)
- `REVIEW_WEEKS_LOOKBACK_MAX`: Maximum weeks to look back (default: 12)
- `APP_STORE_APP_ID`: App Store app ID
- `GOOGLE_PLAY_APP_ID`: Google Play app ID

### LLM Configuration
- `GOOGLE_API_KEY`: Required - Gemini API key
- `GEMINI_MODEL`: Model to use (default: gemini-2.0-flash)
- `GEMINI_TEMPERATURE`: Temperature for generation (default: 0.3)

### Email Configuration
- `EMAIL_FROM`: Sender email address
- `EMAIL_RECIPIENTS`: Comma-separated recipient list
- `SMTP_HOST`: SMTP server hostname
- `SMTP_PORT`: SMTP server port
- `SMTP_USER`: SMTP username
- `SMTP_PASSWORD`: SMTP password (use app password for Gmail)

### Scheduling
- `REVIEW_FETCH_DAY`: Day of week (default: Monday)
- `REVIEW_FETCH_TIME`: Time in HH:MM format (default: 09:00)
- `REVIEW_FETCH_TIMEZONE`: Timezone (default: Asia/Kolkata)

## Database

The system uses SQLite by default for local development. Database file: `reviews.db`

Tables:
- `reviews`: Individual review records
- `themes`: Theme definitions
- `review_themes`: Review-to-theme mappings
- `weekly_reports`: Generated weekly reports

## API Rate Limits

The system includes built-in rate limiting for Gemini API:
- Free tier: 15 requests/minute
- Automatic delays between batches (4.5 seconds)
- Retry logic with exponential backoff for 429 errors

## Troubleshooting

### Issue: "GOOGLE_API_KEY not set"
**Solution:** Add `GOOGLE_API_KEY=your-key` to `.env` file

### Issue: "Rate limit exceeded"
**Solution:** The system automatically handles rate limits. Wait a few minutes and retry.

### Issue: "Email sending failed"
**Solution:** 
1. Check SMTP credentials in `.env`
2. For Gmail, use an App Password (not regular password)
3. Test with `--dry-run` first

### Issue: "No reviews found"
**Solution:** 
1. Check app IDs in settings
2. Verify network connectivity
3. Run `python3 run_fetch.py` to fetch reviews first

## Production Deployment

### Option 1: Cron Job
```bash
# Add to crontab (runs every Monday at 9 AM IST)
0 9 * * 1 cd /path/to/project && python3 run_pipeline.py >> /var/log/review_pipeline.log 2>&1
```

### Option 2: Systemd Service
Create `/etc/systemd/system/review-pipeline.service`:
```ini
[Unit]
Description=Weekly Review Insights Pipeline
After=network.target

[Service]
Type=oneshot
User=your-user
WorkingDirectory=/path/to/project
ExecStart=/usr/bin/python3 run_pipeline.py
Environment="GOOGLE_API_KEY=your-key"
```

### Option 3: Docker
```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python3", "run_scheduler.py"]
```

## License

Internal use only - Groww Engineering

## Support

For issues or questions, contact the Engineering team.
