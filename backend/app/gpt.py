from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import pandas as pd
import logging
from pydantic import BaseModel, EmailStr
import asyncio
from datetime import datetime, timedelta
import json
import redis
from firebase_admin import credentials, firestore, initialize_app
from google.cloud.firestore import SERVER_TIMESTAMP
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
import uuid
from logging.handlers import RotatingFileHandler
from typing import List, Dict, Optional

# ---------- Configuration and Initialization ----------
class Settings:
    FIREBASE_CREDENTIALS_PATH = r"backend\app\firebase-key.json"
    REDIS_URL = "redis://localhost:6379/0"
    RATE_LIMIT_EMAILS_PER_HOUR = 100
    API_VERSION = "1.0.0"

settings = Settings()

# Setup logging
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            RotatingFileHandler("app.log", maxBytes=10000000, backupCount=5),
            logging.StreamHandler(),
        ],
    )

setup_logging()
logger = logging.getLogger(__name__)

# FastAPI app
app = FastAPI(title="Email Automation API", version=settings.API_VERSION)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://your-frontend-domain.com"],  # Restrict CORS origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Firebase
cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
initialize_app(cred)
db = firestore.client()

# Initialize Redis
redis_client = redis.Redis.from_url(settings.REDIS_URL)

# Scheduler for background tasks
scheduler = AsyncIOScheduler()

# ---------- Utility Classes ----------
class EmailService:
    def __init__(self):
        pass

    async def generate_content(self, template: str, data: dict) -> str:
        """Generate email content by populating a template with data."""
        try:
            content = template.format(**data)
            return content
        except KeyError as e:
            raise ValueError(f"Missing data for template placeholder: {e}")

    async def send_email(self, recipient: str, subject: str, content: str) -> str:
        """Send an email and return a message ID."""
        try:
            smtp_server = "smtp.example.com"
            smtp_port = 587
            smtp_user = "your-email@example.com"
            smtp_password = "your-password"

            # Set up the email
            msg = MIMEMultipart()
            msg["From"] = smtp_user
            msg["To"] = recipient
            msg["Subject"] = subject
            msg.attach(MIMEText(content, "html"))

            # Connect to SMTP server
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, recipient, msg.as_string())

            logger.info(f"Email sent to {recipient} with subject: {subject}")
            return str(uuid.uuid4())  # Simulated message ID for tracking

        except Exception as e:
            logger.error(f"Failed to send email to {recipient}: {e}")
            raise Exception(f"Failed to send email: {e}")

email_service = EmailService()

# Google Sheets Service
class GoogleSheetsService:
    def __init__(self):
        self.scopes = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

    async def get_credentials(self, token: dict) -> Credentials:
        """Get OAuth credentials."""
        return Credentials.from_authorized_user_info(token, self.scopes)

    async def read_sheet(self, spreadsheet_id: str, range_name: str, credentials: Credentials) -> pd.DataFrame:
        """Read data from Google Sheets."""
        try:
            service = build("sheets", "v4", credentials=credentials)
            result = service.spreadsheets().values().get(
                spreadsheetId=spreadsheet_id, range=range_name
            ).execute()
            values = result.get("values", [])

            if not values:
                raise ValueError("No data found in the sheet")

            return pd.DataFrame(values[1:], columns=values[0])
        except Exception as e:
            logger.error(f"Failed to read Google Sheets: {e}")
            raise HTTPException(status_code=500, detail=str(e))

sheets_service = GoogleSheetsService()

# ---------- Email Job Processing ----------
async def process_email_job(job_id: str):
    """Process an email job."""
    try:
        job_ref = db.collection("jobs").document(job_id)
        job_data = job_ref.get().to_dict()
        if not job_data:
            logger.error(f"Job {job_id} not found")
            return

        await job_ref.update({"status": "processing"})
        template_data = db.collection("templates").document(job_data["template_id"]).get().to_dict()

        if not template_data:
            await job_ref.update({"status": "failed", "error": "Template not found"})
            return

        throttle_rate = settings.RATE_LIMIT_EMAILS_PER_HOUR
        delay = 3600 / throttle_rate

        successful, failed = 0, 0

        for recipient in job_data["recipients"]:
            try:
                content = await email_service.generate_content(
                    template_data["content"], recipient["data"]
                )
                message_id = await email_service.send_email(
                    recipient["email"], template_data["subject"], content
                )
                db.collection("email_tracking").document(message_id).set({
                    "job_id": job_id,
                    "recipient": recipient["email"],
                    "status": "sent",
                    "sent_at": SERVER_TIMESTAMP,
                })
                successful += 1
                await asyncio.sleep(delay)
            except Exception as e:
                logger.error(f"Failed to send email to {recipient['email']}: {e}")
                failed += 1

        await job_ref.update({
            "status": "completed",
            "successful": successful,
            "failed": failed,
        })

    except Exception as e:
        logger.error(f"Failed to process job {job_id}: {e}")
        await job_ref.update({"status": "failed", "error": str(e)})

# ---------- API Endpoints ----------
@app.post("/api/jobs/{job_id}/retry")
async def retry_failed_job(job_id: str):
    """Retry a failed job."""
    try:
        job_ref = db.collection("jobs").document(job_id)
        job_data = job_ref.get().to_dict()

        if not job_data or job_data["status"] != "failed":
            raise HTTPException(status_code=400, detail="Invalid job")

        await job_ref.update({"status": "pending"})
        BackgroundTasks().add_task(process_email_job, job_id)
        return {"message": "Retry scheduled"}
    except Exception as e:
        logger.error(f"Failed to retry job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ---------- Startup and Shutdown ----------
@app.on_event("startup")
async def startup_event():
    scheduler.start()
    logger.info("Scheduler started")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    logger.info("Scheduler stopped")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
