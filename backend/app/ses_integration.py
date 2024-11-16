# ses_integration.py
import boto3
from botocore.exceptions import ClientError
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Dict
import json
from datetime import datetime
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SESConfig:
    def __init__(self):
        self.ses_client = boto3.client(
            'ses',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )
        self.sns_client = boto3.client(
            'sns',
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY'),
            region_name=os.getenv('AWS_REGION', 'us-east-1')
        )

class EmailDeliveryStatus(BaseModel):
    message_id: str
    status: str
    email: str
    timestamp: datetime
    bounce_type: Optional[str] = None
    bounce_subtype: Optional[str] = None
    diagnostic_code: Optional[str] = None

class SESService:
    def __init__(self, db):
        self.config = SESConfig()
        self.db = db
        
    async def send_email(self, 
                        recipient: str, 
                        subject: str, 
                        body_html: str, 
                        sender: str = os.getenv('SES_SENDER_EMAIL')):
        """Send email using Amazon SES"""
        try:
            response = self.config.ses_client.send_email(
                Source=sender,
                Destination={
                    'ToAddresses': [recipient]
                },
                Message={
                    'Subject': {
                        'Data': subject,
                        'Charset': 'UTF-8'
                    },
                    'Body': {
                        'Html': {
                            'Data': body_html,
                            'Charset': 'UTF-8'
                        }
                    }
                },
                ConfigurationSetName=os.getenv('SES_CONFIGURATION_SET')
            )
            
            # Store email metadata in Firestore
            email_meta = {
                'message_id': response['MessageId'],
                'recipient': recipient,
                'status': 'sent',
                'sent_at': datetime.utcnow(),
                'subject': subject
            }
            
            await self.db.collection('email_tracking').document(response['MessageId']).set(email_meta)
            
            return response['MessageId']
            
        except ClientError as e:
            print(f"Error sending email: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def process_sns_notification(self, notification: dict):
        """Process SNS notifications for email tracking"""
        try:
            message = json.loads(notification['Message'])
            notification_type = message['notificationType']
            
            tracking_ref = self.db.collection('email_tracking').document(message['mail']['messageId'])
            
            if notification_type == 'Delivery':
                await tracking_ref.update({
                    'status': 'delivered',
                    'delivered_at': datetime.utcnow()
                })
                
            elif notification_type == 'Bounce':
                bounce_data = message['bounce']
                await tracking_ref.update({
                    'status': 'bounced',
                    'bounce_type': bounce_data['bounceType'],
                    'bounce_subtype': bounce_data['bounceSubType'],
                    'diagnostic_code': bounce_data.get('diagnosticCode'),
                    'bounced_at': datetime.utcnow()
                })
                
            elif notification_type == 'Complaint':
                await tracking_ref.update({
                    'status': 'complained',
                    'complained_at': datetime.utcnow()
                })
                
            elif notification_type == 'Open':
                await tracking_ref.update({
                    'status': 'opened',
                    'opened_at': datetime.utcnow()
                })
                
        except Exception as e:
            print(f"Error processing SNS notification: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_email_statistics(self):
        """Get email delivery statistics"""
        try:
            stats = {
                'total_sent': 0,
                'delivered': 0,
                'bounced': 0,
                'complained': 0,
                'opened': 0
            }
            
            # Query Firestore for email statistics
            email_refs = self.db.collection('email_tracking').stream()
            
            for doc in email_refs:
                email_data = doc.to_dict()
                stats['total_sent'] += 1
                
                if email_data.get('status') == 'delivered':
                    stats['delivered'] += 1
                elif email_data.get('status') == 'bounced':
                    stats['bounced'] += 1
                elif email_data.get('status') == 'complained':
                    stats['complained'] += 1
                elif email_data.get('status') == 'opened':
                    stats['opened'] += 1
            
            stats['delivery_rate'] = (stats['delivered'] / stats['total_sent'] * 100) if stats['total_sent'] > 0 else 0
            
            return stats
            
        except Exception as e:
            print(f"Error getting email statistics: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))