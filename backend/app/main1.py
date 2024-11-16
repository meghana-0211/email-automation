# main.py
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict, Union
import pandas as pd
import redis
import json
from datetime import datetime, timedelta
import os
import boto3
from botocore.exceptions import ClientError
from groq import Groq
from dotenv import load_dotenv
from firebase_admin import credentials, firestore, initialize_app
from google.cloud.firestore import SERVER_TIMESTAMP
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from fastapi import Depends, Security
from fastapi.security import OAuth2AuthorizationCodeBearer
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import re

# OAuth2 configuration
oauth2_scheme = OAuth2AuthorizationCodeBearer(
    authorizationUrl="https://accounts.google.com/o/oauth2/v2/auth",
    tokenUrl="https://oauth2.googleapis.com/token",
    scopes=["https://www.googleapis.com/auth/gmail.send"]
)

class EmailProvider(BaseModel):
    provider_type: str  # 'gmail', 'outlook', 'smtp', 'ses'
    credentials: Dict[str, str]
    smtp_settings: Optional[Dict[str, str]] = None

class EmailServiceExtended(EmailService):
    def __init__(self):
        super().__init__()
        self.connected_accounts = {}
        
    async def connect_email_account(self, provider: EmailProvider) -> str:
        """Connect an email account using OAuth2 or SMTP credentials"""
        account_id = str(uuid.uuid4())
        
        if provider.provider_type in ['gmail', 'outlook']:
            # OAuth2 flow
            flow = Flow.from_client_config(
                client_config=provider.credentials,
                scopes=['https://www.googleapis.com/auth/gmail.send']
            )
            auth_url = flow.authorization_url()[0]
            
            # Store flow for later use
            self.connected_accounts[account_id] = {
                'flow': flow,
                'provider': provider,
                'status': 'pending_auth'
            }
            
            return {'account_id': account_id, 'auth_url': auth_url}
            
        elif provider.provider_type == 'smtp':
            # Verify SMTP connection
            try:
                with smtplib.SMTP(
                    provider.smtp_settings['host'],
                    provider.smtp_settings['port']
                ) as server:
                    server.starttls()
                    server.login(
                        provider.smtp_settings['username'],
                        provider.smtp_settings['password']
                    )
                    
                self.connected_accounts[account_id] = {
                    'provider': provider,
                    'status': 'connected'
                }
                
                return {'account_id': account_id, 'status': 'connected'}
                
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failed to connect SMTP account: {str(e)}"
                )
    
    async def detect_template_fields(self, content: str) -> List[str]:
        """Detect available template fields from content"""
        # Look for placeholders in format {{field_name}}
        fields = re.findall(r'\{\{(\w+)\}\}', content)
        return list(set(fields))
    
    async def validate_template_fields(
        self,
        template_fields: List[str],
        data_columns: List[str]
    ) -> Dict[str, bool]:
        """Validate template fields against available data columns"""
        return {
            field: field in data_columns
            for field in template_fields
        }
    
    async def send_email_via_provider(
        self,
        account_id: str,
        recipient: str,
        subject: str,
        body_html: str
    ) -> str:
        """Send email using connected provider account"""
        account = self.connected_accounts.get(account_id)
        if not account:
            raise HTTPException(
                status_code=404,
                detail="Email account not found"
            )
            
        if account['provider'].provider_type == 'smtp':
            return await self._send_via_smtp(account, recipient, subject, body_html)
        elif account['provider'].provider_type in ['gmail', 'outlook']:
            return await self._send_via_oauth(account, recipient, subject, body_html)
        else:
            return await super().send_email(recipient, subject, body_html)
    
    async def _send_via_smtp(
        self,
        account: dict,
        recipient: str,
        subject: str,
        body_html: str
    ) -> str:
        """Send email via SMTP"""
        settings = account['provider'].smtp_settings
        
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = settings['username']
        msg['To'] = recipient
        msg.attach(MIMEText(body_html, 'html'))
        
        try:
            with smtplib.SMTP(settings['host'], settings['port']) as server:
                server.starttls()
                server.login(settings['username'], settings['password'])
                server.send_message(msg)
                
            return str(uuid.uuid4())  # Generate message ID
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to send email via SMTP: {str(e)}"
            )

