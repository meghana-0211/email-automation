from services.email_service import EmailService
import asyncio
from settings import settings
from logger import logger
from services.analytics_service import AnalyticsService

analytics_service = AnalyticsService(db)

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
        job_ref.update({'status': 'processing'})
        
        # Get template
        template_ref = db.collection('templates').document(job_data['template_id'])
        template_data = template_ref.get().to_dict()
        
        if not template_data:
            logger.error(f"Template {job_data['template_id']} not found")
            job_ref.update({'status': 'failed', 'error': 'Template not found'})
            return
        
        # Initialize services
        email_service = EmailService()
        
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
                db.collection('email_tracking').document(message_id).set({
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
                db.collection('email_tracking').document().set({
                    'job_id': job_id,
                    'recipient': recipient['email'],
                    'status': 'failed',
                    'error': str(e),
                    'failed_at': SERVER_TIMESTAMP
                })
        
        # Update job status
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
