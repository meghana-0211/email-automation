#email_service.py

import boto3
from botocore.exceptions import ClientError
from groq import Groq
import asyncio
from datetime import datetime
import json
import logging
from typing import Dict, List, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from settings import settings

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(self):
        self.ses_client = boto3.client(
            'ses',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )
        self.groq_client = Groq(api_key=settings.GROQ_API_KEY)
    
    async def generate_content(self, prompt: str, data: dict) -> str:
        try:
            formatted_prompt = prompt.format(**data)
            chat_completion = await self.groq_client.chat.completions.create(
                messages=[
                    {
                        "role": "system",
                        "content": "You are a professional email writer. Write engaging and personalized emails."
                    },
                    {
                        "role": "user",
                        "content": formatted_prompt
                    }
                ],
                model="mixtral-8x7b-32768",
                temperature=0.7,
                max_tokens=1000
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.error(f"Content generation failed: {str(e)}")
            raise
    
    async def send_email(self, recipient: str, subject: str, content: str) -> str:
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = settings.SES_SENDER_EMAIL
            msg['To'] = recipient
            
            html_part = MIMEText(content, 'html')
            msg.attach(html_part)
            
            response = self.ses_client.send_raw_email(
                Source=settings.SES_SENDER_EMAIL,
                Destinations=[recipient],
                RawMessage={'Data': msg.as_string()},
                ConfigurationSetName=settings.SES_CONFIGURATION_SET
            )
            return response['MessageId']
        except ClientError as e:
            logger.error(f"Failed to send email via AWS SES: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error while sending email: {str(e)}")
            raise