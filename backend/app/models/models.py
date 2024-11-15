# backend/app/models/models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Enum, Boolean, Table
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.database import Base

# Association table for many-to-many relationships
campaign_tags = Table('campaign_tags', Base.metadata,
    Column('campaign_id', Integer, ForeignKey('campaigns.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

class EmailStatus(enum.Enum):
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"
    DELIVERED = "delivered"
    OPENED = "opened"
    BOUNCED = "bounced"

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    full_name = Column(String)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    email_provider_tokens = Column(JSON)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    campaigns = relationship("Campaign", back_populates="user")
    email_templates = relationship("EmailTemplate", back_populates="user")

class EmailTemplate(Base):
    __tablename__ = "email_templates"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    name = Column(String, nullable=False)
    subject = Column(String, nullable=False)
    content = Column(String, nullable=False)
    variables = Column(JSON)  # Store template variables
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", back_populates="email_templates")
    campaigns = relationship("Campaign", back_populates="template")

class Campaign(Base):
    __tablename__ = "campaigns"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    template_id = Column(Integer, ForeignKey("email_templates.id"))
    name = Column(String, nullable=False)
    description = Column(String)
    data_source = Column(JSON)  # Store Google Sheet ID or CSV file info
    scheduling_config = Column(JSON)
    status = Column(String, default="draft")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = relationship("User", back_populates="campaigns")
    template = relationship("EmailTemplate", back_populates="campaigns")
    emails = relationship("Email", back_populates="campaign")
    tags = relationship("Tag", secondary=campaign_tags, back_populates="campaigns")

class Email(Base):
    __tablename__ = "emails"
    
    id = Column(Integer, primary_key=True)
    campaign_id = Column(Integer, ForeignKey("campaigns.id"))
    recipient_email = Column(String, nullable=False)
    recipient_name = Column(String)
    subject = Column(String, nullable=False)
    content = Column(String, nullable=False)
    status = Column(Enum(EmailStatus), default=EmailStatus.DRAFT)
    scheduled_time = Column(DateTime)
    sent_time = Column(DateTime)
    tracking_data = Column(JSON)
    metadata = Column(JSON)  # Store additional recipient data
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    campaign = relationship("Campaign", back_populates="emails")

class Tag(Base):
    __tablename__ = "tags"
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    campaigns = relationship("Campaign", secondary=campaign_tags, back_populates="tags")