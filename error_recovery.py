#!/usr/bin/env python3
"""
Enhanced Error Recovery System
Provides intelligent retry mechanisms and error handling
"""

import time
import random
from typing import Dict, List, Optional, Callable
from enum import Enum
from dataclasses import dataclass
from datetime import datetime

class ErrorType(Enum):
    """Types of errors that can occur"""
    NETWORK = "network"
    TIMEOUT = "timeout"
    ELEMENT_NOT_FOUND = "element_not_found"
    LOGIN_FAILED = "login_failed"
    CAPTCHA = "captcha"
    RATE_LIMIT = "rate_limit"
    UNKNOWN = "unknown"

@dataclass
class ErrorRecord:
    """Record of an error occurrence"""
    error_type: ErrorType
    message: str
    timestamp: datetime
    retry_count: int
    resolved: bool

class ErrorRecovery:
    """Intelligent error recovery system"""
    
    def __init__(self, max_retries: int = 3, base_delay: float = 2.0):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.error_history: List[ErrorRecord] = []
        self.error_counts: Dict[ErrorType, int] = {err_type: 0 for err_type in ErrorType}
        
    def classify_error(self, error: Exception) -> ErrorType:
        """Classify error type from exception"""
        error_str = str(error).lower()
        error_type_str = type(error).__name__.lower()
        
        if 'timeout' in error_str or 'timeout' in error_type_str:
            return ErrorType.TIMEOUT
        elif 'network' in error_str or 'connection' in error_str:
            return ErrorType.NETWORK
        elif 'not found' in error_str or 'no such element' in error_str:
            return ErrorType.ELEMENT_NOT_FOUND
        elif 'login' in error_str or 'authentication' in error_str:
            return ErrorType.LOGIN_FAILED
        elif 'captcha' in error_str:
            return ErrorType.CAPTCHA
        elif 'rate limit' in error_str or 'too many' in error_str:
            return ErrorType.RATE_LIMIT
        else:
            return ErrorType.UNKNOWN
    
    def should_retry(self, error_type: ErrorType, retry_count: int) -> bool:
        """Determine if error should be retried"""
        if retry_count >= self.max_retries:
            return False
        
        # Don't retry certain errors
        no_retry_errors = [ErrorType.CAPTCHA, ErrorType.RATE_LIMIT]
        if error_type in no_retry_errors:
            return False
        
        # Check error frequency
        recent_errors = [
            err for err in self.error_history
            if (datetime.now() - err.timestamp).seconds < 300  # Last 5 minutes
            and err.error_type == error_type
        ]
        
        if len(recent_errors) > 5:
            return False  # Too many recent errors of this type
        
        return True
    
    def get_retry_delay(self, error_type: ErrorType, retry_count: int) -> float:
        """Calculate retry delay based on error type and count"""
        # Exponential backoff with jitter
        base = self.base_delay * (2 ** retry_count)
        jitter = random.uniform(0, base * 0.3)
        
        # Adjust for error type
        multipliers = {
            ErrorType.NETWORK: 1.5,
            ErrorType.TIMEOUT: 1.2,
            ErrorType.ELEMENT_NOT_FOUND: 0.8,
            ErrorType.LOGIN_FAILED: 2.0,
            ErrorType.RATE_LIMIT: 5.0,
            ErrorType.CAPTCHA: 10.0,
            ErrorType.UNKNOWN: 1.0
        }
        
        multiplier = multipliers.get(error_type, 1.0)
        return base * multiplier + jitter
    
    def record_error(self, error: Exception, retry_count: int = 0) -> ErrorRecord:
        """Record an error occurrence"""
        error_type = self.classify_error(error)
        record = ErrorRecord(
            error_type=error_type,
            message=str(error),
            timestamp=datetime.now(),
            retry_count=retry_count,
            resolved=False
        )
        
        self.error_history.append(record)
        self.error_counts[error_type] += 1
        
        # Keep only last 100 errors
        if len(self.error_history) > 100:
            self.error_history = self.error_history[-100:]
        
        return record
    
    def retry_with_recovery(self, func: Callable, *args, **kwargs):
        """Execute function with automatic retry and recovery"""
        last_error = None
        
        for attempt in range(self.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                last_error = e
                error_type = self.classify_error(e)
                record = self.record_error(e, attempt)
                
                if not self.should_retry(error_type, attempt):
                    print(f"❌ Error not recoverable after {attempt} attempts: {str(e)}")
                    raise
                
                delay = self.get_retry_delay(error_type, attempt)
                print(f"⚠️  Error occurred (attempt {attempt + 1}/{self.max_retries + 1}): {str(e)}")
                print(f"   Retrying in {delay:.1f} seconds...")
                time.sleep(delay)
        
        # If we get here, all retries failed
        raise last_error
    
    def get_error_summary(self) -> Dict:
        """Get summary of errors"""
        recent_errors = [
            err for err in self.error_history
            if (datetime.now() - err.timestamp).seconds < 3600  # Last hour
        ]
        
        return {
            'total_errors': len(self.error_history),
            'recent_errors': len(recent_errors),
            'error_counts': {err_type.value: count for err_type, count in self.error_counts.items()},
            'most_common': max(self.error_counts.items(), key=lambda x: x[1])[0].value if self.error_counts else None
        }

