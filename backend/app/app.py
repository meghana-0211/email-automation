# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict
import pandas as pd
import redis
import json
from datetime import datetime
import os
from groq import Groq
from dotenv import load_dotenv
from firebase_admin import credentials, firestore, initialize_app
from google.cloud.firestore import SERVER_TIMESTAMP
from ses_integration import SESService
from fastapi import BackgroundTasks



# Load environment variables
load_dotenv()

# Initialize Firebase
cred = credentials.Certificate(r"C:\Users\Megha\OneDrive\Desktop\breakoutai\email-automation\backend\app\firebase-key.json")
initialize_app(cred)
db = firestore.client()

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis setup for job queue
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Pydantic models for request/response
class TemplateCreate(BaseModel):
    name: str
    content: str

class EmailJobCreate(BaseModel):
    template_id: str  # Changed to str for Firestore document IDs
    recipients: List[dict]
    schedule: Optional[datetime] = None

# Routes
@app.post("/api/upload/csv")
async def upload_csv(file: UploadFile = File(...)):
    """Upload and parse CSV file"""
    try:
        contents = await file.read()
        df = pd.read_csv(pd.io.StringIO(contents.decode('utf-8')))
        return {
            "columns": df.columns.tolist(),
            "preview": df.head().to_dict('records')
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/templates")
async def create_template(template: TemplateCreate):
    """Create a new email template"""
    try:
        template_ref = db.collection('templates').document()
        template_data = {
            'name': template.name,
            'content': template.content,
            'created_at': SERVER_TIMESTAMP
        }
        template_ref.set(template_data)
        
        # Get the created document for response
        template_doc = template_ref.get()
        return {
            'id': template_doc.id,
            **template_doc.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/templates")
async def get_templates():
    """Get all templates"""
    try:
        templates = []
        template_refs = db.collection('templates').stream()
        for doc in template_refs:
            templates.append({
                'id': doc.id,
                **doc.to_dict()
            })
        return templates
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs")
async def create_email_job(job: EmailJobCreate):
    """Create a new email job"""
    try:
        # Create job in Firestore
        job_ref = db.collection('jobs').document()
        job_data = {
            'template_id': job.template_id,
            'status': 'pending',
            'recipients': job.recipients,
            'schedule': job.schedule,
            'created_at': SERVER_TIMESTAMP
        }
        job_ref.set(job_data)
        
        # Add to Redis queue for processing
        redis_client.lpush("email_queue", json.dumps({
            "job_id": job_ref.id,
            "template_id": job.template_id,
            "recipients": job.recipients,
            "schedule": job.schedule.isoformat() if job.schedule else None
        }))
        
        # Get the created document for response
        job_doc = job_ref.get()
        return {
            'id': job_doc.id,
            **job_doc.to_dict()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Add to SESService
async def check_rate_limit(self):
    current_count = redis_client.get('ses_daily_count')
    if current_count and int(current_count) >= 50000:  # SES daily limit
        raise HTTPException(status_code=429, detail="Daily sending limit reached")
    redis_client.incr('ses_daily_count')
    redis_client.expire('ses_daily_count', 86400)  # 24 hours

@app.get("/api/jobs")
async def get_jobs():
    """Get all jobs"""
    try:
        jobs = []
        job_refs = db.collection('jobs').stream()
        for doc in job_refs:
            jobs.append({
                'id': doc.id,
                **doc.to_dict()
            })
        return jobs
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics")
async def get_analytics():
    """Get email analytics"""
    try:
        # Get email statistics from SES
        email_stats = await ses_service.get_email_statistics()
        
        # Get job statistics from Firestore
        completed = db.collection('jobs').where('status', '==', 'completed').get()
        pending = db.collection('jobs').where('status', '==', 'pending').get()
        failed = db.collection('jobs').where('status', '==', 'failed').get()
        
        return {
            **email_stats,
            "jobs_completed": len(completed),
            "jobs_pending": len(pending),
            "jobs_failed": len(failed)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
# Email generation with LLM
async def generate_email_content(template: str, data: dict):
    """Generate personalized email content using LLM"""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    prompt = f"""
    Generate a personalized email based on this template:
    {template}
    
    Using this data:
    {json.dumps(data)}
    
    The response should be the final email with all placeholders replaced with actual data.
    """
    
    response = await client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="mixtral-8x7b-32768"
    )
    
    return response.choices[0].message.content

# Background task for processing email queue
async def process_email_queue():
    """Process emails from the queue"""
    while True:
        job_data = redis_client.rpop("email_queue")
        if job_data:
            job = json.loads(job_data)
            try:
                # Get template from Firestore
                template_doc = db.collection('templates').document(job["template_id"]).get()
                template = template_doc.to_dict()
                
                # Generate and send emails
                for recipient in job["recipients"]:
                    email_content = await generate_email_content(template['content'], recipient)
                    
                    # Send email using SES
                    message_id = await ses_service.send_email(
                        recipient=recipient.get('email'),
                        subject=template.get('subject', 'Your Email Subject'),
                        body_html=email_content
                    )
                    
                    # Update job status in Firestore
                    job_ref = db.collection('jobs').document(job["job_id"])
                    job_ref.update({
                        'status': 'completed',
                        'completed_at': SERVER_TIMESTAMP,
                        'message_id': message_id
                    })
                    
            except Exception as e:
                print(f"Error processing job {job['job_id']}: {str(e)}")
                if 'job_ref' in locals():
                    job_ref.update({
                        'status': 'failed',
                        'error': str(e),
                        'failed_at': SERVER_TIMESTAMP
                    })

# Start background tasks
@app.on_event("startup")
async def startup_event():
    """Start background tasks when app starts"""
    import asyncio
    asyncio.create_task(process_email_queue())

@app.post("/api/ses/webhook")
async def ses_webhook(background_tasks: BackgroundTasks):
    """Handle SES webhook notifications"""
    try:
        notification = await request.json()
        
        # Verify SNS message signature
        # Process notification in background
        background_tasks.add_task(ses_service.process_sns_notification, notification)
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)