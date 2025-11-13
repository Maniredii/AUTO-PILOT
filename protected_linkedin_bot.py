#!/usr/bin/env python3
"""
Protected LinkedIn Easy Apply Bot
Wraps the existing LinkedinEasyApply class with comprehensive anti-ban protection
This ensures all operations are protected from detection
"""

import asyncio
import time
import random
import json
import os
import traceback
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path

# Import existing bot and anti-ban system
from linkedineasyapply import LinkedinEasyApply
from anti_ban_system import AntiDetectionManager, BehaviorPattern
from stealth_browser_manager import StealthBrowserManager
from openrouter_client import OpenRouterClient

class ProtectedLinkedInEasyApply:
    """
    Protected wrapper around LinkedinEasyApply that adds comprehensive anti-ban protection
    All operations are automatically protected with human behavior simulation and detection avoidance
    """
    
    def __init__(self, parameters, use_stealth_browser=True):
        """
        Initialize protected bot
        
        Args:
            parameters: Configuration parameters (same as LinkedinEasyApply)
            use_stealth_browser: Whether to use stealth browser (default: True)
        """
        self.parameters = parameters
        self.use_stealth_browser = use_stealth_browser
        
        # Initialize anti-detection system
        self.anti_detection = AntiDetectionManager("anti_ban_config.json")
        self.stealth_manager = StealthBrowserManager()
        
        # Initialize OpenRouter client if enabled
        self.openrouter = None
        if parameters.get('openrouter', {}).get('enabled', False):
            api_key = parameters.get('openrouter', {}).get('api_key', '')
            if api_key:
                self.openrouter = OpenRouterClient(api_key)
                print("🤖 OpenRouter AI features: ENABLED")
            else:
                print("⚠️  OpenRouter API key not found, AI features disabled")
        else:
            print("ℹ️  OpenRouter AI features: DISABLED (set enabled: true in config to enable)")
        
        # Initialize browser (will be set by initialize_browser)
        self.browser = None
        self.bot = None
        
        # Session tracking
        self.applications_today = 0
        self.session_start_time = datetime.now()
        self.last_application_time = None
        
        # Load daily usage
        self._load_daily_usage()
        
        print("🛡️  Protected LinkedIn Bot initialized with anti-ban system")
        print(f"📊 Applications today: {self.applications_today}")
    
    def _load_daily_usage(self):
        """Load daily application count"""
        today = datetime.now().strftime("%Y-%m-%d")
        usage_file = f"daily_usage_{today}.json"
        
        try:
            if os.path.exists(usage_file):
                with open(usage_file, 'r') as f:
                    usage_data = json.load(f)
                    self.applications_today = usage_data.get('applications_count', 0)
        except Exception as e:
            print(f"⚠️  Could not load daily usage: {str(e)}")
            self.applications_today = 0
    
    def _save_daily_usage(self):
        """Save daily application count"""
        today = datetime.now().strftime("%Y-%m-%d")
        usage_file = f"daily_usage_{today}.json"
        
        usage_data = {
            'date': today,
            'applications_count': self.applications_today,
            'last_updated': datetime.now().isoformat()
        }
        
        try:
            with open(usage_file, 'w') as f:
                json.dump(usage_data, f, indent=2)
        except Exception as e:
            print(f"⚠️  Could not save daily usage: {str(e)}")
    
    def initialize_browser(self):
        """
        Initialize browser with anti-detection protection
        Returns True if successful, False otherwise
        """
        try:
            print("🔧 Initializing protected browser...")
            
            if self.use_stealth_browser:
                # Use stealth browser manager (Playwright)
                # ✅ NO user_data_dir = fresh session every time
                context, page = self.stealth_manager.create_stealth_driver(
                    session_id=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                self.browser = page
                self.browser_context = context
                print("✅ Fresh browser session created (no data persistence)")
            else:
                # Use anti-detection manager's stealth driver (if it supports Playwright)
                # For now, fallback to stealth browser
                context, page = self.stealth_manager.create_stealth_driver(
                    session_id=f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                )
                self.browser = page
                self.browser_context = context
                print("✅ Fresh browser session created (no data persistence)")
            
            # Pass OpenRouter client to LinkedinEasyApply if available
            if self.openrouter:
                self.parameters['openrouter_client'] = self.openrouter
            
            # Navigate to LinkedIn automatically
            print("🌐 Navigating to LinkedIn...")
            try:
                self.browser.goto("https://www.linkedin.com", wait_until='networkidle', timeout=30000)
                time.sleep(2)  # Give page time to load
                print("✅ LinkedIn page loaded")
            except Exception as e:
                print(f"⚠️  Navigation warning: {str(e)}")
                # Continue anyway, login will handle navigation
            
            # Create LinkedinEasyApply instance with protected browser (page)
            self.bot = LinkedinEasyApply(self.parameters, self.browser)
            
            print("✅ Protected browser initialized successfully")
            return True
            
        except Exception as e:
            print(f"❌ Failed to initialize browser: {str(e)}")
            traceback.print_exc()
            return False
    
    def protected_login(self):
        """
        Login with anti-detection measures (synchronous version)
        Wraps the original login method with protection
        """
        def _safe_page_source_lower():
            try:
                return (self.browser.content() or "").lower()
            except Exception as e:
                # If page is navigating, wait briefly and retry once
                if 'navigating' in str(e).lower() or 'changing the content' in str(e).lower():
                    time.sleep(1.0)
                    try:
                        return (self.browser.content() or "").lower()
                    except Exception:
                        return ""
                return ""

        try:
            print("🔐 Starting protected login...")
            
            # Let the original login method handle navigation and login flow
            # It knows how to navigate to login page properly
            print("📝 Attempting login...")
            try:
                self.bot.login()
            except Exception as e:
                print(f"⚠️  Login error: {e}")
                # Fallback to direct login navigation
                try:
                    self.bot.load_login_page_and_login()
                except Exception as e2:
                    print(f"⚠️  Direct login navigation failed: {e2}")
            
            # Wait for login to complete
            time.sleep(random.uniform(3, 6))
            
            # Check for security check (this handles CAPTCHA and 2FA)
            try:
                self.bot.security_check()
            except Exception as e:
                print(f"⚠️  Security check note: {str(e)}")
            
            # Wait a bit more after security check
            time.sleep(random.uniform(2, 4))
            
            # Now check for CAPTCHA or rate limiting AFTER login attempt
            current_url = self.browser.url.lower()
            page_source = _safe_page_source_lower()
            
            # Check for actual CAPTCHA (not just false positives)
            captcha_indicators = [
                '/checkpoint/challenge/' in current_url,
                'recaptcha' in page_source and 'iframe' in page_source,
                "verify you're human" in page_source or "verify you\u2019re human" in page_source,
                'security check' in page_source and 'challenge' in current_url
            ]
            
            if any(captcha_indicators):
                print("🛑 CAPTCHA or security challenge detected")
                print("⚠️  Please complete the security check in the browser")
                print("⚠️  The bot will wait for you to complete it...")
                
                # Wait for user to complete CAPTCHA (up to 5 minutes)
                max_wait = 300  # 5 minutes
                waited = 0
                while waited < max_wait:
                    time.sleep(10)
                    waited += 10
                    try:
                        current_url = self.browser.url.lower()
                        if '/checkpoint/challenge/' not in current_url:
                            if any(x in current_url for x in ['feed', 'mynetwork', 'jobs']):
                                print("✅ Security check completed!")
                                break
                    except Exception:
                        pass
                    if waited % 30 == 0:
                        print(f"⏳ Still waiting for login... ({waited}s/{max_wait}s)")
            
            # Final verification: if still not logged in, attempt a direct feed navigation
            try:
                if 'login' in current_url or 'signin' in current_url:
                    print("🔄 Attempting to open login page in new tab as fallback...")
                    self.bot._open_login_page_in_new_tab("https://www.linkedin.com/login")
            except Exception:
                pass
            
            return True
        except KeyboardInterrupt:
            raise
        except Exception as e:
            print(f"❌ Failed to login: {str(e)}")
            traceback.print_exc()
            return False
    
    
    def _check_daily_limits(self) -> bool:
        """Check if daily application limits are reached"""
        daily_limit = self.anti_detection.config.get('max_daily_applications', 50)
        
        if self.applications_today >= daily_limit:
            return True
        
        return False
    
    def protected_start_applying(self):
        """
        Start applying to jobs with full protection (synchronous version)
        Wraps the original start_applying method with session management
        """
        try:
            print("🚀 Starting protected application cycle...")
            print(f"📊 Current applications today: {self.applications_today}")
            print("🛡️  Protection active - monitoring session...")
            
            # Patch bot methods to add protection
            self._patch_bot_methods()
            
            # Call original method
            self.bot.start_applying()
            
            # Save session data
            self.anti_detection.save_session_data()
            
            print(f"\n🎉 Application cycle completed!")
            print(f"📊 Total applications today: {self.applications_today}")
            
        except KeyboardInterrupt:
            print("\n⏹️  Bot stopped by user")
            self.anti_detection.save_session_data()
        except Exception as e:
            print(f"❌ Application cycle error: {str(e)}")
            self.anti_detection.log_activity('error', {
                'type': 'cycle_error',
                'message': str(e)
            })
            traceback.print_exc()
        finally:
            self.anti_detection.save_session_data()
    
    def _patch_bot_methods(self):
        """
        Patch bot methods to add protection
        This wraps critical methods with anti-detection
        """
        # Store original method
        original_apply = self.bot.apply_to_job
        
        # Create protected wrapper (synchronous)
        def protected_apply(job_tile):
            """Protected wrapper for apply_to_job"""
            return self._sync_protected_apply(job_tile)
        
        # Replace method
        self.bot.apply_to_job = protected_apply
    
    def _sync_protected_apply(self, job_tile):
        """
        Synchronous wrapper for protected apply
        This handles the case where we're in a sync context
        """
        # Check limits
        if self._check_daily_limits():
            return False
        
        # Check for break - but don't stop, just wait a bit
        if self.anti_detection.should_take_break():
            print("⏸️  Break recommended, taking short break (30 seconds)...")
            self.anti_detection.log_activity('break_needed')
            # Take a short break instead of stopping completely
            time.sleep(30)
            print("✅ Break completed, continuing with application...")
        
        # Get delay
        if self.last_application_time:
            delay = self.anti_detection.get_application_delay()
            elapsed = (datetime.now() - self.last_application_time).total_seconds()
            if elapsed < delay:
                remaining = delay - elapsed
                print(f"⏰ Waiting {remaining/60:.1f} minutes...")
                time.sleep(remaining)
        
        # Check detection - but be less aggressive
        if self.anti_detection.detect_captcha(self.browser):
            print("⚠️  Possible CAPTCHA detected - waiting 10 seconds and continuing...")
            time.sleep(10)
            # Don't return False - let it try to continue
        
        if self.anti_detection.detect_rate_limiting(self.browser):
            print("⚠️  Possible rate limiting detected - waiting 30 seconds and continuing...")
            time.sleep(30)
            # Don't return False - let it try to continue
        
        # Add human-like delays before applying
        time.sleep(random.uniform(2, 4))
        
        # Call original method
        result = self.bot.__class__.apply_to_job(self.bot, job_tile)
        
        if result:
            self.applications_today += 1
            self.last_application_time = datetime.now()
            self._save_daily_usage()
            self.anti_detection.log_activity('application_success')
            print(f"✅ Application successful! (Total today: {self.applications_today})")
            
            # Add delay after application
            time.sleep(random.uniform(3, 6))
        else:
            self.anti_detection.log_activity('application_failed')
        
        return result
    
    def run(self):
        """
        Main entry point - runs the protected bot (synchronous)
        """
        try:
            # Initialize browser
            if not self.initialize_browser():
                print("❌ Failed to initialize browser")
                return
            
            # Login
            if not self.protected_login():
                print("❌ Failed to login")
                return
            
            # Start applying (this will use patched methods)
            self.protected_start_applying()
            
        except KeyboardInterrupt:
            print("\n⏹️  Bot stopped by user")
        except Exception as e:
            print(f"❌ Critical error: {str(e)}")
            traceback.print_exc()
        finally:
            # Cleanup
            if self.browser_context:
                try:
                    self.browser_context.close()
                except:
                    pass
            elif self.browser:
                try:
                    if hasattr(self.browser, 'close'):
                        self.browser.close()
                except:
                    pass
            self.anti_detection.save_session_data()
            print("🧹 Cleanup completed")