# Load environment variables
load_dotenv()

# Initialize Firebase
cred = credentials.Certificate(os.getenv('FIREBASE_CREDENTIALS_PATH'))
initialize_app(cred)
db = firestore.client()

# Initialize FastAPI app
app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Redis for job queue and rate limiting
redis_client = redis.Redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379"))

# Initialize scheduler
scheduler = AsyncIOScheduler()

# Initialize AWS SES client
ses_client = boto3.client(
    'ses',
    aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
    region_name=os.getenv('AWS_REGION', 'us-east-1')
)

# Pydantic models
class EmailTemplate(BaseModel):
    name: str
    content: str
    subject: str

class Recipient(BaseModel):
    email: EmailStr
    data: Dict[str, str]

class EmailJobCreate(BaseModel):
    template_id: str
    recipients: List[Recipient]
    schedule: Optional[datetime] = None
    throttle_rate: Optional[int] = None  # Emails per hour

class EmailDeliveryStatus(BaseModel):
    message_id: str
    status: str
    email: str
    timestamp: datetime
    bounce_type: Optional[str] = None
    diagnostic_code: Optional[str] = None

# Email service class
class EmailService:
    def __init__(self):
        self.groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    async def generate_content(self, template: str, data: dict) -> str:
        """Generate personalized email content using Groq LLM"""
        prompt = f"""
        Generate a personalized email based on this template:
        {template}
        
        Using this data:
        {json.dumps(data)}
        
        The response should be the final email with all placeholders replaced with actual data.
        """
        
        response = await self.groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="mixtral-8x7b-32768"
        )
        
        return response.choices[0].message.content
    
    async def send_email(self, recipient: str, subject: str, body_html: str) -> str:
        """Send email using Amazon SES"""
        try:
            # Check rate limit
            if not await self._check_rate_limit():
                raise HTTPException(status_code=429, detail="Rate limit exceeded")
                
            response = ses_client.send_email(
                Source=os.getenv('SES_SENDER_EMAIL'),
                Destination={'ToAddresses': [recipient]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {'Html': {'Data': body_html, 'Charset': 'UTF-8'}}
                },
                ConfigurationSetName=os.getenv('SES_CONFIGURATION_SET')
            )
            
            return response['MessageId']
            
        except ClientError as e:
            print(f"Error sending email: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _check_rate_limit(self) -> bool:
        """Check if within SES rate limits"""
        current_count = redis_client.get('ses_daily_count')
        if current_count and int(current_count) >= 50000:  # SES daily limit
            return False
        redis_client.incr('ses_daily_count')
        redis_client.expire('ses_daily_count', 86400)  # 24 hours
        return True

# Initialize email service
email_service = EmailService()

# Routes
@app.post("/api/email-accounts")
async def connect_email_account(provider: EmailProvider):
    """Connect new email account"""
    return await email_service.connect_email_account(provider)

@app.post("/api/templates/validate")
async def validate_template(
    template: EmailTemplate,
    columns: List[str]
):
    """Validate template fields against available columns"""
    fields = await email_service.detect_template_fields(template.content)
    validation = await email_service.validate_template_fields(fields, columns)
    return {
        'fields': fields,
        'validation': validation
    }
@app.post("/api/upload/csv")
async def upload_csv(file: UploadFile = File(...)):
    """Upload and parse CSV file"""
    try:
        contents = await file.read()
        df = pd.read_csv(pd.io.StringIO(contents.decode('utf-8')))
        
        # Convert DataFrame to list of dictionaries with email validation
        recipients = []
        for _, row in df.iterrows():
            data = row.to_dict()
            if 'email' not in data:
                raise HTTPException(status_code=400, detail="CSV must contain 'email' column")
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
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/templates")
async def create_template(template: EmailTemplate):
    """Create a new email template"""
    try:
        template_ref = db.collection('templates').document()
        template_data = {
            'name': template.name,
            'content': template.content,
            'subject': template.subject,
            'created_at': SERVER_TIMESTAMP
        }
        template_ref.set(template_data)
        
        return {
            'id': template_ref.id,
            **template_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs")
async def create_email_job(
    job: EmailJobCreate,
    background_tasks: BackgroundTasks,
    account_id: Optional[str] = None
):
    """Create and schedule new email job with optional custom provider"""
    try:
        # Create job in Firestore
        job_ref = db.collection('jobs').document()
        job_data = {
            'template_id': job.template_id,
            'status': 'pending',
            'recipients': [r.dict() for r in job.recipients],
            'schedule': job.schedule,
            'throttle_rate': job.throttle_rate,
            'account_id': account_id,
            'created_at': SERVER_TIMESTAMP
        }
        job_ref.set(job_data)
        
        # Schedule job processing
        if job.schedule:
            scheduler.add_job(
                process_email_job,
                trigger=DateTrigger(run_date=job.schedule),
                args=[job_ref.id],
                id=job_ref.id
            )
        else:
            background_tasks.add_task(process_email_job, job_ref.id)
        
        return {
            'id': job_ref.id,
            **job_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/jobs")
async def create_email_job(
    job: EmailJobCreate,
    background_tasks: BackgroundTasks,
    account_id: Optional[str] = None
):
    """Create and schedule new email job with optional custom provider"""
    try:
        # Create job in Firestore
        job_ref = db.collection('jobs').document()
        job_data = {
            'template_id': job.template_id,
            'status': 'pending',
            'recipients': [r.dict() for r in job.recipients],
            'schedule': job.schedule,
            'throttle_rate': job.throttle_rate,
            'account_id': account_id,
            'created_at': SERVER_TIMESTAMP
        }
        job_ref.set(job_data)
        
        # Schedule job processing
        if job.schedule:
            scheduler.add_job(
                process_email_job,
                trigger=DateTrigger(run_date=job.schedule),
                args=[job_ref.id],
                id=job_ref.id
            )
        else:
            background_tasks.add_task(process_email_job, job_ref.id)
        
        return {
            'id': job_ref.id,
            **job_data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/ses/webhook")
async def ses_webhook(request: Request):
    """Handle SES webhook notifications"""
    try:
        notification = await request.json()
        message = json.loads(notification['Message'])
        
        tracking_ref = db.collection('email_tracking').document(message['mail']['messageId'])
        
        if message['notificationType'] == 'Delivery':
            await tracking_ref.update({
                'status': 'delivered',
                'delivered_at': SERVER_TIMESTAMP
            })
        elif message['notificationType'] == 'Bounce':
            await tracking_ref.update({
                'status': 'bounced',
                'bounce_type': message['bounce']['bounceType'],
                'diagnostic_code': message['bounce'].get('diagnosticCode'),
                'bounced_at': SERVER_TIMESTAMP
            })
        elif message['notificationType'] == 'Complaint':
            await tracking_ref.update({
                'status': 'complained',
                'complained_at': SERVER_TIMESTAMP
            })
        
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/analytics")
async def get_analytics():
    """Get email analytics"""
    try:
        stats = {
            'total_sent': 0,
            'delivered': 0,
            'bounced': 0,
            'complained': 0,
            'pending': 0
        }
        
        # Get email tracking stats
        tracking_refs = db.collection('email_tracking').stream()
        for doc in tracking_refs:
            email_data = doc.to_dict()
            stats['total_sent'] += 1
            if email_data.get('status') == 'delivered':
                stats['delivered'] += 1
            elif email_data.get('status') == 'bounced':
                stats['bounced'] += 1
            elif email_data.get('status') == 'complained':
                stats['complained'] += 1
        
        # Get job stats
        job_refs = db.collection('jobs').stream()
        for doc in job_refs:
            job_data = doc.to_dict()
            if job_data.get('status') == 'pending':
                stats['pending'] += len(job_data.get('recipients', []))
        
        # Calculate rates
        stats['delivery_rate'] = (stats['delivered'] / stats['total_sent'] * 100) if stats['total_sent'] > 0 else 0
        stats['bounce_rate'] = (stats['bounced'] / stats['total_sent'] * 100) if stats['total_sent'] > 0 else 0
        
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Startup events
@app.on_event("startup")
async def startup_event():
    """Start scheduler on app startup"""
    scheduler.start()

# Shutdown events
@app.on_event("shutdown")
async def shutdown_event():
    """Shutdown scheduler on app shutdown"""
    scheduler.shutdown()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)