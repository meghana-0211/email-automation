#analytics_service.py

from typing import Dict, List
from firebase_admin import firestore
from datetime import datetime, timedelta

class AnalyticsService:
    def __init__(self, db: firestore.Client):
        self.db = db
    
    async def get_email_stats(self, job_id: str = None) -> Dict:
        query = self.db.collection('email_tracking')
        if job_id:
            query = query.where('job_id', '==', job_id)
        
        docs = query.stream()
        stats = {
            'total': 0,
            'sent': 0,
            'delivered': 0,
            'opened': 0,
            'failed': 0,
            'bounced': 0
        }
        
        for doc in docs:
            data = doc.to_dict()
            stats['total'] += 1
            stats[data['status']] += 1
        
        return stats
    
    async def get_hourly_stats(self, hours: int = 24) -> List[Dict]:
        start_time = datetime.now() - timedelta(hours=hours)
        docs = self.db.collection('email_tracking')\
            .where('sent_at', '>=', start_time)\
            .stream()
        
        hourly_stats = {}
        for doc in docs:
            data = doc.to_dict()
            hour = data['sent_at'].replace(minute=0, second=0, microsecond=0)
            if hour not in hourly_stats:
                hourly_stats[hour] = {
                    'sent': 0, 'delivered': 0, 'opened': 0, 'failed': 0
                }
            hourly_stats[hour][data['status']] += 1
        
        return [{'hour': hour, **stats} for hour, stats in sorted(hourly_stats.items())]
