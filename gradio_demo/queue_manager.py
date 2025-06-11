"""
Queue Management System for MultiTalk Gradio Demo
Provides queue visibility and job tracking functionality
"""

import time
import json
import threading
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
import uuid
import logging

logger = logging.getLogger(__name__)

@dataclass
class JobInfo:
    """Information about a queued job"""
    job_id: str
    user_session: str
    job_type: str  # "single" or "multi"
    status: str  # "queued", "processing", "completed", "failed"
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    current_step: str = ""
    estimated_duration: Optional[float] = None
    error_message: Optional[str] = None

class QueueManager:
    """Manages job queue and provides status information"""
    
    def __init__(self):
        self.jobs: Dict[str, JobInfo] = {}
        self.queue_order: List[str] = []
        self.active_job: Optional[str] = None
        self.lock = threading.Lock()
        self.job_history: List[JobInfo] = []
        
        # Performance tracking
        self.avg_processing_times = {
            "single": 120.0,  # Default 2 minutes
            "multi": 180.0    # Default 3 minutes
        }
    
    def add_job(self, job_type: str, user_session: str = None) -> str:
        """Add a new job to the queue"""
        job_id = str(uuid.uuid4())[:8]
        
        if user_session is None:
            user_session = f"session_{int(time.time())}"
        
        job = JobInfo(
            job_id=job_id,
            user_session=user_session,
            job_type=job_type,
            status="queued",
            created_at=datetime.now(),
            estimated_duration=self.avg_processing_times.get(job_type, 150.0)
        )
        
        with self.lock:
            self.jobs[job_id] = job
            self.queue_order.append(job_id)
        
        logger.info(f"Added job {job_id} to queue (type: {job_type})")
        return job_id
    
    def start_job(self, job_id: str) -> bool:
        """Mark a job as started"""
        with self.lock:
            if job_id not in self.jobs:
                return False
            
            job = self.jobs[job_id]
            job.status = "processing"
            job.started_at = datetime.now()
            self.active_job = job_id
            
            # Remove from queue order
            if job_id in self.queue_order:
                self.queue_order.remove(job_id)
        
        logger.info(f"Started processing job {job_id}")
        return True
    
    def update_job_progress(self, job_id: str, progress: float, current_step: str = ""):
        """Update job progress"""
        with self.lock:
            if job_id in self.jobs:
                self.jobs[job_id].progress = progress
                self.jobs[job_id].current_step = current_step
    
    def complete_job(self, job_id: str, success: bool = True, error_message: str = None):
        """Mark a job as completed"""
        with self.lock:
            if job_id not in self.jobs:
                return
            
            job = self.jobs[job_id]
            job.status = "completed" if success else "failed"
            job.completed_at = datetime.now()
            job.progress = 1.0 if success else job.progress
            
            if error_message:
                job.error_message = error_message
            
            # Update average processing time
            if success and job.started_at:
                duration = (job.completed_at - job.started_at).total_seconds()
                self._update_avg_processing_time(job.job_type, duration)
            
            # Move to history and clean up
            self.job_history.append(job)
            if len(self.job_history) > 100:  # Keep last 100 jobs
                self.job_history.pop(0)
            
            # Clear active job
            if self.active_job == job_id:
                self.active_job = None
            
            # Clean up old job
            del self.jobs[job_id]
        
        logger.info(f"Completed job {job_id} (success: {success})")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status"""
        with self.lock:
            queue_jobs = [self.jobs[job_id] for job_id in self.queue_order if job_id in self.jobs]
            active_job_info = self.jobs.get(self.active_job) if self.active_job else None
            
            total_estimated_wait = 0
            for i, job in enumerate(queue_jobs):
                if i == 0 and active_job_info:
                    # First job waits for current job to finish
                    remaining_time = self._estimate_remaining_time(active_job_info)
                    total_estimated_wait += remaining_time
                else:
                    total_estimated_wait += job.estimated_duration or 150.0
            
            return {
                "queue_length": len(queue_jobs),
                "active_job": asdict(active_job_info) if active_job_info else None,
                "estimated_wait_time": total_estimated_wait,
                "queue_jobs": [asdict(job) for job in queue_jobs[:5]],  # Show first 5
                "avg_processing_times": self.avg_processing_times.copy()
            }
    
    def get_job_position(self, job_id: str) -> Optional[int]:
        """Get position of job in queue (1-indexed)"""
        with self.lock:
            try:
                return self.queue_order.index(job_id) + 1
            except ValueError:
                return None
    
    def get_job_info(self, job_id: str) -> Optional[JobInfo]:
        """Get information about a specific job"""
        with self.lock:
            return self.jobs.get(job_id)
    
    def _estimate_remaining_time(self, job: JobInfo) -> float:
        """Estimate remaining time for a job in progress"""
        if not job.started_at or job.progress <= 0:
            return job.estimated_duration or 150.0
        
        elapsed = (datetime.now() - job.started_at).total_seconds()
        if job.progress >= 1.0:
            return 0.0
        
        estimated_total = elapsed / job.progress
        return max(0, estimated_total - elapsed)
    
    def _update_avg_processing_time(self, job_type: str, duration: float):
        """Update average processing time with exponential moving average"""
        if job_type in self.avg_processing_times:
            # Use exponential moving average with alpha=0.3
            current_avg = self.avg_processing_times[job_type]
            self.avg_processing_times[job_type] = 0.7 * current_avg + 0.3 * duration
    
    def cleanup_old_jobs(self, max_age_hours: int = 24):
        """Clean up old completed jobs"""
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        with self.lock:
            # Clean up job history
            self.job_history = [
                job for job in self.job_history 
                if job.completed_at and job.completed_at > cutoff_time
            ]
            
            # Clean up any stale jobs in main dict
            stale_jobs = [
                job_id for job_id, job in self.jobs.items()
                if job.created_at < cutoff_time and job.status in ["completed", "failed"]
            ]
            
            for job_id in stale_jobs:
                del self.jobs[job_id]
                if job_id in self.queue_order:
                    self.queue_order.remove(job_id)

# Global queue manager instance
queue_manager = QueueManager()
