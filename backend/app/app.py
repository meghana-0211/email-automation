from fastapi import FastAPI, BackgroundTasks, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import logging
from logging.handlers import RotatingFileHandler
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import redis
from firebase_admin import credentials, firestore, initialize_app
from google.cloud.firestore import SERVER_TIMESTAMP
import pandas as pd
import json
from typing import List, Optional
from datetime import datetime
from settings import Settings
from models import EmailTemplate, EmailJob, EmailStatus, DataSource, Recipient
import asyncio
import uvicorn

import os
import sys

# Add the parent directory to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.insert(0, parent_dir)
sys.path.insert(0, current_dir)


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('app.log', maxBytes=10000000, backupCount=5),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


# Initialize FastAPI app
app = FastAPI(title="Email Automation API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Initialize services
redis_client = redis.Redis.from_url(Settings.REDIS_URL)
scheduler = AsyncIOScheduler()
cred = credentials.Certificate(Settings.FIREBASE_CREDENTIALS_PATH)
initialize_app(cred)
db = firestore.client()

from services.email_service import EmailService
from services.sheet_services import SheetService
from services.analytics_service import AnalyticsService

# Initialize services
email_service = EmailService()
sheet_service = SheetService()
analytics_service = AnalyticsService(db)


async def process_email_job(job_id: str):
    try:
        job_ref = db.collection('jobs').document(job_id)
        job_data = job_ref.get().to_dict()
        
        if not job_data:
            logger.error(f"Job {job_id} not found")
            return
        
        job_ref.update({'status': 'processing'})
        template_ref = db.collection('templates').document(job_data['template_id'])
        template_data = template_ref.get().to_dict()
        
        if not template_data:
            logger.error(f"Template {job_data['template_id']} not found")
            job_ref.update({'status': 'failed', 'error': 'Template not found'})
            return
        
        throttle_rate = job_data.get('throttle_rate', Settings.RATE_LIMIT_EMAILS_PER_HOUR)
        delay = 3600 / throttle_rate
        
        successful = 0
        failed = 0
        
        for recipient in job_data['recipients']:
            try:
                content = await email_service.generate_content(
                    template_data['content'],
                    recipient['data']
                )
                
                message_id = await email_service.send_email(
                    recipient['email'],
                    template_data['subject'],
                    content
                )
                
                db.collection('email_tracking').document(message_id).set({
                    'job_id': job_id,
                    'recipient': recipient['email'],
                    'status': 'sent',
                    'sent_at': SERVER_TIMESTAMP
                })
                
                successful += 1
                await asyncio.sleep(delay)
                
            except Exception as e:
                logger.error(f"Failed to send email to {recipient['email']}: {str(e)}")
                failed += 1
                
                db.collection('email_tracking').document().set({
                    'job_id': job_id,
                    'recipient': recipient['email'],
                    'status': 'failed',
                    'error': str(e),
                    'failed_at': SERVER_TIMESTAMP
                })
        
        job_ref.update({
            'status': 'completed',
            'completed_at': SERVER_TIMESTAMP,
            'successful': successful,
            'failed': failed
        })
        
    except Exception as e:
        logger.error(f"Job {job_id} failed: {str(e)}")
        job_ref.update({
            'status': 'failed',
            'error': str(e),
            'failed_at': SERVER_TIMESTAMP
        })

# API Routes
@app.post("/upload/csv")
async def upload_csv(file: UploadFile = File(...)):
    if not file.filename.endswith('.csv'):
        raise HTTPException(400, "File must be a CSV")
    
    df = pd.read_csv(file.file)
    return {
        "columns": df.columns.tolist(),
        "preview": df.head().to_dict('records')
    }
# Continuing from the previous imports and initialization...


@app.post("/templates")
async def create_template(template: EmailTemplate):
    try:
        template_dict = template.dict()
        template_dict['created_at'] = SERVER_TIMESTAMP
        template_dict['updated_at'] = SERVER_TIMESTAMP
        doc_ref = db.collection('templates').document()
        doc_ref.set(template_dict)
        return {"id": doc_ref.id, **template_dict}
    except Exception as e:
        logger.error(f"Failed to create template: {str(e)}")
        raise HTTPException(500, str(e))

@app.get("/templates")
async def list_templates():
    try:
        templates = []
        for doc in db.collection('templates').stream():
            templates.append({"id": doc.id, **doc.to_dict()})
        return templates
    except Exception as e:
        logger.error(f"Failed to list templates: {str(e)}")
        raise HTTPException(500, str(e))



@app.get("/templates/{template_id}")
async def get_template(template_id: str):
    try:
        doc = db.collection('templates').document(template_id).get()
        if not doc.exists:
            raise HTTPException(404, "Template not found")
        return {"id": doc.id, **doc.to_dict()}
    except Exception as e:
        logger.error(f"Failed to get template: {str(e)}")
        raise HTTPException(500, str(e))

@app.post("/jobs")
async def create_job(job: EmailJob, background_tasks: BackgroundTasks):
    try:
        # Validate template exists
        template_ref = db.collection('templates').document(job.template_id)
        if not template_ref.get().exists:
            raise HTTPException(404, "Template not found")
        
        # Check rate limits
        current_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
        rate_key = f"email_rate:{current_hour.timestamp()}"
        current_rate = int(redis_client.get(rate_key) or 0)
        
        if current_rate + len(job.recipients) > Settings.RATE_LIMIT_EMAILS_PER_HOUR:
            raise HTTPException(429, "Rate limit exceeded for this hour")
        
        # Create job document
        job_dict = job.dict()
        job_dict['created_at'] = SERVER_TIMESTAMP
        job_dict['updated_at'] = SERVER_TIMESTAMP
        job_dict['status'] = EmailStatus.PENDING
        
        doc_ref = db.collection('jobs').document()
        doc_ref.set(job_dict)
        
        # Schedule job processing
        if job.schedule_time and job.schedule_time > datetime.now():
            scheduler.add_job(
                process_email_job,
                'date',
                run_date=job.schedule_time,
                args=[doc_ref.id]
            )
        else:
            background_tasks.add_task(process_email_job, doc_ref.id)
        
        return {"id": doc_ref.id, **job_dict}
    except Exception as e:
        logger.error(f"Failed to create job: {str(e)}")
        raise HTTPException(500, str(e))
    

@app.get("/jobs")
async def list_jobs():
    try:
        jobs = []
        for doc in db.collection('jobs').stream():
            jobs.append({"id": doc.id, **doc.to_dict()})
        return jobs
    except Exception as e:
        logger.error(f"Failed to list jobs: {str(e)}")
        raise HTTPException(500, str(e))

@app.get("/jobs/{job_id}")
async def get_job(job_id: str):
    try:
        doc = db.collection('jobs').document(job_id).get()
        if not doc.exists:
            raise HTTPException(404, "Job not found")
        return {"id": doc.id, **doc.to_dict()}
    except Exception as e:
        logger.error(f"Failed to get job: {str(e)}")
        raise HTTPException(500, str(e))

@app.get("/jobs/{job_id}/status")
async def get_job_status(job_id: str):
    try:
        stats = await analytics_service.get_email_stats(job_id)
        return stats
    except Exception as e:
        logger.error(f"Failed to get job status: {str(e)}")
        raise HTTPException(500, str(e))

@app.get("/analytics/hourly")
async def get_hourly_analytics(hours: int = 24):
    try:
        stats = await analytics_service.get_hourly_stats(hours)
        return stats
    except Exception as e:
        logger.error(f"Failed to get hourly analytics: {str(e)}")
        raise HTTPException(500, str(e))

REQUIRED_COLUMNS = ['Company Name', 'Location', 'Email']

@app.post("/google-sheets/connect")
async def connect_google_sheet(data: DataSource):
    try:
        if data.type != "google_sheet":
            raise HTTPException(400, "Invalid data source type")
        
        sheet_data = sheet_service.read_sheet(
            spreadsheet_id=data.source.split('/')[-1],
            range_name="A1:Z1000"
        )
        
        if not sheet_data:
            raise HTTPException(404, "No data found in sheet")
        
        columns = list(sheet_data[0].keys())
        missing_columns = [col for col in REQUIRED_COLUMNS if col not in columns]
        
        if missing_columns:
            raise HTTPException(400, f"Missing required columns: {', '.join(missing_columns)}")
        
        return {
            "columns": columns, 
            "preview": sheet_data[:5],
            "total_recipients": len(sheet_data)
        }
    except Exception as e:
        logger.error(f"Failed to connect to Google Sheet: {str(e)}")
        raise HTTPException(500, str(e))
    

    
@app.on_event("startup")
async def startup_event():
    scheduler.start()
    logger.info("Application started, scheduler initialized")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    redis_client.close()
    logger.info("Application shutting down")

def create_app():
    return app

if __name__ == "__main__":
    uvicorn.run(
        app, 
        host="127.0.0.1",
        port=8000,
        reload=True
    )

@app.get("/")
async def health_check():
    return {"status": "healthy"}
