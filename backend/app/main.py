from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from google.oauth2.credentials import Credentials
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
import pandas as pd
import logging
from .config import settings
from .middleware import AuthenticationMiddleware, LoggingMiddleware, RequestValidationMiddleware
import asyncio
from datetime import datetime, timedelta
import json
from typing import List, Optional, Dict
from pydantic import BaseModel, EmailStr
import redis
from firebase_admin import credentials, firestore, initialize_app
from google.cloud.firestore import SERVER_TIMESTAMP
import boto3
from botocore.exceptions import ClientError
from groq import Groq
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
import uuid

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Email Automation API", version=settings.API_VERSION)

# Add middleware
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
app.add_middleware(AuthenticationMiddleware)
app.add_middleware(LoggingMiddleware)
app.add_middleware(RequestValidationMiddleware)

# Initialize services
redis_client = redis.Redis.from_url(settings.REDIS_URL)
scheduler = AsyncIOScheduler()
email_service = EmailService()

# Initialize Firebase
cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
initialize_app(cred)
db = firestore.client()

# Process email job implementation
async def process_email_job(job_id: str):
    """Process email job with throttling and tracking"""
    try:
        # Get job data
        job_ref = db.collection('jobs').document(job_id)
        job_data = job_ref.get().to_dict()
        
        if not job_data:
            logger.error(f"Job {job_id} not found")
            return
            
        # Update job status
        await job_ref.update({'status': 'processing'})
        
        # Get template
        template_ref = db.collection('templates').document(job_data['template_id'])
        template_data = template_ref.get().to_dict()
        
        if not template_data:
            logger.error(f"Template {job_data['template_id']} not found")
            await job_ref.update({'status': 'failed', 'error': 'Template not found'})
            return
            
        # Process recipients with throttling
        throttle_rate = job_data.get('throttle_rate', settings.RATE_LIMIT_EMAILS_PER_HOUR)
        delay = 3600 / throttle_rate  # seconds between emails
        
        successful = 0
        failed = 0
        
        for recipient in job_data['recipients']:
            try:
                # Generate personalized content
                content = await email_service.generate_content(
                    template_data['content'],
                    recipient['data']
                )
                
                # Send email
                message_id = await email_service.send_email(
                    recipient['email'],
                    template_data['subject'],
                    content
                )
                
                # Track delivery
                await db.collection('email_tracking').document(message_id).set({
                    'job_id': job_id,
                    'recipient': recipient['email'],
                    'status': 'sent',
                    'sent_at': SERVER_TIMESTAMP
                })
                
                successful += 1
                
                # Apply throttling
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Failed to send email to {recipient['email']}: {str(e)}")
                failed += 1
                
                # Track failure
                await db.collection('email_tracking').document().set({
                    'job_id': job_id,
                    'recipient': recipient['email'],
                    'status': 'failed',
                    'error': str(e),
                    'failed_at': SERVER_TIMESTAMP
                })
        
        # Update job status
        await job_ref.update({
            'status': 'completed',
            'completed_at': SERVER_TIMESTAMP,
            'successful': successful,
            'failed': failed
        })
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        await job_ref.update({
            'status': 'failed',
            'error': str(e),
            'failed_at': SERVER_TIMESTAMP
        })
        
        # Implement retry mechanism
        if job_data.get('retry_count', 0) < 3:
            await job_ref.update({
                'retry_count': job_data.get('retry_count', 0) + 1
            })
            # Schedule retry after 5 minutes
            scheduler.add_job(
                process_email_job,
                trigger=DateTrigger(run_date=datetime.now() + timedelta(minutes=5)),
                args=[job_id],
                id=f"{job_id}_retry_{job_data.get('retry_count', 0) + 1}"
            )

# Google Sheets Integration
class GoogleSheetsService:
    def __init__(self):
        self.scopes = ['https://www.googleapis.com/auth/spreadsheets.readonly']
        
    async def get_credentials(self, token: dict) -> Credentials:
        return Credentials.from_authorized_user_info(token, self.scopes)
        
    async def read_sheet(self, spreadsheet_id: str, range_name: str, credentials: Credentials) -> pd.DataFrame:
        try:
            service = build('sheets', 'v4', credentials=credentials)
            sheet = service.spreadsheets()
            result = sheet.values().get(
                spreadsheetId=spreadsheet_id,
                range=range_name
            ).execute()
            
            values = result.get('values', [])
            if not values:
                raise ValueError("No data found in sheet")
                
            df = pd.DataFrame(values[1:], columns=values[0])
            return df
            
        except Exception as e:
            logger.error(f"Failed to read Google Sheet: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to read Google Sheet: {str(e)}"
            )

sheets_service = GoogleSheetsService()

# OAuth2 callback implementation
@app.get("/api/auth/callback")
async def auth_callback(code: str, state: str):
    """Handle OAuth2 callback for email provider authentication"""
    try:
        # Verify state token
        account_id = redis_client.get(f"oauth_state_{state}")
        if not account_id:
            raise HTTPException(status_code=400, detail="Invalid state token")
            
        account = email_service.connected_accounts.get(account_id.decode())
        if not account:
            raise HTTPException(status_code=404, detail="Account not found")
            
        # Exchange code for tokens
        flow = account['flow']
        flow.fetch_token(code=code)
        
        # Store credentials
        credentials = flow.credentials
        account['credentials'] = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': credentials.scopes
        }
        account['status'] = 'connected'
        
        # Clean up state token
        redis_client.delete(f"oauth_state_{state}")
        
        return {"status": "success", "account_id": account_id.decode()}
        
    except Exception as e:
        logger.error(f"OAuth callback failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Google Sheets connection endpoint
@app.post("/api/connect/sheets")
async def connect_google_sheets(
    spreadsheet_id: str,
    range_name: str,
    credentials: dict
):
    """Connect and read Google Sheets data"""
    try:
        creds = await sheets_service.get_credentials(credentials)
        df = await sheets_service.read_sheet(spreadsheet_id, range_name, creds)
        
        # Convert DataFrame to list of recipients
        recipients = []
        for _, row in df.iterrows():
            data = row.to_dict()
            if 'email' not in data:
                raise HTTPException(
                    status_code=400,
                    detail="Sheet must contain 'email' column"
                )
            recipients.append({
                'email': data.pop('email'),
                'data': data
            })
            
        return {
            "columns": df.columns.tolist(),
            "preview": df.head().to_dict('records'),
            "recipients": recipients
        }
        
    except Exception as e:
        logger.error(f"Failed to connect Google Sheets: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Error recovery endpoint
@app.post("/api/jobs/{job_id}/retry")
async def retry_failed_job(job_id: str):
    """Retry a failed email job"""
    try:
        job_ref = db.collection('jobs').document(job_id)
        job_data = job_ref.get().to_dict()
        
        if not job_data:
            raise HTTPException(status_code=404, detail="Job not found")
            
        if job_data['status'] != 'failed':
            raise HTTPException(
                status_code=400,
                detail="Only failed jobs can be retried"
            )
            
        # Reset job status and retry count
        await job_ref.update({
            'status': 'pending',
            'retry_count': 0,
            'error': None
        })
        
        # Schedule immediate retry
        background_tasks = BackgroundTasks()
        background_tasks.add_task(process_email_job, job_id)
        
        return {"status": "success", "message": "Job scheduled for retry"}
        
    except Exception as e:
        logger.error(f"Failed to retry job {job_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize services on startup"""
    try:
        scheduler.start()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start application: {str(e)}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    try:
        scheduler.shutdown()
        redis_client.close()
        logger.info("Application shut down successfully")
    except Exception as e:
        logger.error(f"Error during shutdown: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)