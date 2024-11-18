from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Union, Any
from pydantic import BaseModel, EmailStr, HttpUrl, Field, validator
import re

class EmailStatus(str, Enum):
    """
    Enum for tracking email status throughout the system
    """
    PENDING = "pending"
    PROCESSING = "processing"
    SCHEDULED = "scheduled"
    SENT = "sent"
    DELIVERED = "delivered"
    FAILED = "failed"
    BOUNCED = "bounced"
    OPENED = "opened"
    CLICKED = "clicked"
    SPAM = "spam"
    UNSUBSCRIBED = "unsubscribed"

class DataSourceType(str, Enum):
    """
    Supported data source types
    """
    GOOGLE_SHEET = "google_sheet"
    CSV = "csv"

class DataSource(BaseModel):
    """
    Model for handling different data sources
    """
    type: DataSourceType
    source: str = Field(..., description="URL for Google Sheet or file path for CSV")
    columns: List[str] = Field(default_factory=list)
    sheet_name: Optional[str] = Field(None, description="Sheet name for Google Sheets")
    range: Optional[str] = Field(None, description="Cell range for Google Sheets")

    @validator('source')
    def validate_source(cls, v, values):
        if values.get('type') == DataSourceType.GOOGLE_SHEET:
            # Validate Google Sheets URL format
            pattern = r'https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)'
            if not re.match(pattern, v):
                raise ValueError("Invalid Google Sheets URL format")
        return v

class Recipient(BaseModel):
    """
    Model for email recipients with their personalization data
    """
    email: EmailStr
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Personalization data for email template"
    )
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('email')
    def validate_email_domain(cls, v):
        domain = v.split('@')[1]
        if domain.lower() in ['example.com', 'test.com']:
            raise ValueError("Invalid email domain")
        return v

class EmailTemplate(BaseModel):
    """
    Model for email templates with personalization capabilities
    """
    id: Optional[str] = None
    name: str = Field(..., min_length=1, max_length=100)
    subject: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1)
    placeholders: List[str] = Field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    version: Optional[int] = Field(1, description="Template version for tracking changes")
    is_active: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('content')
    def validate_placeholders_in_content(cls, v, values):
        if 'placeholders' in values:
            for placeholder in values['placeholders']:
                if '{' + placeholder + '}' not in v:
                    raise ValueError(f"Placeholder {placeholder} not found in content")
        return v

class EmailScheduling(BaseModel):
    """
    Model for email scheduling configuration
    """
    enabled: bool = False
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    timezone: str = "UTC"
    batch_size: Optional[int] = Field(None, ge=1)
    interval_minutes: Optional[int] = Field(None, ge=1)
    max_emails_per_day: Optional[int] = Field(None, ge=1)

class EmailJob(BaseModel):
    """
    Model for email sending jobs
    """
    id: Optional[str] = None
    template_id: str
    status: EmailStatus = EmailStatus.PENDING
    recipients: List[Recipient]
    data_source: Optional[DataSource] = None
    schedule: Optional[EmailScheduling] = None
    throttle_rate: int = Field(
        default=100,
        ge=1,
        le=1000,
        description="Emails per hour rate limit"
    )
    retry_count: int = Field(default=0, ge=0, le=5)
    retry_delay: int = Field(
        default=300,
        ge=60,
        description="Delay in seconds between retries"
    )
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('recipients')
    def validate_recipients_limit(cls, v):
        if len(v) > 10000:  # Adjust this limit based on your needs
            raise ValueError("Too many recipients in a single job")
        return v

class EmailTracking(BaseModel):
    """
    Model for tracking email delivery and engagement
    """
    message_id: str
    job_id: str
    recipient: EmailStr
    status: EmailStatus
    sent_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    clicked_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    bounced_at: Optional[datetime] = None
    error: Optional[str] = None
    open_count: int = Field(default=0, ge=0)
    click_count: int = Field(default=0, ge=0)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class AnalyticsData(BaseModel):
    """
    Model for email analytics data
    """
    total_sent: int = 0
    total_delivered: int = 0
    total_opened: int = 0
    total_clicked: int = 0
    total_failed: int = 0
    total_bounced: int = 0
    delivery_rate: float = 0.0
    open_rate: float = 0.0
    click_rate: float = 0.0
    bounce_rate: float = 0.0
    time_period: str
    start_date: datetime
    end_date: datetime

class WebhookEvent(BaseModel):
    """
    Model for handling ESP webhook events
    """
    event_type: str
    message_id: str
    timestamp: datetime
    recipient: EmailStr
    event_data: Dict[str, Any] = Field(default_factory=dict)
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }