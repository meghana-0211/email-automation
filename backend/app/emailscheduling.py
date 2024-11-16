from fastapi import FastAPI, BackgroundTasks
from redis import Redis
from typing import List, Dict, Optional
import asyncio
from datetime import datetime, timedelta
import pytz
from email_validator import validate_email, EmailNotValidError

class EmailScheduler:
    def __init__(self, redis_client: Redis, db_session, esp_client):
        self.redis = redis_client
        self.db = db_session
        self.esp = esp_client
        self.processing = False

    async def schedule_campaign(self, campaign_data: Dict) -> Dict:
        """Schedule a new email campaign with smart optimization"""
        try:
            # Validate and prepare recipient list
            recipients = await self.prepare_recipients(campaign_data["recipients"])
            
            # Determine optimal send times
            send_times = await self.calculate_send_times(
                recipients=recipients,
                rate_limit=campaign_data["rate_limit"],
                start_time=campaign_data["start_time"],
                end_time=campaign_data["end_time"]
            )
            
            # Create campaign record
            campaign_id = await self.create_campaign_record(
                campaign_data,
                len(recipients)
            )
            
            # Queue emails with calculated send times
            await self.queue_emails(
                campaign_id=campaign_id,
                recipients=recipients,
                send_times=send_times
            )
            
            return {
                "campaign_id": campaign_id,
                "scheduled_count": len(recipients),
                "first_send": min(send_times),
                "last_send": max(send_times)
            }
            
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to schedule campaign: {str(e)}"
            )

    async def prepare_recipients(self, recipients: List[Dict]) -> List[Dict]:
        """Validate and prepare recipient list"""
        valid_recipients = []
        
        for recipient in recipients:
            try:
                # Validate email
                valid = validate_email(recipient["email"])
                
                # Check against suppression list
                if await self.check_suppression(valid.email):
                    continue
                    
                # Enrich recipient data
                enriched_data = await self.enrich_recipient_data(recipient)
                
                valid_recipients.append(enriched_data)
                
            except EmailNotValidError:
                # Log invalid email
                await self.log_invalid_recipient(recipient)
                continue
                
        return valid_recipients

    async def calculate_send_times(
        self,
        recipients: List[Dict],
        rate_limit: int,
        start_time: datetime,
        end_time: datetime
    ) -> List[datetime]:
        """Calculate optimal send times for each recipient"""
        send_times = []
        total_duration = (end_time - start_time).total_seconds()
        interval = total_duration / len(recipients)
        
        for idx, recipient in enumerate(recipients):
            # Get recipient's timezone
            recipient_tz = pytz.timezone(
                recipient.get("timezone", "UTC")
            )
            
            # Calculate base send time
            base_time = start_time + timedelta(seconds=idx * interval)
            
            # Adjust for recipient's timezone
            local_time = base_time.astimezone(recipient_tz)
            
            # Optimize for recipient's time
            optimized_time = await self.optimize_send_time(
                local_time,
                recipient.get("engagement_history", {})
            )
            
            send_times.append(optimized_time)
            
        return send_times

    async def optimize_send_time(
        self,
        base_time: datetime,
        engagement_history: Dict
    ) -> datetime:
        """Optimize send time based on recipient's engagement history"""
        if not engagement_history:
            return base_time
            
        # Analyze best sending hours from history
        engagement_hours = engagement_history.get("open_hours", [])
        if engagement_hours:
            # Find the closest preferred hour
            current_hour = base_time.hour
            preferred_hour = min(
                engagement_hours,
                key=lambda x: abs(x - current_hour)
            )
            
            # Adjust time if needed
            if current_hour != preferred_hour:
                base_time = base_time.replace(hour=preferred_hour)
                
        return base_time

    async def queue_emails(
        self,
        campaign_id: str,
        recipients: List[Dict],
        send_times: List[datetime]
    ) -> None:
        """Queue emails for sending"""
        for recipient, send_time in zip(recipients, send_times):
            email_data = {
                "campaign_id": campaign_id,
                "recipient": recipient,
                "scheduled_time": send_time.timestamp(),
                "status": "queued",
                "retry_count": 0
            }
            
            # Add to Redis sorted set
            await self.redis.zadd(
                f"campaign:{campaign_id}:queue",
                {json.dumps(email_data): send_time.timestamp()}
            )
            
            # Store in database
            await self.db.recipients.insert_one({
                **email_data,
                "created_at": datetime.now()
            })

    async def process_queue(self):
        """Process email queue with smart throttling"""
        self.processing = True
        
        while self.processing:
            try:
                # Get current campaigns
                campaigns = await self.db.campaigns.find(
                    {"status": "active"}
                ).to_list(None)
                
                for campaign in campaigns:
                    # Get due emails
                    due_emails = await self.get_due_emails(campaign["_id"])
                    
                    if not due_emails:
                        continue
                        
                    # Process emails with rate limiting
                    for email in due_emails:
                        if await self.check_rate_limit(campaign["_id"]):
                            # Wait if rate limit reached
                            await asyncio.sleep(1)
                            continue
                            
                        # Send email
                        success = await self.send_email(email)
                        
                        if success:
                            # Update status and remove from queue
                            await self.mark_email_sent(email)
                        else:
                            # Handle failure
                            await self.handle_send_failure(email)
                            
                # Sleep briefly before next check
                await asyncio.sleep(0.1)
                
            except Exception as e:
                # Log error and continue
                print(f"Queue processing error: {str(e)}")
                await asyncio.sleep(1)

    async def check_rate_limit(self, campaign_id: str) -> bool:
        """Check if rate limit is reached"""
        now = datetime.now()
        window_start = now - timedelta(minutes=1)
        
        # Count sends in last minute
        sent_count = await self.db.email_tracking.count_documents({
            "campaign_id": campaign_id,
            "sent_time": {"$gte": window_start}
        })
        
        campaign = await self.db.campaigns.find_one({"_id": campaign_id})
        return sent_count >= campaign["rate_limit"]