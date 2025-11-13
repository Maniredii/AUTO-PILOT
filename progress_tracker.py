#!/usr/bin/env python3
"""
Real-time Progress Tracker
Provides live updates and progress monitoring
"""

import time
from datetime import datetime, timedelta
from typing import Dict, Optional
from threading import Lock

class ProgressTracker:
    """Real-time progress tracking and reporting"""
    
    def __init__(self):
        self.start_time = datetime.now()
        self.lock = Lock()
        self.current_job = None
        self.jobs_processed = 0
        self.jobs_successful = 0
        self.jobs_failed = 0
        self.jobs_skipped = 0
        self.current_position = None
        self.current_location = None
        self.last_update = datetime.now()
        
    def start_job(self, job_title: str, company: str):
        """Start tracking a new job"""
        with self.lock:
            self.current_job = {
                'title': job_title,
                'company': company,
                'start_time': datetime.now()
            }
            self.last_update = datetime.now()
    
    def complete_job(self, status: str):
        """Mark current job as complete"""
        with self.lock:
            if self.current_job:
                self.current_job['status'] = status
                self.current_job['duration'] = (datetime.now() - self.current_job['start_time']).total_seconds()
                self.jobs_processed += 1
                
                if status == 'success':
                    self.jobs_successful += 1
                elif status == 'failed':
                    self.jobs_failed += 1
                else:
                    self.jobs_skipped += 1
                
                self.current_job = None
                self.last_update = datetime.now()
    
    def set_search_context(self, position: str, location: str):
        """Set current search context"""
        with self.lock:
            self.current_position = position
            self.current_location = location
            self.last_update = datetime.now()
    
    def get_progress_summary(self) -> Dict:
        """Get current progress summary"""
        with self.lock:
            elapsed = datetime.now() - self.start_time
            success_rate = (self.jobs_successful / self.jobs_processed * 100) if self.jobs_processed > 0 else 0.0
            
            return {
                'elapsed_time': str(elapsed),
                'jobs_processed': self.jobs_processed,
                'jobs_successful': self.jobs_successful,
                'jobs_failed': self.jobs_failed,
                'jobs_skipped': self.jobs_skipped,
                'success_rate': success_rate,
                'current_job': self.current_job,
                'current_position': self.current_position,
                'current_location': self.current_location,
                'jobs_per_hour': (self.jobs_processed / elapsed.total_seconds() * 3600) if elapsed.total_seconds() > 0 else 0.0
            }
    
    def print_progress(self):
        """Print formatted progress update"""
        summary = self.get_progress_summary()
        
        print("\n" + "=" * 70)
        print("📊 PROGRESS UPDATE")
        print("=" * 70)
        print(f"⏱️  Elapsed Time: {summary['elapsed_time']}")
        print(f"📝 Jobs Processed: {summary['jobs_processed']}")
        print(f"   ✅ Successful: {summary['jobs_successful']}")
        print(f"   ❌ Failed: {summary['jobs_failed']}")
        print(f"   ⏭️  Skipped: {summary['jobs_skipped']}")
        print(f"📈 Success Rate: {summary['success_rate']:.1f}%")
        print(f"⚡ Jobs/Hour: {summary['jobs_per_hour']:.1f}")
        
        if summary['current_job']:
            job = summary['current_job']
            print(f"\n🔄 Current Job:")
            print(f"   {job['title']} at {job.get('company', 'Unknown')}")
        
        if summary['current_position']:
            print(f"\n🎯 Current Search:")
            print(f"   Position: {summary['current_position']}")
            print(f"   Location: {summary['current_location']}")
        
        print("=" * 70 + "\n")

