# backend/queue/manager.py
from rq import Queue
from redis import Redis
from typing import Dict, Any

class QueueManager:
    def __init__(self):
        self.redis_conn = Redis()
        self.queue = Queue(connection=self.redis_conn)
        
    def enqueue_job(self, job_data: Dict[str, Any]):
        job = self.queue.enqueue(
            'process_email_job',
            job_data,
            job_timeout='1h',
            result_ttl=500
        )
        return job.id
        
    def get_job_status(self, job_id: str):
        job = self.queue.fetch_job(job_id)
        if job is None:
            return None
        return {
            'id': job.id,
            'status': job.get_status(),
            'result': job.result,
            'error': job.exc_info
        }