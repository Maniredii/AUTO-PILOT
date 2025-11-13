#!/usr/bin/env python3
"""
Enhanced Statistics Dashboard for LinkedIn Easy Apply Bot
Provides comprehensive analytics, reporting, and visualization
"""

import json
import csv
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from collections import defaultdict

class StatisticsDashboard:
    """Comprehensive statistics tracking and reporting"""
    
    def __init__(self, output_dir: str = "output"):
        self.output_dir = output_dir
        self.stats_file = os.path.join(output_dir, "statistics.json")
        self.history_file = os.path.join(output_dir, "application_history.json")
        self.daily_stats = {}
        self.session_stats = {}
        self.application_history = []
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Load existing statistics
        self._load_statistics()
    
    def _load_statistics(self):
        """Load existing statistics from file"""
        try:
            if os.path.exists(self.stats_file):
                with open(self.stats_file, 'r') as f:
                    data = json.load(f)
                    self.daily_stats = data.get('daily_stats', {})
                    self.session_stats = data.get('session_stats', {})
        except Exception as e:
            print(f"⚠️  Could not load statistics: {e}")
            self.daily_stats = {}
            self.session_stats = {}
        
        try:
            if os.path.exists(self.history_file):
                with open(self.history_file, 'r') as f:
                    self.application_history = json.load(f)
        except Exception as e:
            print(f"⚠️  Could not load application history: {e}")
            self.application_history = []
    
    def _save_statistics(self):
        """Save statistics to file"""
        try:
            data = {
                'daily_stats': self.daily_stats,
                'session_stats': self.session_stats,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.stats_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save statistics: {e}")
    
    def _save_history(self):
        """Save application history to file"""
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.application_history, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save application history: {e}")
    
    def record_application(self, job_title: str, company: str, location: str, 
                          status: str, job_url: str, timestamp: Optional[datetime] = None):
        """Record a job application"""
        if timestamp is None:
            timestamp = datetime.now()
        
        record = {
            'timestamp': timestamp.isoformat(),
            'date': timestamp.strftime('%Y-%m-%d'),
            'job_title': job_title,
            'company': company,
            'location': location,
            'status': status,  # 'success', 'failed', 'skipped'
            'job_url': job_url
        }
        
        self.application_history.append(record)
        
        # Update daily stats
        date_key = timestamp.strftime('%Y-%m-%d')
        if date_key not in self.daily_stats:
            self.daily_stats[date_key] = {
                'total_applications': 0,
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'companies': set(),
                'positions': []
            }
        
        daily = self.daily_stats[date_key]
        daily['total_applications'] += 1
        
        if status == 'success':
            daily['successful'] += 1
        elif status == 'failed':
            daily['failed'] += 1
        else:
            daily['skipped'] += 1
        
        daily['companies'].add(company)
        daily['positions'].append(job_title)
        
        # Keep only last 1000 records in memory
        if len(self.application_history) > 1000:
            self.application_history = self.application_history[-1000:]
        
        self._save_statistics()
        self._save_history()
    
    def update_session_stats(self, stats: Dict):
        """Update session statistics"""
        session_id = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.session_stats[session_id] = {
            **stats,
            'timestamp': datetime.now().isoformat()
        }
        self._save_statistics()
    
    def get_daily_summary(self, date: Optional[str] = None) -> Dict:
        """Get summary for a specific date (default: today)"""
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        if date not in self.daily_stats:
            return {
                'date': date,
                'total_applications': 0,
                'successful': 0,
                'failed': 0,
                'skipped': 0,
                'success_rate': 0.0,
                'unique_companies': 0,
                'unique_positions': 0
            }
        
        daily = self.daily_stats[date]
        total = daily['total_applications']
        successful = daily['successful']
        
        return {
            'date': date,
            'total_applications': total,
            'successful': successful,
            'failed': daily['failed'],
            'skipped': daily['skipped'],
            'success_rate': (successful / total * 100) if total > 0 else 0.0,
            'unique_companies': len(daily['companies']),
            'unique_positions': len(set(daily['positions']))
        }
    
    def get_weekly_summary(self) -> Dict:
        """Get summary for the past week"""
        today = datetime.now()
        week_data = []
        
        for i in range(7):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            summary = self.get_daily_summary(date)
            week_data.append(summary)
        
        total_apps = sum(d['total_applications'] for d in week_data)
        total_success = sum(d['successful'] for d in week_data)
        
        return {
            'period': 'last_7_days',
            'total_applications': total_apps,
            'successful': total_success,
            'failed': sum(d['failed'] for d in week_data),
            'skipped': sum(d['skipped'] for d in week_data),
            'success_rate': (total_success / total_apps * 100) if total_apps > 0 else 0.0,
            'daily_average': total_apps / 7,
            'daily_breakdown': week_data
        }
    
    def get_top_companies(self, limit: int = 10) -> List[Dict]:
        """Get top companies by application count"""
        company_counts = defaultdict(int)
        
        for record in self.application_history:
            if record['status'] == 'success':
                company_counts[record['company']] += 1
        
        sorted_companies = sorted(company_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {'company': company, 'applications': count}
            for company, count in sorted_companies[:limit]
        ]
    
    def get_top_positions(self, limit: int = 10) -> List[Dict]:
        """Get top positions by application count"""
        position_counts = defaultdict(int)
        
        for record in self.application_history:
            if record['status'] == 'success':
                position_counts[record['job_title']] += 1
        
        sorted_positions = sorted(position_counts.items(), key=lambda x: x[1], reverse=True)
        
        return [
            {'position': position, 'applications': count}
            for position, count in sorted_positions[:limit]
        ]
    
    def get_success_rate_trend(self, days: int = 30) -> List[Dict]:
        """Get success rate trend over specified days"""
        today = datetime.now()
        trend = []
        
        for i in range(days):
            date = (today - timedelta(days=i)).strftime('%Y-%m-%d')
            summary = self.get_daily_summary(date)
            trend.append({
                'date': date,
                'success_rate': summary['success_rate'],
                'total': summary['total_applications']
            })
        
        return list(reversed(trend))
    
    def export_detailed_report(self, filename: Optional[str] = None) -> str:
        """Export detailed statistics report to CSV"""
        if filename is None:
            filename = os.path.join(self.output_dir, f"detailed_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
        
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                'Date', 'Time', 'Job Title', 'Company', 'Location', 
                'Status', 'Job URL'
            ])
            
            # Data
            for record in self.application_history:
                timestamp = datetime.fromisoformat(record['timestamp'])
                writer.writerow([
                    record['date'],
                    timestamp.strftime('%H:%M:%S'),
                    record['job_title'],
                    record['company'],
                    record['location'],
                    record['status'],
                    record['job_url']
                ])
        
        return filename
    
    def print_dashboard(self):
        """Print a formatted statistics dashboard"""
        print("\n" + "=" * 70)
        print("📊 STATISTICS DASHBOARD")
        print("=" * 70)
        
        # Today's summary
        today_summary = self.get_daily_summary()
        print(f"\n📅 Today ({today_summary['date']}):")
        print(f"   Total Applications: {today_summary['total_applications']}")
        print(f"   ✅ Successful: {today_summary['successful']}")
        print(f"   ❌ Failed: {today_summary['failed']}")
        print(f"   ⏭️  Skipped: {today_summary['skipped']}")
        print(f"   📈 Success Rate: {today_summary['success_rate']:.1f}%")
        print(f"   🏢 Unique Companies: {today_summary['unique_companies']}")
        
        # Weekly summary
        weekly = self.get_weekly_summary()
        print(f"\n📊 Last 7 Days:")
        print(f"   Total Applications: {weekly['total_applications']}")
        print(f"   ✅ Successful: {weekly['successful']}")
        print(f"   📈 Success Rate: {weekly['success_rate']:.1f}%")
        print(f"   📉 Daily Average: {weekly['daily_average']:.1f}")
        
        # Top companies
        top_companies = self.get_top_companies(5)
        if top_companies:
            print(f"\n🏢 Top Companies (This Week):")
            for i, company_data in enumerate(top_companies, 1):
                print(f"   {i}. {company_data['company']}: {company_data['applications']} applications")
        
        # Top positions
        top_positions = self.get_top_positions(5)
        if top_positions:
            print(f"\n💼 Top Positions (This Week):")
            for i, position_data in enumerate(top_positions, 1):
                print(f"   {i}. {position_data['position']}: {position_data['applications']} applications")
        
        print("\n" + "=" * 70)

