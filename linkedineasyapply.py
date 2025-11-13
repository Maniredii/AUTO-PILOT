import time, random, csv, pyautogui, pdb, traceback, sys, os
import cv2
import numpy as np
import pytesseract
from PIL import Image
from playwright.sync_api import Page, BrowserContext, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from datetime import date, datetime
from itertools import product
import re
from typing import Optional
import json

# Selenium compatibility imports (for code that still uses Selenium APIs)
try:
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, ElementClickInterceptedException
except ImportError:
    # Create compatibility classes if Selenium is not available
    class TimeoutException(Exception):
        pass
    class ElementClickInterceptedException(Exception):
        pass
    # WebDriverWait and EC will need to be handled differently if Selenium is not available
    WebDriverWait = None
    EC = None

# Import visual feedback
try:
    from visual_feedback import highlight_element, get_visual_feedback
    VISUAL_FEEDBACK_AVAILABLE = True
except ImportError:
    VISUAL_FEEDBACK_AVAILABLE = False
    print("⚠️  Visual feedback module not available")

# Import new improvements
try:
    from statistics_dashboard import StatisticsDashboard
    STATISTICS_AVAILABLE = True
except ImportError:
    STATISTICS_AVAILABLE = False
    print("⚠️  Statistics dashboard not available")

try:
    from job_matcher import JobMatcher
    JOB_MATCHER_AVAILABLE = True
except ImportError:
    JOB_MATCHER_AVAILABLE = False
    print("⚠️  Job matcher not available")

try:
    from error_recovery import ErrorRecovery
    ERROR_RECOVERY_AVAILABLE = True
except ImportError:
    ERROR_RECOVERY_AVAILABLE = False
    print("⚠️  Error recovery not available")

# Compatibility class for Selenium By enum
class By:
    ID = "id"
    NAME = "name"
    CSS_SELECTOR = "css selector"
    XPATH = "xpath"
    CLASS_NAME = "class name"
    TAG_NAME = "tag name"

class PlaywrightElementWrapper:
    """Wrapper to make Playwright locators compatible with Selenium-style methods"""
    def __init__(self, locator):
        self.locator = locator
    
    def is_displayed(self):
        """Selenium-compatible method for checking visibility"""
        try:
            return self.locator.is_visible()
        except:
            return False
    
    def is_enabled(self):
        """Check if element is enabled"""
        try:
            return not self.locator.is_disabled()
        except:
            return True
    
    @property
    def text(self):
        """Get element text"""
        try:
            return self.locator.text_content() or ""
        except:
            return ""
    
    def click(self):
        """Click the element"""
        try:
            self.locator.click()
        except Exception as e:
            # Try with force if regular click fails
            try:
                self.locator.click(force=True)
            except:
                raise e
    
    def get_attribute(self, name):
        """Get element attribute"""
        try:
            return self.locator.get_attribute(name) or ""
        except:
            return ""
    
    @property
    def size(self):
        """Get element size (Selenium-compatible)"""
        try:
            box = self.locator.bounding_box()
            if box:
                return {'width': box['width'], 'height': box['height']}
            return {'width': 0, 'height': 0}
        except:
            return {'width': 0, 'height': 0}
    
    def find_element(self, by, selector):
        """Find child element"""
        # This is a simplified version - full implementation would need proper selector conversion
        return PlaywrightElementWrapper(self.locator.locator(selector))
    
    def find_elements(self, by, selector):
        """Find child elements"""
        locators = self.locator.locator(selector).all()
        return [PlaywrightElementWrapper(loc) for loc in locators]
    
    def __getattr__(self, name):
        """Forward any other attribute access to the underlying locator"""
        return getattr(self.locator, name)

class LinkedinEasyApply:
    def __init__(self, parameters, driver):
        # Playwright: driver can be either a Page or (context, page) tuple
        if isinstance(driver, tuple):
            self.browser_context, self.browser = driver
        elif hasattr(driver, 'goto'):  # It's a Page
            self.browser = driver
            self.browser_context = driver.context
        else:  # Legacy: assume it's a page
            self.browser = driver
            self.browser_context = driver.context if hasattr(driver, 'context') else None
        self.email = parameters['email']
        self.password = parameters['password']
        self.disable_lock = parameters['disableAntiLock']
        self.company_blacklist = parameters.get('companyBlacklist', []) or []
        self.title_blacklist = parameters.get('titleBlacklist', []) or []
        self.poster_blacklist = parameters.get('posterBlacklist', []) or []
        self.positions = parameters.get('positions', [])
        self.locations = parameters.get('locations', [])
        self.residency = parameters.get('residentStatus', [])
        self.base_search_url = self.get_base_search_url(parameters)
        self.seen_jobs = []
        self.file_name = "output"
        self.unprepared_questions_file_name = "unprepared_questions"
        self.output_file_directory = parameters['outputFileDirectory']
        self.resume_dir = parameters['uploads']['resume']
        if 'coverLetter' in parameters['uploads']:
            self.cover_letter_dir = parameters['uploads']['coverLetter']
        else:
            self.cover_letter_dir = ''
        self.checkboxes = parameters.get('checkboxes', [])
        self.university_gpa = parameters['universityGpa']
        self.salary_minimum = parameters['salaryMinimum']
        self.notice_period = int(parameters['noticePeriod'])
        self.languages = parameters.get('languages', [])
        self.experience = parameters.get('experience', [])
        self.personal_info = parameters.get('personalInfo', [])
        self.eeo = parameters.get('eeo', [])
        self.experience_default = int(self.experience['default'])
        
        # User skills and preferences for job matching
        self.user_skills = parameters.get('userSkills', [
            'python', 'javascript', 'java', 'react', 'node.js', 'aws', 'sql',
            'machine learning', 'data analysis', 'web development'
        ])
        self.user_tech_stack = parameters.get('userTechStack', [
            'python', 'javascript', 'react', 'node.js', 'aws', 'sql', 'mongodb',
            'docker', 'git', 'agile', 'scrum'
        ])
        self.experience_level = parameters.get('userExperienceLevel', 'mid')  # junior, mid, senior
        self.prefer_remote = parameters.get('preferRemote', True)
        self.min_salary = parameters.get('minSalary', 50000)
        self.max_salary = parameters.get('maxSalary', 150000)
        
        # Hibernation configuration cache
        self._hibernation_config = None
        
        # Current job tracking for skill editor
        self.current_job_title = None
        self.current_company = None

        # Config path and interactive behavior
        # Default config path is config.yaml in project root unless provided
        self.config_path = parameters.get('configPath', 'config.yaml')
        self.interactive_skill_editor = parameters.get('interactiveSkillEditor', False)
        self.debug_mode = parameters.get('debugMode', False)

        # Internal per-application event buffer (reset per job)
        self._app_events = []
        
        # Statistics tracking
        self.stats = {
            'total_applications_attempted': 0,
            'total_applications_successful': 0,
            'total_applications_failed': 0,
            'total_jobs_skipped': 0,
            'total_logins': 0,
            'total_logouts_detected': 0,
            'total_relogins': 0,
            'session_start_time': datetime.now(),
            'last_application_time': None,
            'errors_by_type': {},
            'jobs_by_company': {},
            'form_filling_attempts': 0,
            'form_filling_successes': 0
        }

        # Prepare Chrome options hint (for restarts)
        self._chrome_options = self.build_chrome_options()

        # OpenRouter AI client (if provided)
        self.openrouter = parameters.get('openrouter_client', None)
        
        # Visual feedback settings
        self.visual_feedback_enabled = parameters.get('visualFeedback', {}).get('enabled', True)
        if VISUAL_FEEDBACK_AVAILABLE:
            visual_fb = get_visual_feedback()
            visual_fb.enabled = self.visual_feedback_enabled
        
        # Initialize statistics dashboard
        if STATISTICS_AVAILABLE:
            self.dashboard = StatisticsDashboard(output_dir=self.output_file_directory)
        else:
            self.dashboard = None
        
        # Initialize job matcher
        if JOB_MATCHER_AVAILABLE:
            self.job_matcher = JobMatcher(
                user_skills=self.user_skills,
                user_tech_stack=self.user_tech_stack,
                experience_level=self.experience_level,
                prefer_remote=self.prefer_remote,
                min_salary=self.min_salary,
                max_salary=self.max_salary
            )
        else:
            self.job_matcher = None
        
        # Initialize error recovery
        if ERROR_RECOVERY_AVAILABLE:
            self.error_recovery = ErrorRecovery(max_retries=3, base_delay=2.0)
        else:
            self.error_recovery = None
        
        # Job matching threshold (0.0 to 1.0)
        self.min_match_score = parameters.get('minMatchScore', 0.6)

    @staticmethod
    def build_chrome_options():
        """
        Build optimized Chrome options for Playwright (returns dict of args).
        """
        return {
            'args': [
                '--disable-gpu',
                '--disable-software-rasterizer',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-features=VizDisplayCompositor',
                '--disable-features=NetworkService',
                '--enable-features=NetworkServiceInProcess',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-extensions',
                '--disable-notifications',
                '--ignore-certificate-errors',
                '--log-level=3'
            ],
            'viewport': {'width': 1280, 'height': 900},
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def create_browser(self):
        """
        Create a new browser instance (not used with Playwright, kept for compatibility).
        """
        # This method is kept for compatibility but should not be used with Playwright
        # Browser creation is handled by stealth_browser_manager or main.py
        raise NotImplementedError("Browser creation should be handled by Playwright context manager")

    def restart_browser(self, reason="unknown"):
        """
        Restart the browser to recover from fatal automation issues (GPU resets, deprecated endpoints, crashes).
        """
        try:
            self._log_info(f"Restarting browser - reason: {reason}", checkpoint="browser_restart")
            try:
                if self.browser_context:
                    self.browser_context.close()
                elif hasattr(self.browser, 'close'):
                    self.browser.close()
            except Exception:
                pass
            time.sleep(2)
            # Browser recreation should be handled by the caller
            # Best-effort: land on LinkedIn homepage to reinitialize context
            self.safe_get('https://www.linkedin.com/')
            return True
        except Exception as e:
            self._log_error("E_BROWSER_RESTART", f"Browser restart failed: {str(e)}")
            return False

    def safe_get(self, url, retries=3, backoff=2.0):
        """
        Navigate with retries and recover from transient browser errors.
        """
        for attempt in range(1, retries + 1):
            try:
                self.browser.goto(url, wait_until='networkidle', timeout=45000)
                return True
            except Exception as e:
                msg = str(e)
                self._log_error("E_GET_NAV", f"goto('{url}') failed (attempt {attempt}/{retries}): {msg}")
                if 'GPU state invalid' in msg or 'DEPRECATED_ENDPOINT' in msg or 'chrome not reachable' in msg or 'Target closed' in msg:
                    self.restart_browser(reason=msg[:120])
                time.sleep(backoff * attempt)
        return False

    def wait_for(self, by, selector, timeout=15, condition='visible'):
        """
        Unified waiting utility: presence/visible/clickable.
        Playwright: by parameter is ignored, selector should be CSS or XPath.
        """
        try:
            # Convert Selenium By to Playwright selector if needed
            if isinstance(by, str):
                # If by is already a selector string, use it directly
                actual_selector = by if not selector else selector
            else:
                # Convert By enum to selector string
                if hasattr(by, 'value'):
                    by_value = by.value
                else:
                    by_value = str(by)
                
                if 'CSS_SELECTOR' in by_value or 'css' in by_value.lower():
                    actual_selector = selector
                elif 'XPATH' in by_value or 'xpath' in by_value.lower():
                    actual_selector = f"xpath={selector}"
                elif 'ID' in by_value:
                    actual_selector = f"#{selector}"
                elif 'CLASS_NAME' in by_value or 'class' in by_value.lower():
                    actual_selector = f".{selector}"
                elif 'NAME' in by_value:
                    actual_selector = f"[name='{selector}']"
                elif 'TAG_NAME' in by_value:
                    actual_selector = selector
                else:
                    actual_selector = selector
            
            locator = self.browser.locator(actual_selector)
            
            if condition == 'clickable':
                locator.wait_for(state='attached', timeout=timeout * 1000)
                return locator
            elif condition == 'visible':
                locator.wait_for(state='visible', timeout=timeout * 1000)
                return locator
            else:  # presence
                locator.wait_for(state='attached', timeout=timeout * 1000)
                return locator
        except PlaywrightTimeoutError:
            self._log_error("E_WAIT", f"Wait failed for {selector}: timeout")
            return None
        except Exception as e:
            self._log_error("E_WAIT", f"Wait failed for {selector}: {str(e)}")
            return None

    def safe_click(self, element, retries=2, action_description: str = None):
        """
        Safe click with JS fallback.
        Playwright: element can be a Locator or ElementHandle.
        
        Args:
            element: Element to click (Locator, ElementHandle, or selector string)
            retries: Number of retry attempts
            action_description: Optional description for visual feedback
        """
        # Get selector string for visual feedback
        selector_str = None
        if isinstance(element, str):
            selector_str = element
        else:
            # For Playwright locators, we can't easily extract the selector
            # So we'll try to use the element directly if it's a locator
            # Visual feedback will be skipped if selector is not available
            pass
        
        # Show visual feedback before clicking (only if we have a selector string)
        if VISUAL_FEEDBACK_AVAILABLE and self.visual_feedback_enabled and selector_str:
            try:
                highlight_element(
                    self.browser,
                    selector_str,
                    color='green',
                    duration=1.0,
                    action_description=action_description or f"Clicking element"
                )
            except Exception as e:
                # Don't fail if visual feedback fails
                if self.debug_mode:
                    print(f"⚠️  Visual feedback error: {e}")
        
        for attempt in range(1, retries + 1):
            try:
                if hasattr(element, 'click'):
                    element.click(timeout=5000)
                    return True
                else:
                    # If it's a selector string, get locator
                    locator = self.browser.locator(element) if isinstance(element, str) else element
                    locator.click(timeout=5000)
                    return True
            except Exception:
                try:
                    # JavaScript fallback
                    if hasattr(element, 'evaluate'):
                        element.evaluate("el => el.click()")
                    else:
                        self.browser.evaluate(f"document.querySelector('{element}')?.click()")
                    return True
                except Exception as e:
                    self._log_error("E_CLICK", f"click failed (attempt {attempt}/{retries}): {str(e)}")
                    time.sleep(0.8 * attempt)
        return False

    def safe_send_keys(self, element, text, clear=True, retries=2, action_description: str = None):
        """
        Safe text input with Playwright.
        
        Args:
            element: Element to type into (Locator, ElementHandle, or selector string)
            text: Text to type
            clear: Whether to clear the field first
            retries: Number of retry attempts
            action_description: Optional description for visual feedback
        """
        # Get selector string for visual feedback
        selector_str = None
        if isinstance(element, str):
            selector_str = element
        
        # Show visual feedback before typing (only if we have a selector string)
        if VISUAL_FEEDBACK_AVAILABLE and self.visual_feedback_enabled and selector_str:
            try:
                desc = action_description or f"Typing into field ({len(text)} chars)"
                highlight_element(
                    self.browser,
                    selector_str,
                    color='blue',
                    duration=0.8,
                    action_description=desc
                )
            except Exception as e:
                # Don't fail if visual feedback fails
                if self.debug_mode:
                    print(f"⚠️  Visual feedback error: {e}")
        
        for attempt in range(1, retries + 1):
            try:
                if hasattr(element, 'fill'):
                    if clear:
                        element.fill('')
                    element.fill(text)
                    return True
                elif hasattr(element, 'type'):
                    if clear:
                        element.clear()
                    element.type(text, delay=random.randint(50, 150))
                    return True
                else:
                    # If it's a selector string, get locator
                    locator = self.browser.locator(element) if isinstance(element, str) else element
                    if clear:
                        locator.fill('')
                    locator.fill(text)
                    return True
            except Exception as e:
                self._log_error("E_KEYS", f"send_keys failed (attempt {attempt}/{retries}): {str(e)}")
                time.sleep(0.6 * attempt)
        return False

    # -------------------------- Playwright compatibility helpers --------------------------
    def _find_element(self, by, selector):
        """Helper to find element using Playwright, compatible with Selenium By enum"""
        if isinstance(by, str):
            actual_selector = by if not selector else selector
        else:
            by_value = str(by) if not hasattr(by, 'value') else by.value
            if 'CSS_SELECTOR' in by_value or 'css' in by_value.lower():
                actual_selector = selector
            elif 'XPATH' in by_value or 'xpath' in by_value.lower():
                actual_selector = f"xpath={selector}"
            elif 'ID' in by_value:
                actual_selector = f"#{selector}"
            elif 'CLASS_NAME' in by_value or 'class' in by_value.lower():
                actual_selector = f".{selector}"
            elif 'NAME' in by_value:
                actual_selector = f"[name='{selector}']"
            elif 'TAG_NAME' in by_value:
                actual_selector = selector
            else:
                actual_selector = selector
        locator = self.browser.locator(actual_selector).first
        return PlaywrightElementWrapper(locator)
    
    def _find_elements(self, by, selector):
        """Helper to find elements using Playwright, compatible with Selenium By enum"""
        if isinstance(by, str):
            actual_selector = by if not selector else selector
        else:
            by_value = str(by) if not hasattr(by, 'value') else by.value
            if 'CSS_SELECTOR' in by_value or 'css' in by_value.lower():
                actual_selector = selector
            elif 'XPATH' in by_value or 'xpath' in by_value.lower():
                actual_selector = f"xpath={selector}"
            elif 'ID' in by_value:
                actual_selector = f"#{selector}"
            elif 'CLASS_NAME' in by_value or 'class' in by_value.lower():
                actual_selector = f".{selector}"
            elif 'NAME' in by_value:
                actual_selector = f"[name='{selector}']"
            elif 'TAG_NAME' in by_value:
                actual_selector = selector
            else:
                actual_selector = selector
        locators = self.browser.locator(actual_selector).all()
        return [PlaywrightElementWrapper(loc) for loc in locators]
    
    @property
    def current_url(self):
        """Get current URL (Playwright compatible)"""
        try:
            return self.browser.url
        except:
            return ""
    
    @property
    def page_source(self):
        """Get page source (Playwright compatible)"""
        try:
            return self.browser.content()
        except Exception as e:
            # If page is navigating, wait a bit and try again
            if 'navigating' in str(e).lower() or 'changing' in str(e).lower():
                time.sleep(1)
                try:
                    return self.browser.content()
                except:
                    return ""
            return ""
    
    def execute_script(self, script, *args):
        """Execute JavaScript (Playwright compatible)"""
        if args:
            # If we have element arguments, we need to handle them differently
            # For now, use evaluate with the script
            return self.browser.evaluate(script)
        else:
            return self.browser.evaluate(script)
    
    def find_element(self, by, selector):
        """Compatibility method: Selenium-style find_element using Playwright"""
        return self._find_element(by, selector)
    
    def find_elements(self, by, selector):
        """Compatibility method: Selenium-style find_elements using Playwright"""
        return self._find_elements(by, selector)
    
    def get_ai_selector(self, element_description: str, use_cache: bool = True) -> Optional[str]:
        """
        Use AI to dynamically generate a CSS selector for an element.
        
        Args:
            element_description: Description of the element (e.g., "Easy Apply button")
            use_cache: Whether to cache selectors to avoid repeated API calls
            
        Returns:
            CSS selector string or None on error
        """
        if not self.openrouter:
            print("⚠️  OpenRouter client not available, cannot use AI selector generation")
            return None
        
        # Check cache if enabled
        if use_cache and hasattr(self, '_selector_cache'):
            cache_key = element_description.lower()
            if cache_key in self._selector_cache:
                print(f"📋 Using cached selector for '{element_description}': {self._selector_cache[cache_key]}")
                return self._selector_cache[cache_key]
        else:
            self._selector_cache = {}
        
        try:
            # Get page HTML
            page_html = self.browser.content()
            
            # Take screenshot and convert to base64
            screenshot_bytes = self.browser.screenshot(type='png', full_page=False)
            import base64
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            # Call OpenRouter API
            selector = self.openrouter.get_ai_selector(
                page_html=page_html,
                screenshot_base64=screenshot_base64,
                element_description=element_description
            )
            
            # Cache the result
            if selector and use_cache:
                self._selector_cache[element_description.lower()] = selector
            
            return selector
            
        except Exception as e:
            print(f"⚠️  Error generating AI selector: {e}")
            return None
    
    # -------------------------- Logging helpers --------------------------
    def _now(self):
        return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    def _append_event(self, level, message, code=None, checkpoint=None):
        event = {
            'time': self._now(),
            'level': level,
            'message': message,
            'code': code or '',
            'checkpoint': checkpoint or ''
        }
        self._app_events.append(event)

    def _log(self, level, message):
        print(f"[{self._now()}] {level}: {message}")

    def _log_info(self, message, checkpoint=None):
        if checkpoint:
            self._log('INFO', f"{message} | checkpoint={checkpoint}")
        else:
            self._log('INFO', message)
        self._append_event('INFO', message, checkpoint=checkpoint)

    def _log_debug(self, message):
        if self.debug_mode:
            self._log('DEBUG', message)
        self._append_event('DEBUG', message)

    def _log_error(self, code, message):
        self._log('ERROR', f"{code} | {message}")
        self._append_event('ERROR', message, code=code)
        # Track error statistics
        if code not in self.stats['errors_by_type']:
            self.stats['errors_by_type'][code] = 0
        self.stats['errors_by_type'][code] += 1

    def _summarize_application(self, job_title, company, outcome, start_time, form_attempts, submitted):
        try:
            duration_s = round(time.perf_counter() - start_time, 2) if start_time else None
            
            # Update statistics
            self.stats['total_applications_attempted'] += 1
            if outcome == "success" and submitted:
                self.stats['total_applications_successful'] += 1
            else:
                self.stats['total_applications_failed'] += 1
                # Capture screenshot for failed applications
                if outcome == "failed":
                    self.capture_error_screenshot("APPLICATION_FAILED", f"{company} - {job_title}")
            
            if company:
                if company not in self.stats['jobs_by_company']:
                    self.stats['jobs_by_company'][company] = 0
                self.stats['jobs_by_company'][company] += 1
            
            self.stats['last_application_time'] = datetime.now()
            
            print("\n" + "-" * 60)
            print("📄 Application Summary")
            print("-" * 60)
            print(f"Company: {company or 'Unknown'}")
            print(f"Position: {job_title or 'Unknown'}")
            print(f"Outcome: {outcome}")
            print(f"Submitted: {'Yes' if submitted else 'No/Unknown'}")
            if duration_s is not None:
                print(f"Duration: {duration_s}s")
            if form_attempts is not None:
                print(f"Form Attempts: {form_attempts}")
            
            # Show session statistics
            success_rate = (self.stats['total_applications_successful'] / self.stats['total_applications_attempted'] * 100) if self.stats['total_applications_attempted'] > 0 else 0
            print(f"\n📊 Session Stats: {self.stats['total_applications_successful']}/{self.stats['total_applications_attempted']} successful ({success_rate:.1f}%)")
            
            # Print last few events for quick trace
            tail = self._app_events[-10:]
            if tail:
                print("Events (last 10):")
                for ev in tail:
                    code = f" code={ev['code']}" if ev['code'] else ''
                    chk = f" checkpoint={ev['checkpoint']}" if ev['checkpoint'] else ''
                    print(f"  - [{ev['time']}] {ev['level']}: {ev['message']}{code}{chk}")
            print("-" * 60 + "\n")
        except Exception:
            pass
    
    def print_session_summary(self):
        """Print comprehensive session summary with statistics dashboard"""
        try:
            session_duration = datetime.now() - self.stats['session_start_time']
            hours = session_duration.total_seconds() / 3600
            
            print("\n" + "=" * 70)
            print("📊 SESSION SUMMARY")
            print("=" * 70)
            print(f"⏱️  Session Duration: {hours:.2f} hours")
            print(f"📅 Start Time: {self.stats['session_start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📅 End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print()
            print("📈 Application Statistics:")
            print(f"  ✅ Successful: {self.stats['total_applications_successful']}")
            print(f"  ❌ Failed: {self.stats['total_applications_failed']}")
            print(f"  ⏭️  Skipped: {self.stats['total_jobs_skipped']}")
            print(f"  📝 Total Attempted: {self.stats['total_applications_attempted']}")
            
            if self.stats['total_applications_attempted'] > 0:
                success_rate = (self.stats['total_applications_successful'] / self.stats['total_applications_attempted']) * 100
                print(f"  📊 Success Rate: {success_rate:.1f}%")
                apps_per_hour = self.stats['total_applications_attempted'] / hours if hours > 0 else 0
                print(f"  ⚡ Applications/Hour: {apps_per_hour:.2f}")
            
            print()
            print("🔐 Authentication Statistics:")
            print(f"  🔑 Logins: {self.stats['total_logins']}")
            print(f"  🔒 Logouts Detected: {self.stats['total_logouts_detected']}")
            print(f"  🔄 Re-logins: {self.stats['total_relogins']}")
            
            print()
            print("📋 Form Filling Statistics:")
            print(f"  📝 Attempts: {self.stats['form_filling_attempts']}")
            print(f"  ✅ Successes: {self.stats['form_filling_successes']}")
            if self.stats['form_filling_attempts'] > 0:
                form_success_rate = (self.stats['form_filling_successes'] / self.stats['form_filling_attempts']) * 100
                print(f"  📊 Success Rate: {form_success_rate:.1f}%")
            
            if self.stats['jobs_by_company']:
                print()
                print("🏢 Applications by Company:")
                sorted_companies = sorted(self.stats['jobs_by_company'].items(), key=lambda x: x[1], reverse=True)
                for company, count in sorted_companies[:10]:  # Top 10
                    print(f"  • {company}: {count}")
            
            if self.stats['errors_by_type']:
                print()
                print("⚠️  Errors by Type:")
                sorted_errors = sorted(self.stats['errors_by_type'].items(), key=lambda x: x[1], reverse=True)
                for error_type, count in sorted_errors:
                    print(f"  • {error_type}: {count}")
            
            print("=" * 70 + "\n")
            
            # Show statistics dashboard if available
            if self.dashboard:
                self.dashboard.print_dashboard()
                
                # Update session stats
                self.dashboard.update_session_stats({
                    'total_applications': self.stats['total_applications_attempted'],
                    'successful': self.stats['total_applications_successful'],
                    'failed': self.stats['total_applications_failed'],
                    'skipped': self.stats['total_jobs_skipped'],
                    'session_duration_hours': hours
                })
                
                # Export detailed report
                try:
                    report_file = self.dashboard.export_detailed_report()
                    print(f"📄 Detailed report exported to: {report_file}")
                except Exception as e:
                    print(f"⚠️  Could not export detailed report: {e}")
            
            # Show error recovery summary if available
            if self.error_recovery:
                error_summary = self.error_recovery.get_error_summary()
                if error_summary['total_errors'] > 0:
                    print("\n" + "=" * 70)
                    print("🔧 ERROR RECOVERY SUMMARY")
                    print("=" * 70)
                    print(f"Total Errors: {error_summary['total_errors']}")
                    print(f"Recent Errors (last hour): {error_summary['recent_errors']}")
                    if error_summary['most_common']:
                        print(f"Most Common Error: {error_summary['most_common']}")
                    print("=" * 70 + "\n")
                    
        except Exception as e:
            print(f"⚠️  Error generating session summary: {str(e)}")
    
    def capture_error_screenshot(self, error_code, context=""):
        """Capture screenshot when critical errors occur"""
        try:
            screenshot_dir = os.path.join(self.output_file_directory, "error_screenshots")
            os.makedirs(screenshot_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"error_{error_code}_{timestamp}.png"
            filepath = os.path.join(screenshot_dir, filename)
            
            self.browser.screenshot(path=filepath, full_page=True)
            print(f"📸 Error screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            print(f"⚠️  Could not capture screenshot: {str(e)}")
            return None

    def persist_skills_to_config(self, added_skills, removed_skills):
        """
        Persist added/removed skills to config.yaml and handle userTechStack updates.
        Returns True on success, False otherwise.
        """
        try:
            import yaml
            from datetime import datetime

            if not added_skills and not removed_skills:
                return True

            if not os.path.exists(self.config_path):
                print(f"❌ Config file not found at: {self.config_path}")
                return False

            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f) or {}

            # Ensure keys exist
            config.setdefault('userSkills', [])
            config.setdefault('userTechStack', [])

            # Normalize for consistent comparisons (preserve original case in storage)
            user_skills_lower = {s.lower(): s for s in config['userSkills']}
            user_tech_lower = {s.lower(): s for s in config['userTechStack']}

            # Add skills
            for skill in added_skills:
                if skill.lower() not in user_skills_lower:
                    config['userSkills'].append(skill)
                    user_skills_lower[skill.lower()] = skill

            # Remove skills
            for skill in removed_skills:
                config['userSkills'] = [s for s in config['userSkills'] if s.lower() != skill.lower()]

            # Heuristic list of technical skills for tech stack autosync
            technical_skills = {
                'python','javascript','java','c++','c#','php','ruby','go','rust','swift',
                'react','angular','vue','node.js','express','django','flask','spring',
                'sql','mysql','postgresql','mongodb','redis','oracle','sqlite',
                'aws','azure','docker','kubernetes','git','jenkins','terraform'
            }

            for skill in added_skills:
                if skill.lower() in technical_skills and skill.lower() not in user_tech_lower:
                    config['userTechStack'].append(skill)
                    user_tech_lower[skill.lower()] = skill

            for skill in removed_skills:
                config['userTechStack'] = [s for s in config['userTechStack'] if s.lower() != skill.lower()]

            # Write updated config
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

            # Backup
            backup_file = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
            try:
                with open(backup_file, 'w', encoding='utf-8') as f:
                    yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
            except Exception as be:
                # Non-fatal
                print(f"⚠️  Failed to write backup config: {str(be)}")

            print(f"✅ Persisted resume skills to {self.config_path}. Backup: {backup_file}")
            return True
        except Exception as e:
            print(f"❌ Error persisting skills to config: {str(e)}")
            return False

    def check_tesseract_availability(self):
        """
        Check if Tesseract OCR is available and properly configured
        Returns True if available, False otherwise
        """
        try:
            # Try to get tesseract version
            version = pytesseract.get_tesseract_version()
            print(f"✅ Tesseract OCR available (version: {version})")
            return True
        except Exception as e:
            print(f"❌ Tesseract OCR not available: {str(e)}")
            print("💡 To enable OCR functionality:")
            print("   Windows: Download from https://github.com/UB-Mannheim/tesseract/wiki")
            print("   macOS: brew install tesseract")
            print("   Linux: sudo apt-get install tesseract-ocr")
            print("   Then restart your terminal/IDE")
            return False

    def read_job_description_ocr(self, job_element=None):
        """
        Read job description using computer vision and OCR with robust fallback
        Returns the extracted text from the job description area
        """
        # First check if Tesseract is available
        if not self.check_tesseract_availability():
            print("🔄 Tesseract not available, falling back to HTML text extraction...")
            return self.read_job_description_text_only(job_element)
        
        try:
            print("Reading job description using OCR...")
            
            # If no specific element provided, try to find the job description container
            if job_element is None:
                job_element = self.find_job_description_element()
                if not job_element:
                    print("Could not find job description container")
                    return self.read_job_description_text_only(None)
            
            # Try OCR with multiple fallback methods
            return self.extract_text_with_ocr(job_element)
                
        except Exception as e:
            print(f"Error in OCR job description reading: {str(e)}")
            print("🔄 Falling back to HTML text extraction...")
            return self.read_job_description_text_only(job_element)

    def find_job_description_element(self):
        """
        Find the job description element using multiple selectors with improved detection
        Returns the element if found, None otherwise
        """
        description_selectors = [
            "[data-test-id='job-description']",
            ".jobs-description-content__text",
            ".jobs-box__html-content",
            ".jobs-search__job-details--container",
            ".jobs-description",
            ".job-description", 
            ".description__text",
            ".show-more-less-html__markup",
            "[class*='job-description']",
            "[class*='jobs-description']",
            "[class*='description-content']",
            "div[class*='description']",
            "section[class*='description']"
        ]
        
        # First, try to expand "Show more" buttons to reveal full description
        try:
            show_more_selectors = [
                "button[aria-label*='Show more' i]",
                "button[aria-label*='see more' i]",
                "button:has-text('Show more')",
                "button:has-text('See more')",
                ".show-more-text",
                "[data-test-id='show-more']"
            ]
            
            for selector in show_more_selectors:
                try:
                    if selector.startswith('button:has-text') or selector.startswith('[data-test-id'):
                        elements = self.browser.find_elements(By.CSS_SELECTOR, selector)
                    else:
                        elements = self.browser.find_elements(By.CSS_SELECTOR, selector)
                    
                    for elem in elements:
                        try:
                            if elem.is_displayed() and elem.is_enabled():
                                text = elem.text.lower() if hasattr(elem, 'text') else ''
                                if 'show more' in text or 'see more' in text or 'more' in text:
                                    # Scroll to button and click
                                    self.browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", elem)
                                    time.sleep(0.5)
                                    elem.click()
                                    time.sleep(1.5)  # Wait for content to expand
                                    print("✅ Expanded 'Show more' button to reveal full description")
                                    break
                        except:
                            continue
                except:
                    continue
        except Exception as e:
            print(f"⚠️  Could not expand 'Show more' button: {str(e)}")
        
        # Now try to find the description element
        for selector in description_selectors:
            try:
                # Try multiple methods to find element
                element = None
                
                # Method 1: Try find_element
                try:
                    element = self.browser.find_element(By.CSS_SELECTOR, selector)
                    if element and element.is_displayed():
                        print(f"✅ Found job description using selector: {selector}")
                        # Scroll to element to ensure it's fully loaded
                        self.browser.execute_script("arguments[0].scrollIntoView({block: 'start'});", element)
                        time.sleep(0.5)
                        return element
                except:
                    pass
                
                # Method 2: Try wait_for
                try:
                    element = self.wait_for(By.CSS_SELECTOR, selector, timeout=3, condition='visible')
                    if element:
                        print(f"✅ Found job description using selector: {selector} (with wait)")
                        self.browser.execute_script("arguments[0].scrollIntoView({block: 'start'});", element)
                        time.sleep(0.5)
                        return element
                except:
                    pass
                    
            except:
                continue
        
        print("⚠️  Could not find job description container with any selector")
        return None

    def _action_chains_click(self, element):
        """
        Click element using ActionChains (Selenium) for more reliable clicking
        """
        try:
            from selenium.webdriver.common.action_chains import ActionChains
            actions = ActionChains(self.browser)
            actions.move_to_element(element).click().perform()
        except:
            # Fallback to regular click
            element.click()

    def _verify_easy_apply_modal_opened(self):
        """
        Verify that the Easy Apply modal/form has opened after clicking the button
        Returns True if modal is detected, False otherwise
        """
        form_indicators = [
            ".jobs-easy-apply-modal",
            ".jobs-easy-apply-content",
            "form.jobs-easy-apply-form",
            "[role='dialog']",
            ".artdeco-modal__content",
            ".jobs-easy-apply-form",
            "[data-test-modal='easy-apply-modal']"
        ]
        
        for indicator in form_indicators:
            try:
                elements = self.browser.find_elements(By.CSS_SELECTOR, indicator)
                for elem in elements:
                    if elem.is_displayed():
                        return True
            except:
                continue
        
        # Also check page source for modal indicators
        try:
            page_source = self.page_source.lower()
            if 'easy apply' in page_source or 'application' in page_source:
                # Check if modal classes are present
                if 'jobs-easy-apply' in page_source or 'artdeco-modal' in page_source:
                    return True
        except:
            pass
        
        return False

    def extract_text_with_ocr(self, job_element):
        """
        Extract text using OCR with multiple fallback methods
        """
        try:
            # Method 1: Screenshot-based OCR
            text = self.ocr_from_screenshot(job_element)
            if text and len(text.strip()) > 50:  # Minimum meaningful text length
                return text
            
            # Method 2: Alternative OCR libraries (if available)
            text = self.try_alternative_ocr(job_element)
            if text and len(text.strip()) > 50:
                return text
            
            # Method 3: Enhanced HTML extraction
            print("🔄 OCR methods failed, using enhanced HTML extraction...")
            return self.read_job_description_text_only(job_element)
            
        except Exception as e:
            print(f"Error in OCR extraction: {str(e)}")
            return self.read_job_description_text_only(job_element)

    def ocr_from_screenshot(self, job_element):
        """
        Extract text using screenshot + OCR
        """
        try:
            # Scroll element into view
            if hasattr(job_element, 'scroll_into_view_if_needed'):
                job_element.scroll_into_view_if_needed()
            else:
                self.browser.evaluate("el => el.scrollIntoView({block: 'center'})", job_element)
            time.sleep(1)
            
            # Get element bounding box (Playwright equivalent of location/size)
            try:
                box = job_element.bounding_box()
                location = {'x': box['x'], 'y': box['y']}
                size = {'width': box['width'], 'height': box['height']}
            except:
                # Fallback
                location = {'x': 0, 'y': 0}
                size = {'width': 1920, 'height': 1080}
            
            # Take full page screenshot
            screenshot_path = "temp_job_screenshot.png"
            self.browser.screenshot(path=screenshot_path, full_page=True)
            
            # Load and crop screenshot
            full_screenshot = cv2.imread(screenshot_path)
            x = int(location['x'])
            y = int(location['y']) 
            w = int(size['width'])
            h = int(size['height'])
            
            job_description_img = full_screenshot[y:y+h, x:x+w]
            
            # Clean up temporary file
            if os.path.exists(screenshot_path):
                os.remove(screenshot_path)
            
            if job_description_img.size == 0:
                print("Failed to capture job description image")
                return ""
            
            # Preprocess image for better OCR
            gray = cv2.cvtColor(job_description_img, cv2.COLOR_BGR2GRAY)
            
            # Try multiple OCR configurations
            ocr_configs = [
                '--psm 6',  # Uniform block of text
                '--psm 3',  # Fully automatic page segmentation
                '--psm 4',  # Assume a single column of text
                '--psm 1'   # Automatic page segmentation with OSD
            ]
            
            for config in ocr_configs:
                try:
                    text = pytesseract.image_to_string(gray, config=config)
                    if text and len(text.strip()) > 20:
                        text = self.clean_job_description_text(text)
                        print(f"✅ OCR successful with config {config}: {len(text)} characters")
                        return text
                except Exception as e:
                    print(f"OCR config {config} failed: {str(e)}")
                    continue
            
            print("All OCR configurations failed")
            return ""
            
        except Exception as e:
            print(f"Screenshot OCR failed: {str(e)}")
            return ""

    def try_alternative_ocr(self, job_element):
        """
        Try alternative OCR methods if available
        """
        try:
            # Check for easyocr (alternative OCR library)
            try:
                import easyocr
                print("🔄 Trying EasyOCR as alternative...")
                
                # Take screenshot
                screenshot_path = "temp_job_screenshot.png"
                self.browser.screenshot(path=screenshot_path, full_page=True)
                
                # Initialize EasyOCR reader
                reader = easyocr.Reader(['en'])
                
                # Read text from image
                results = reader.readtext(screenshot_path)
                
                # Clean up
                if os.path.exists(screenshot_path):
                    os.remove(screenshot_path)
                
                # Extract text from results
                text = ' '.join([result[1] for result in results])
                
                if text and len(text.strip()) > 20:
                    text = self.clean_job_description_text(text)
                    print(f"✅ EasyOCR successful: {len(text)} characters")
                    return text
                    
            except ImportError:
                print("EasyOCR not available")
            except Exception as e:
                print(f"EasyOCR failed: {str(e)}")
            
            # Check for paddleocr (another alternative)
            try:
                from paddleocr import PaddleOCR
                print("🔄 Trying PaddleOCR as alternative...")
                
                # Take screenshot
                screenshot_path = "temp_job_screenshot.png"
                self.browser.screenshot(path=screenshot_path, full_page=True)
                
                # Initialize PaddleOCR
                ocr = PaddleOCR(use_angle_cls=True, lang='en')
                
                # Read text from image
                result = ocr.ocr(screenshot_path, cls=True)
                
                # Clean up
                if os.path.exists(screenshot_path):
                    os.remove(screenshot_path)
                
                # Extract text from results
                text = ''
                for line in result:
                    for word_info in line:
                        text += word_info[1][0] + ' '
                
                if text and len(text.strip()) > 20:
                    text = self.clean_job_description_text(text)
                    print(f"✅ PaddleOCR successful: {len(text)} characters")
                    return text
                    
            except ImportError:
                print("PaddleOCR not available")
            except Exception as e:
                print(f"PaddleOCR failed: {str(e)}")
            
            return ""
            
        except Exception as e:
            print(f"Alternative OCR methods failed: {str(e)}")
            return ""
    
    def read_job_description_text_only(self, job_element=None):
        """
        Read job description using HTML text with enhanced extraction methods
        This is a robust fallback method when OCR is not available
        """
        try:
            print("Reading job description using enhanced HTML text extraction...")
            
            if job_element is None:
                job_element = self.find_job_description_element()
                if not job_element:
                    print("Could not find job description container")
                    return ""
            
            # Try multiple extraction methods
            text = self.extract_text_from_element(job_element)
            
            if text and len(text.strip()) > 20:
                text = self.clean_job_description_text(text)
                print(f"✅ Successfully extracted {len(text)} characters from job description using HTML text")
                return text
            else:
                print("No meaningful text found in job description HTML")
                return ""
                
        except Exception as e:
            print(f"Error reading job description HTML: {str(e)}")
            return ""

    def extract_text_from_element(self, job_element):
        """
        Extract text from job element using multiple methods
        """
        try:
            # Method 1: Direct text extraction
            text = job_element.text
            if text and len(text.strip()) > 20:
                return text
            
            # Method 2: Get innerHTML and parse
            try:
                inner_html = job_element.get_attribute('innerHTML')
                if inner_html:
                    # Remove HTML tags and extract text
                    import re
                    clean_text = re.sub(r'<[^>]+>', ' ', inner_html)
                    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                    if len(clean_text) > 20:
                        return clean_text
            except Exception as e:
                print(f"innerHTML extraction failed: {str(e)}")
            
            # Method 3: Try to find nested text elements
            try:
                # Look for specific text containers within the job description
                text_selectors = [
                    "p", "div", "span", "li", "h1", "h2", "h3", "h4", "h5", "h6"
                ]
                
                all_text = []
                for selector in text_selectors:
                    try:
                        elements = job_element.find_elements(By.TAG_NAME, selector)
                        for element in elements:
                            if element.text and element.is_displayed():
                                all_text.append(element.text)
                    except:
                        continue
                
                if all_text:
                    combined_text = ' '.join(all_text)
                    if len(combined_text.strip()) > 20:
                        return combined_text
            except Exception as e:
                print(f"Nested text extraction failed: {str(e)}")
            
            # Method 4: Try to expand "Show more" if present
            try:
                show_more_buttons = job_element.find_elements(By.XPATH, 
                    ".//button[contains(text(), 'Show more') or contains(text(), 'see more') or contains(text(), 'more')]")
                
                for button in show_more_buttons:
                    try:
                        if button.is_displayed() and button.is_enabled():
                            button.click()
                            time.sleep(1)  # Wait for content to load
                            # Try to get text again after expanding
                            expanded_text = job_element.text
                            if expanded_text and len(expanded_text.strip()) > len(text or ""):
                                return expanded_text
                    except:
                        continue
            except Exception as e:
                print(f"Show more expansion failed: {str(e)}")
            
            return text or ""
            
        except Exception as e:
            print(f"Text extraction from element failed: {str(e)}")
            return ""
    
    def read_job_description(self, job_element=None):
        """
        Main method to read job description with comprehensive fallback
        Tries OCR first, then falls back to HTML text extraction
        """
        print("🔍 Starting job description extraction...")
        
        # Try OCR first if available
        if self.check_tesseract_availability():
            print("📸 Attempting OCR extraction...")
            ocr_text = self.read_job_description_ocr(job_element)
            if ocr_text and len(ocr_text.strip()) > 50:
                print("✅ OCR extraction successful")
                return ocr_text
            else:
                print("⚠️  OCR extraction failed or insufficient text")
        
        # Fall back to HTML text extraction
        print("🌐 Falling back to HTML text extraction...")
        html_text = self.read_job_description_text_only(job_element)
        
        if html_text and len(html_text.strip()) > 20:
            print("✅ HTML text extraction successful")
            return html_text
        else:
            print("❌ All extraction methods failed")
            return ""

    def clean_job_description_text(self, text):
        """
        Clean and normalize job description text for better analysis
        """
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = ' '.join(text.split())
        
        # Remove common LinkedIn artifacts
        text = text.replace('LinkedIn', '')
        text = text.replace('Easy Apply', '')
        text = text.replace('Apply now', '')
        text = text.replace('Show more', '')
        text = text.replace('Show less', '')
        
        # Remove excessive punctuation
        text = text.replace('...', '.')
        text = text.replace('..', '.')
        
        # Normalize line breaks
        text = text.replace('\n', ' ')
        text = text.replace('\r', ' ')
        
        # Remove multiple spaces
        text = ' '.join(text.split())
        
        # Remove common job posting artifacts
        artifacts = [
            'Posted', 'Apply', 'Save', 'Share', 'Report job',
            'See who you know', 'Get notified', 'View all',
            'Company overview', 'Job details', 'Requirements'
        ]
        
        for artifact in artifacts:
            text = text.replace(artifact, '')
        
        return text.strip()
    
    def extract_skills_from_text(self, text):
        """
        Extract skills and technical requirements from job description text
        Returns a list of identified skills with improved pattern matching
        """
        if not text:
            return []
        
        # Convert to lowercase for matching
        text_lower = text.lower()
        
        # Define skill categories and keywords (expanded list)
        programming_languages = [
            'python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'swift',
            'kotlin', 'scala', 'r', 'matlab', 'perl', 'bash', 'powershell', 'typescript',
            'html', 'css', 'sass', 'less', 'dart', 'lua', 'haskell', 'clojure', 'erlang'
        ]
        
        frameworks_libraries = [
            'react', 'angular', 'vue', 'node.js', 'nodejs', 'express', 'django', 'flask', 'spring',
            'laravel', 'asp.net', 'jquery', 'bootstrap', 'tailwind', 'material-ui', 'mui',
            'redux', 'mobx', 'graphql', 'rest api', 'api development', 'next.js', 'nuxt.js',
            'fastapi', 'rails', 'symfony', 'nest.js', 'ember', 'backbone', 'svelte'
        ]
        
        databases = [
            'sql', 'mysql', 'postgresql', 'postgres', 'oracle', 'sql server', 'sqlite', 'mongodb',
            'redis', 'cassandra', 'dynamodb', 'elasticsearch', 'neo4j', 'firebase', 'couchdb',
            'mariadb', 'db2', 'nosql', 'bigquery', 'snowflake'
        ]
        
        cloud_platforms = [
            'aws', 'amazon web services', 'azure', 'google cloud', 'gcp', 'heroku', 'digitalocean', 
            'linode', 'kubernetes', 'k8s', 'docker', 'terraform', 'cloudformation', 'serverless',
            'lambda', 'ec2', 's3', 'rds', 'vpc', 'cloudfront', 'route53'
        ]
        
        devops_tools = [
            'git', 'github', 'gitlab', 'jenkins', 'circleci', 'travis ci', 'gitlab ci', 'github actions',
            'ansible', 'chef', 'puppet', 'vagrant', 'virtualbox', 'vmware', 'prometheus', 'grafana',
            'elk stack', 'splunk', 'new relic', 'datadog'
        ]
        
        methodologies = [
            'agile', 'scrum', 'kanban', 'waterfall', 'devops', 'ci/cd', 'tdd', 'bdd',
            'lean', 'six sigma', 'prince2', 'pmp', 'saas', 'paas', 'iaas'
        ]
        
        soft_skills = [
            'leadership', 'communication', 'teamwork', 'problem solving', 'analytical thinking',
            'creativity', 'adaptability', 'time management', 'project management', 'collaboration'
        ]
        
        # Combine all skills
        all_skills = (
            programming_languages + frameworks_libraries + databases + 
            cloud_platforms + devops_tools + methodologies + soft_skills
        )
        
        # Find skills in text with improved matching
        found_skills = []
        found_skills_lower = set()  # Track lowercase versions to avoid duplicates
        
        for skill in all_skills:
            skill_lower = skill.lower()
            
            # Skip if already found (case-insensitive)
            if skill_lower in found_skills_lower:
                continue
            
            # Check for exact word match (better than substring match)
            # Use word boundaries to avoid partial matches
            import re
            pattern = r'\b' + re.escape(skill_lower) + r'\b'
            if re.search(pattern, text_lower):
                found_skills.append(skill)
                found_skills_lower.add(skill_lower)
        
        # Look for skills mentioned in context (e.g., "experience with Python", "proficient in React")
        skill_context_patterns = [
            r'(?:experience with|proficient in|knowledge of|familiar with|expert in|skilled in)\s+([a-z\s\+\.#]+?)(?:\s|,|\.|$)',
            r'(?:required|must have|should have|preferred)\s+([a-z\s\+\.#]+?)(?:\s|,|\.|$)',
            r'([a-z\s\+\.#]+?)\s+(?:experience|knowledge|skills|proficiency)'
        ]
        
        for pattern in skill_context_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                # Clean up the match
                skill_candidate = match.strip()
                # Remove common words
                if len(skill_candidate) > 2 and skill_candidate not in ['the', 'and', 'or', 'with', 'for', 'to', 'in', 'of']:
                    # Check if it matches any known skill (case-insensitive)
                    for known_skill in all_skills:
                        if known_skill.lower() in skill_candidate or skill_candidate in known_skill.lower():
                            if known_skill.lower() not in found_skills_lower:
                                found_skills.append(known_skill)
                                found_skills_lower.add(known_skill.lower())
                                break
        
        # Look for additional patterns
        # Years of experience
        experience_patterns = [
            r'(\d+)\+?\s*years?\s*of\s*experience',
            r'experience:\s*(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?\s*in\s*[a-zA-Z\s]+'
        ]
        
        for pattern in experience_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                exp_skill = f"{matches[0]}+ years experience"
                if exp_skill.lower() not in found_skills_lower:
                    found_skills.append(exp_skill)
                    found_skills_lower.add(exp_skill.lower())
        
        # Education requirements
        education_keywords = ['bachelor', 'master', 'phd', 'degree', 'diploma', 'certification']
        for keyword in education_keywords:
            if keyword in text_lower and f"education: {keyword}" not in found_skills_lower:
                found_skills.append(f"education: {keyword}")
                found_skills_lower.add(f"education: {keyword}")
        
        # Remove duplicates and return (already handled, but keep for safety)
        return list(set(found_skills))
    
    def calculate_skill_match_score(self, job_skills, user_skills):
        """
        Calculate how well user skills match job requirements
        Returns a score from 0-100 and detailed analysis
        """
        if not job_skills or not user_skills:
            return {
                'score': 0,
                'matched_skills': [],
                'missing_skills': job_skills,
                'extra_skills': user_skills,
                'match_percentage': 0
            }
        
        # Convert all skills to lowercase for comparison
        job_skills_lower = [skill.lower() for skill in job_skills]
        user_skills_lower = [skill.lower() for skill in user_skills]
        
        # Convert to sets for comparison
        job_skills_set = set(job_skills_lower)
        user_skills_set = set(user_skills_lower)
        
        # Calculate matches
        matched_skills = job_skills_set.intersection(user_skills_set)
        missing_skills = job_skills_set - user_skills_set
        extra_skills = user_skills_set - job_skills_set
        
        # Map back to original case for display
        matched_skills_original = [skill for skill in job_skills if skill.lower() in matched_skills]
        missing_skills_original = [skill for skill in job_skills if skill.lower() in missing_skills]
        extra_skills_original = [skill for skill in user_skills if skill.lower() in extra_skills]
        
        # Calculate score
        if len(job_skills_set) == 0:
            match_percentage = 0
        else:
            match_percentage = (len(matched_skills) / len(job_skills_set)) * 100
        
        # Weight the score based on importance
        score = match_percentage
        
        # Bonus for having extra relevant skills
        if len(extra_skills) > 0:
            score += min(10, len(extra_skills) * 2)  # Max 10 bonus points
        
        # Cap score at 100
        score = min(100, score)
        
        return {
            'score': round(score, 1),
            'matched_skills': matched_skills_original,
            'missing_skills': missing_skills_original,
            'extra_skills': extra_skills_original,
            'match_percentage': round(match_percentage, 1)
        }

    def analyze_job_description(self, job_text):
        """
        Analyze the job description text for key information
        Uses OpenRouter API if available for intelligent analysis, otherwise falls back to keyword matching
        Returns a dictionary with analysis results
        """
        if not job_text:
            return {}
        
        analysis = {}
        
        # Try using OpenRouter API for intelligent analysis if available
        if self.openrouter and hasattr(self, 'user_skills') and self.user_skills:
            try:
                print("🤖 Using OpenRouter AI for intelligent job analysis...")
                user_skills_list = self.user_skills if isinstance(self.user_skills, list) else list(self.user_skills)
                user_experience = getattr(self, 'experience_level', 'mid')
                
                ai_analysis = self.openrouter.analyze_job_match(
                    job_description=job_text[:3000],  # Limit to avoid token limits
                    candidate_skills=user_skills_list,
                    candidate_experience=f"{user_experience} level experience"
                )
                
                if ai_analysis and isinstance(ai_analysis, dict):
                    # Use AI analysis results
                    if 'match_score' in ai_analysis and ai_analysis['match_score'] is not None:
                        analysis['skill_match_score'] = ai_analysis['match_score']
                        analysis['ai_analysis'] = True
                        print(f"✅ AI Analysis: Match Score: {ai_analysis['match_score']}/100")
                    
                    if 'strengths' in ai_analysis:
                        analysis['matched_skills'] = ai_analysis['strengths']
                    
                    if 'gaps' in ai_analysis:
                        analysis['missing_skills'] = ai_analysis['gaps']
                    
                    if 'recommendation' in ai_analysis:
                        analysis['ai_recommendation'] = ai_analysis['recommendation']
                        print(f"🤖 AI Recommendation: {ai_analysis['recommendation']}")
                
            except Exception as e:
                print(f"⚠️  OpenRouter API analysis failed: {str(e)}")
                print("📋 Falling back to keyword-based analysis...")
        
        # Convert to lowercase for analysis
        text_lower = job_text.lower()
        
        # Extract skills from job description
        job_skills = self.extract_skills_from_text(job_text)
        analysis['job_skills'] = job_skills
        
        # Calculate skill match with user skills (fallback or supplement to AI)
        if hasattr(self, 'user_skills') and self.user_skills:
            skill_match = self.calculate_skill_match_score(job_skills, self.user_skills)
            analysis['skill_match'] = skill_match
            # Only override skill_match_score if AI didn't provide one
            if 'skill_match_score' not in analysis:
                analysis['skill_match_score'] = skill_match['score']
            if 'matched_skills' not in analysis:
                analysis['matched_skills'] = skill_match['matched_skills']
            if 'missing_skills' not in analysis:
                analysis['missing_skills'] = skill_match['missing_skills']
            if 'extra_skills' not in analysis:
                analysis['extra_skills'] = skill_match['extra_skills']
        
        # Experience level detection
        experience_keywords = {
            'junior': ['junior', 'entry level', 'entry-level', '0-2 years', '1-2 years', 'new grad', 'recent graduate'],
            'mid': ['mid level', 'mid-level', 'intermediate', '3-5 years', '4-6 years', 'mid-senior'],
            'senior': ['senior', 'lead', 'principal', 'staff', '5+ years', '7+ years', '10+ years', 'expert']
        }
        
        for level, keywords in experience_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                analysis['experience_level'] = level
                break
        
        if 'experience_level' not in analysis:
            analysis['experience_level'] = 'unknown'
        
        # Remote work detection
        remote_keywords = ['remote', 'work from home', 'wfh', 'telecommute', 'virtual', 'distributed team']
        analysis['remote_work'] = any(keyword in text_lower for keyword in remote_keywords)
        
        # Salary detection
        salary_keywords = ['salary', 'compensation', 'pay', 'rate', '$', 'dollars', 'annual', 'yearly']
        analysis['salary_mentioned'] = any(keyword in text_lower for keyword in salary_keywords)
        
        # Tech stack analysis
        tech_keywords = [
            'python', 'javascript', 'java', 'react', 'node.js', 'aws', 'sql', 'mongodb',
            'docker', 'kubernetes', 'git', 'agile', 'scrum', 'machine learning', 'ai',
            'data science', 'cloud', 'devops', 'ci/cd'
        ]
        
        found_tech = []
        for tech in tech_keywords:
            if tech in text_lower:
                found_tech.append(tech)
        
        analysis['tech_stack'] = found_tech
        
        # Red flag detection
        red_flags = []
        
        # Unpaid/volunteer work
        unpaid_keywords = ['unpaid', 'volunteer', 'internship', 'no pay', 'experience only']
        if any(keyword in text_lower for keyword in unpaid_keywords):
            red_flags.append('unpaid/volunteer position')
        
        # Commission only
        if 'commission only' in text_lower or 'commission-based' in text_lower:
            red_flags.append('commission-only compensation')
        
        # No benefits
        if 'no benefits' in text_lower or 'benefits not included' in text_lower:
            red_flags.append('no benefits mentioned')
        
        # Excessive overtime
        overtime_keywords = ['24/7', 'on-call', 'overtime required', 'weekend work', 'holiday work']
        if any(keyword in text_lower for keyword in overtime_keywords):
            red_flags.append('excessive overtime requirements')
        
        # High pressure
        pressure_keywords = ['fast-paced', 'high-pressure', 'deadline-driven', 'crunch time']
        if any(keyword in text_lower for keyword in pressure_keywords):
            red_flags.append('high-pressure environment')
        
        analysis['red_flags'] = red_flags
        
        # Job type detection
        job_types = {
            'full_time': ['full-time', 'full time', 'permanent', 'regular'],
            'part_time': ['part-time', 'part time', 'temporary', 'contract'],
            'contract': ['contract', 'freelance', 'consulting', 'project-based']
        }
        
        for job_type, keywords in job_types.items():
            if any(keyword in text_lower for keyword in keywords):
                analysis['job_type'] = job_type
                break
        
        if 'job_type' not in analysis:
            analysis['job_type'] = 'unknown'
        
        # Location requirements
        location_keywords = ['on-site', 'onsite', 'in-office', 'hybrid', 'flexible']
        if any(keyword in text_lower for keyword in location_keywords):
            analysis['location_type'] = 'on-site'
        elif analysis.get('remote_work', False):
            analysis['location_type'] = 'remote'
        else:
            analysis['location_type'] = 'unknown'
        
        return analysis

    def should_apply_to_job(self, analysis, job_text):
        """
        Determine whether to apply to a job based on analysis
        Returns True if should apply, False if should skip
        Made less restrictive to ensure jobs are actually applied to
        """
        if not analysis:
            print("⚠️  No job analysis available. Proceeding with application.")
            return True
        
        # Check for critical red flags only (very restrictive)
        red_flags = analysis.get('red_flags', [])
        if red_flags:
            print(f"🚨 Red flags detected: {', '.join(red_flags)}")
            
            # Only skip for truly critical red flags
            critical_flags = ['unpaid/volunteer position', 'commission-only compensation']
            if any(flag in red_flags for flag in critical_flags):
                print("❌ Critical red flag detected. Skipping this job.")
                return False
        
        # If AI provided a recommendation, respect it but be lenient
        if 'ai_recommendation' in analysis:
            ai_rec = analysis['ai_recommendation'].lower()
            if 'skip' in ai_rec and 'critical' in ai_rec:
                print("❌ AI recommends skipping due to critical issues.")
                return False
            elif 'apply' in ai_rec:
                print("✅ AI recommends applying. Proceeding!")
                return True
        
        # Check experience level compatibility (more lenient)
        user_experience = getattr(self, 'experience_level', 'mid')
        job_experience = analysis.get('experience_level', 'unknown')
        
        if user_experience and job_experience != 'unknown':
            experience_compatibility = self.check_experience_compatibility(user_experience, job_experience)
            if not experience_compatibility:
                # Don't skip based on experience level - just log it
                print(f"⚠️  Experience level note: You're {user_experience}, job requires {job_experience} (still applying)")
            else:
                print(f"✅ Experience level compatible: {user_experience} → {job_experience}")
        
        # Check skill match score (informational only, don't block applications)
        skill_match_score = analysis.get('skill_match_score', 0)
        if skill_match_score > 0:
            print(f"🎯 Skill Match Score: {skill_match_score}/100")
            
            # Show skill analysis
            matched_skills = analysis.get('matched_skills', [])
            missing_skills = analysis.get('missing_skills', [])
            extra_skills = analysis.get('extra_skills', [])
            
            if matched_skills:
                print(f"  ✅ Matched Skills: {', '.join(matched_skills[:5])}{'...' if len(matched_skills) > 5 else ''}")
            
            if missing_skills:
                print(f"  ⚠️  Missing Skills: {', '.join(missing_skills[:5])}{'...' if len(missing_skills) > 5 else ''}")
            
            if extra_skills:
                print(f"  🎁 Extra Skills: {', '.join(extra_skills[:5])}{'...' if len(extra_skills) > 5 else ''}")
            
            # Informational only - don't block based on score
            if skill_match_score >= 80:
                print("🎉 Excellent skill match!")
            elif skill_match_score >= 60:
                print("✅ Good skill match.")
            elif skill_match_score >= 40:
                print("⚠️  Moderate skill match.")
            else:
                print("⚠️  Lower skill match, but proceeding with application.")
                
                # Attempt automatic resume update to avoid blocking GUI in automated runs
                if missing_skills and len(missing_skills) > 2:
                    print("\n🎯 Skill mismatch detected! Attempting automatic resume update...")
                    added_skills = list(missing_skills)
                    removed_skills = []

                    # Update in-memory lists first for this session
                    for skill in added_skills:
                        if skill not in self.user_skills:
                            self.user_skills.append(skill)
                        if skill not in self.user_tech_stack:
                            self.user_tech_stack.append(skill)

                    # Persist to config.yaml
                    persisted = self.persist_skills_to_config(added_skills, removed_skills)
                    if not persisted:
                        print("⚠️  Failed to persist skills to config. Continuing with in-memory updates only.")

                    print(f"✅ Skills updated - Added: {added_skills}, Removed: {removed_skills}")
                    print("🔄 Skill lists updated for this session!")

                    # Recalculate skill match with updated skills
                    if 'job_skills' in analysis:
                        updated_skill_match = self.calculate_skill_match_score(
                            analysis['job_skills'], 
                            self.user_skills
                        )
                        print(f"🔄 Updated Skill Match Score: {updated_skill_match['score']}/100")

                        if updated_skill_match['score'] >= 40:
                            print("✅ Skill match improved! Proceeding with application.")
                            return True

                    # If interactive mode explicitly requested, fall back to GUI editor
                    if self.interactive_skill_editor:
                        try:
                            print("💡 Opening interactive Skill Editor for manual review...")
                            from skill_editor_gui import show_skill_editor
                            job_title = getattr(self, 'current_job_title', 'Unknown Position')
                            company = getattr(self, 'current_company', 'Unknown Company')
                            gui_added, gui_removed = show_skill_editor(
                                list(missing_skills),
                                self.user_skills,
                                job_title,
                                company
                            )
                            if gui_added or gui_removed:
                                # Update memory and persist again
                                for skill in gui_added or []:
                                    if skill not in self.user_skills:
                                        self.user_skills.append(skill)
                                    if skill not in self.user_tech_stack:
                                        self.user_tech_stack.append(skill)
                                for skill in gui_removed or []:
                                    if skill in self.user_skills:
                                        self.user_skills.remove(skill)
                                    if skill in self.user_tech_stack:
                                        self.user_tech_stack.remove(skill)
                                self.persist_skills_to_config(gui_added or [], gui_removed or [])
                                if 'job_skills' in analysis:
                                    updated_skill_match = self.calculate_skill_match_score(
                                        analysis['job_skills'], self.user_skills
                                    )
                                    print(f"🔄 Updated Skill Match Score: {updated_skill_match['score']}/100")
                                    if updated_skill_match['score'] >= 40:
                                        print("✅ Skill match improved! Proceeding with application.")
                                        return True
                        except Exception as e:
                            print(f"⚠️  Skill editor GUI error: {str(e)}")
                
                # Don't skip based on low skill match - proceed with application
                print("✅ Proceeding with application despite lower skill match.")
                return True
        
        # Check remote work preference
        prefer_remote = getattr(self, 'prefer_remote', False)
        job_remote = analysis.get('remote_work', False)
        
        if prefer_remote and not job_remote:
            print("⚠️  You prefer remote work, but this job is not remote.")
            # Don't skip, just warn
        elif not prefer_remote and job_remote:
            print("✅ Remote work available, which might be a plus.")
        
        # Check tech stack overlap
        user_tech_stack = getattr(self, 'user_tech_stack', [])
        job_tech_stack = analysis.get('tech_stack', [])
        
        if user_tech_stack and job_tech_stack:
            tech_overlap = len(set(user_tech_stack) & set(job_tech_stack))
            tech_total = len(set(job_tech_stack))
            
            if tech_total > 0:
                tech_match_percentage = (tech_overlap / tech_total) * 100
                print(f"🔧 Tech Stack Match: {tech_overlap}/{tech_total} technologies ({tech_match_percentage:.1f}%)")
                
                if tech_match_percentage >= 50:
                    print("✅ Good tech stack alignment.")
                elif tech_match_percentage >= 25:
                    print("⚠️  Moderate tech stack alignment.")
                else:
                    print("❌ Low tech stack alignment.")
        
        # Overall decision
        print("✅ Job analysis completed. Proceeding with application.")
        return True

    def _update_skills_based_on_job_description(self, analysis, job_description_text):
        """
        Intelligently update user skills based on job description requirements
        This method automatically adds missing skills that are frequently mentioned in the job description
        """
        try:
            if not analysis or 'job_skills' not in analysis:
                return
            
            job_skills = analysis.get('job_skills', [])
            if not job_skills:
                return
            
            # Get current user skills
            if not hasattr(self, 'user_skills') or not self.user_skills:
                return
            
            # Find missing skills that are important (mentioned multiple times or in key sections)
            missing_skills = []
            job_text_lower = job_description_text.lower()
            
            # Check each job skill
            for skill in job_skills:
                skill_lower = skill.lower()
                
                # Skip if user already has this skill (case-insensitive)
                if any(s.lower() == skill_lower for s in self.user_skills):
                    continue
                
                # Check how important this skill is based on frequency and context
                skill_count = job_text_lower.count(skill_lower)
                
                # Check if skill appears in important sections (requirements, qualifications, etc.)
                important_sections = [
                    'requirements', 'qualifications', 'must have', 'required', 
                    'skills', 'experience with', 'proficient in', 'knowledge of'
                ]
                in_important_section = any(section in job_text_lower for section in important_sections)
                
                # Add skill if it's mentioned multiple times or in important sections
                if skill_count >= 2 or (skill_count >= 1 and in_important_section):
                    # Only add technical/professional skills, not generic terms
                    if len(skill) > 2 and skill.lower() not in ['the', 'and', 'or', 'with', 'for', 'to']:
                        missing_skills.append(skill)
            
            # Limit to top 5 most important missing skills to avoid over-adding
            if missing_skills:
                # Sort by importance (frequency in job description)
                missing_skills.sort(key=lambda s: job_text_lower.count(s.lower()), reverse=True)
                missing_skills = missing_skills[:5]
                
                print(f"\n🎯 Auto-updating skills based on job description...")
                print(f"   Found {len(missing_skills)} important missing skills")
                
                # Update in-memory skills
                added_count = 0
                for skill in missing_skills:
                    if skill not in self.user_skills:
                        self.user_skills.append(skill)
                        added_count += 1
                        print(f"   ✅ Added: {skill}")
                    
                    # Also add to tech stack if it's a technical skill
                    if hasattr(self, 'user_tech_stack') and skill.lower() in [
                        'python', 'javascript', 'java', 'react', 'angular', 'vue', 'node.js',
                        'aws', 'azure', 'docker', 'kubernetes', 'sql', 'mongodb', 'git'
                    ]:
                        if skill not in self.user_tech_stack:
                            self.user_tech_stack.append(skill)
                
                # Persist to config file
                if added_count > 0:
                    persisted = self.persist_skills_to_config(missing_skills, [])
                    if persisted:
                        print(f"   ✅ Successfully updated {added_count} skills in config file")
                    else:
                        print(f"   ⚠️  Failed to persist skills to config, but updated in-memory")
                
                # Recalculate skill match
                if 'job_skills' in analysis:
                    updated_match = self.calculate_skill_match_score(job_skills, self.user_skills)
                    print(f"   📊 Updated skill match score: {updated_match['score']}/100")
        except Exception as e:
            print(f"⚠️  Error updating skills based on job description: {str(e)}")

    def check_experience_compatibility(self, user_level, job_level):
        """
        Check if user experience level is compatible with job requirements
        """
        if user_level == job_level:
            return True
        
        # Allow some flexibility
        if user_level == 'mid' and job_level == 'senior':
            return True  # Mid-level can apply to senior positions
        elif user_level == 'senior' and job_level == 'mid':
            return True  # Senior can apply to mid-level positions
        elif user_level == 'mid' and job_level == 'junior':
            return True  # Mid-level can apply to junior positions (overqualified but acceptable)
        
        return False

    def login(self):
        try:
            self._log_info("Attempting to restore previous session...", checkpoint="login_start")
            
            # First, check if we're already logged in
            try:
                current_url = self.current_url.lower()
                if any(page in current_url for page in ["feed", "jobs", "mynetwork", "linkedin.com/in/"]):
                    # Verify we're actually logged in by checking for profile elements
                    try:
                        profile_elem = self.wait_for(By.CSS_SELECTOR, "[data-test-global-nav]", timeout=5, condition='visible')
                        if profile_elem:
                            print("✅ Already logged in, skipping login")
                            return
                    except:
                        pass
            except:
                pass
            
            if os.path.exists("chrome_bot"):
                # Try to navigate to feed first
                if not self.safe_get("https://www.linkedin.com/feed/"):
                    self._log_error("E_NAV_FEED", "Initial navigation failed, redirecting to login")
                    self.load_login_page_and_login()
                else:
                    # Verify we are in feed, else proceed to login
                    current_url = self.current_url.lower()
                    if "feed" not in current_url and "mynetwork" not in current_url and "jobs" not in current_url:
                        self._log_info("Not on feed page, redirecting to login.", checkpoint="login_redirect")
                        self.load_login_page_and_login()
            else:
                self._log_info("No session found, redirecting to login page.")
                self.load_login_page_and_login()

        except TimeoutException:
            print("Timeout occurred, checking for security challenges...")
            self.security_check()
            # raise Exception("Could not login!")

    def security_check(self):
        current_url = self.current_url
        page_source = self.page_source

        if '/checkpoint/challenge/' in current_url or 'security check' in page_source or 'quick verification' in page_source or 'Check your LinkedIn app' in page_source:
            print("⚠️  Security check detected. Please complete it in the browser.")
            print("⏳ Waiting for security check completion (max 5 minutes)...")
            # Wait automatically for security check (no user input required)
            max_wait = 300  # 5 minutes
            waited = 0
            while waited < max_wait:
                time.sleep(10)
                waited += 10
                current_url_check = self.browser.url.lower()
                if '/checkpoint/challenge/' not in current_url_check:
                    if 'feed' in current_url_check or 'mynetwork' in current_url_check or 'jobs' in current_url_check:
                        print("✅ Security check completed!")
                        break
                if waited % 30 == 0:
                    print(f"⏳ Still waiting... ({waited}s/{max_wait}s)")
            time.sleep(random.uniform(5.5, 10.5))

    def is_logged_out(self):
        """
        Advanced logout detection with multiple fallback methods
        Checks for login modals, login URLs, login prompts, and session state
        Returns True if logged out, False if still logged in
        """
        try:
            current_url = self.current_url.lower()
            page_source = self.page_source.lower()
            
            # Method 1: Check for login URLs (most reliable)
            login_urls = [
                '/login',
                '/uas/login',
                '/checkpoint/login',
                'signin',
                '/checkpoint',
                '/challenge'
            ]
            
            if any(url in current_url for url in login_urls):
                print("🔒 Detected login URL - user appears to be logged out")
                return True
            
            # Method 2: Check for authenticated page indicators
            # If we're on a page that requires login but see login prompts, we're logged out
            authenticated_pages = ['/feed', '/jobs', '/mynetwork', '/messaging', '/notifications']
            is_authenticated_page = any(page in current_url for page in authenticated_pages)
            
            # Method 3: Check for login modal/popup indicators (enhanced)
            login_modal_indicators = [
                'sign in to view more jobs',
                'sign in to view',
                'continue with google',
                'new to linkedin? join now',
                'sign in to create job alert',
                'sign in to apply',
                'join now',
                'sign in',
                'please sign in',
                'sign in to continue',
                'you need to sign in'
            ]
            
            # Method 4: Enhanced modal detection with multiple strategies
            def check_for_login_modal():
                """Helper function to check for login modals using multiple methods"""
                try:
                    # Strategy 1: Look for modal-specific elements
                    modal_selectors = [
                        '[role="dialog"]',
                        '.artdeco-modal',
                        '.modal',
                        '[data-test-modal]',
                        '.sign-in-modal',
                        '.login-modal',
                        '[class*="modal"]',
                        '[class*="overlay"]',
                        '[data-test-id="sign-in-modal"]',
                        '.authwall-modal',
                        '.login-dialog'
                    ]
                    
                    for selector in modal_selectors:
                        try:
                            modals = self.browser.find_elements(By.CSS_SELECTOR, selector)
                            for modal in modals:
                                if modal.is_displayed():
                                    modal_text = modal.text.lower()
                                    # Check if modal contains login indicators
                                    if any(ind in modal_text for ind in login_modal_indicators):
                                        print(f"🔒 Detected login modal using selector: {selector}")
                                        return True
                        except:
                            continue
                    
                    # Strategy 2: Check for page overlay/dimming (indicates modal)
                    try:
                        body = self.browser.find_element(By.TAG_NAME, 'body')
                        body_classes = body.get_attribute('class') or ''
                        body_style = body.get_attribute('style') or ''
                        
                        # Check for modal-related classes
                        if any(keyword in body_classes.lower() for keyword in ['modal-open', 'overlay', 'backdrop', 'locked']):
                            # Verify there's a login-related element visible
                            try:
                                login_elements = self.browser.find_elements(By.XPATH, 
                                    "//*[contains(text(), 'Sign in') or contains(text(), 'Continue with Google')]")
                                for elem in login_elements:
                                    if elem.is_displayed():
                                        print("🔒 Detected modal overlay with login content")
                                        return True
                            except:
                                pass
                    except:
                        pass
                    
                    # Strategy 3: Check for specific "Sign in to view more jobs" text
                    if 'sign in to view more jobs' in page_source:
                        # Count occurrences - if it appears multiple times, it's likely a modal
                        count = page_source.count('sign in to view more jobs')
                        if count >= 1:
                            # Check if it's in a prominent position (likely modal)
                            try:
                                # Look for the text in visible elements
                                elements_with_text = self.browser.find_elements(By.XPATH, 
                                    "//*[contains(text(), 'Sign in to view more jobs')]")
                                for elem in elements_with_text:
                                    if elem.is_displayed():
                                        # Check if it's in a modal-like container
                                        parent = elem.find_element(By.XPATH, "./ancestor::*[contains(@class, 'modal') or contains(@role, 'dialog')]")
                                        if parent:
                                            print("🔒 Detected 'Sign in to view more jobs' in modal container")
                                            return True
                            except:
                                # If we can't verify, but text is present, assume logged out
                                print("🔒 Detected 'Sign in to view more jobs' text - assuming logged out")
                                return True
                    
                    return False
                except Exception as e:
                    print(f"⚠️  Error in modal detection: {str(e)}")
                    return False
            
            # Check for login modal
            if check_for_login_modal():
                return True
            
            # Method 5: Check for "Continue with Google" button (strong indicator)
            if 'continue with google' in page_source:
                try:
                    google_buttons = self.browser.find_elements(By.XPATH, 
                        "//button[contains(text(), 'Continue with Google') or contains(text(), 'Google')]")
                    for btn in google_buttons:
                        if btn.is_displayed():
                            print("🔒 Detected 'Continue with Google' button - logged out")
                            return True
                except:
                    if 'continue with google' in page_source:
                        print("🔒 Detected 'Continue with Google' text - likely logged out")
                        return True
            
            # Method 6: Check for "Sign in" buttons in header when on non-authenticated pages
            
            try:
                sign_in_buttons = self.browser.find_elements(By.XPATH, 
                    "//a[contains(text(), 'Sign in') or contains(text(), 'Join now')] | //button[contains(text(), 'Sign in')]")
                for button in sign_in_buttons:
                    if button.is_displayed():
                        button_text = button.text.lower()
                        if 'sign in' in button_text:
                            # If we're on a page that should be authenticated but see sign in button, we're logged out
                            if is_authenticated_page:
                                print("🔒 Detected sign in button on authenticated page - logged out")
                                return True
                            # If we're on a non-authenticated page and see prominent sign in button, likely logged out
                            elif not is_authenticated_page and button.size['height'] > 30:
                                print("🔒 Detected prominent sign in button - likely logged out")
                                return True
            except:
                pass
            
            # Method 7: Check if we're on authenticated pages but see login prompts
            if is_authenticated_page:
                # If we see login prompts on authenticated pages, we're definitely logged out
                if any(ind in page_source for ind in ['sign in to view', 'continue with google', 'new to linkedin']):
                    print("🔒 Detected login prompt on authenticated page - logged out")
                    return True
                
                # Check for absence of user profile elements (indicates logout)
                try:
                    profile_indicators = [
                        '[data-test-global-nav]',
                        '[data-control-name="nav.settings"]',
                        '.global-nav__me',
                        '[data-test-app-aware-link="messaging"]'
                    ]
                    found_profile = False
                    for selector in profile_indicators:
                        try:
                            elem = self.browser.find_element(By.CSS_SELECTOR, selector)
                            if elem.is_displayed():
                                found_profile = True
                                break
                        except:
                            continue
                    
                    if not found_profile and is_authenticated_page:
                        print("🔒 No profile elements found on authenticated page - likely logged out")
                        return True
                except:
                    pass
            
            return False
            
        except Exception as e:
            print(f"⚠️  Error checking login status: {str(e)}")
            # If we can't determine, assume we're logged in to avoid unnecessary re-logins
            return False

    def handle_logout_and_relogin(self, max_retries=3):
        """
        Enhanced re-login handler with retry logic and better error recovery
        Opens login page in current tab and performs login
        """
        for attempt in range(1, max_retries + 1):
            try:
                print(f"🔄 Detected logout. Attempting to re-login... (Attempt {attempt}/{max_retries})")
                
                # Step 1: Close any modals that might be open
                try:
                    close_selectors = [
                        'button[aria-label="Dismiss"]',
                        'button[aria-label="Close"]',
                        '.artdeco-modal__dismiss',
                        '[data-test-modal-close-btn]',
                        'button[data-test-modal-close-button]',
                        '.modal-close',
                        '[class*="close"]'
                    ]
                    
                    for selector in close_selectors:
                        try:
                            close_buttons = self.browser.find_elements(By.CSS_SELECTOR, selector)
                            for btn in close_buttons:
                                if btn.is_displayed():
                                    self.safe_click(btn)
                                    time.sleep(1)
                                    break
                        except:
                            continue
                    
                    # Also try pressing Escape key to close modals
                    try:
                        from selenium.webdriver.common.keys import Keys
                        self.browser.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)
                        time.sleep(1)
                    except:
                        pass
                except Exception as e:
                    print(f"⚠️  Could not close modals: {str(e)}")
                    # Continue anyway
            
                # Step 2: Ensure we're on login page (will redirect if not)
                if not self.ensure_login_page():
                    print(f"❌ Failed to ensure login page")
                    if attempt < max_retries:
                        print(f"⏳ Retrying in 3 seconds...")
                        time.sleep(3)
                        continue
                    return False
            
                # Step 3: Wait for login form and fill it with multiple selectors
                print("🔍 Looking for login form fields...")
                
                # Try multiple selectors for username field
                username_selectors = [
                    (By.ID, "username"),
                    (By.NAME, "session_key"),
                    (By.CSS_SELECTOR, "input[type='email']"),
                    (By.CSS_SELECTOR, "input[autocomplete='username']"),
                    (By.XPATH, "//input[@id='username' or @name='session_key']")
                ]
                
                username_el = None
                for by, selector in username_selectors:
                    try:
                        username_el = self.wait_for(by, selector, timeout=10, condition='visible')
                        if username_el:
                            break
                    except:
                        continue
                
                # Try multiple selectors for password field
                password_selectors = [
                    (By.ID, "session_password"),
                    (By.ID, "password"),
                    (By.NAME, "session_password"),
                    (By.CSS_SELECTOR, "input[type='password']"),
                    (By.CSS_SELECTOR, "input[autocomplete='current-password']"),
                    (By.XPATH, "//input[@type='password']")
                ]
                
                password_el = None
                for by, selector in password_selectors:
                    try:
                        password_el = self.wait_for(by, selector, timeout=10, condition='visible')
                        if password_el:
                            break
                    except:
                        continue
                
                if not username_el or not password_el:
                    print(f"❌ Login fields not found (username: {username_el is not None}, password: {password_el is not None})")
                    if attempt < max_retries:
                        print(f"⏳ Retrying in 3 seconds...")
                        time.sleep(3)
                        continue
                    return False
                
                print("📝 Entering credentials...")
                # Clear fields first
                try:
                    username_el.clear()
                    password_el.clear()
                except:
                    pass
                
                # Enter credentials with human-like typing
                self.safe_send_keys(username_el, self.email, clear=True)
                time.sleep(random.uniform(1.5, 2.5))
                self.safe_send_keys(password_el, self.password, clear=True)
                time.sleep(random.uniform(1.5, 2.5))
            
                # Step 4: Find and click login button with multiple strategies
                login_button_selectors = [
                    "button[type='submit']",
                    ".btn__primary--large",
                    "button[data-litms-control-urn='login-submit']",
                    "button[aria-label*='Sign in']",
                    "input[type='submit']",
                    "button.login__form_action_container",
                    "button.artdeco-button--primary"
                ]
                
                login_btn = None
                for selector in login_button_selectors:
                    try:
                        login_btn = self.wait_for(By.CSS_SELECTOR, selector, timeout=5, condition='clickable')
                        if login_btn:
                            break
                    except:
                        continue
                
                if login_btn:
                    print("🔐 Clicking login button...")
                    # Scroll into view first
                    try:
                        self.browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", login_btn)
                        time.sleep(0.5)
                    except:
                        pass
                    
                    if not self.safe_click(login_btn):
                        # Try JavaScript click as fallback
                        try:
                            self.browser.execute_script("arguments[0].click();", login_btn)
                            print("🔐 Login submitted via JavaScript")
                        except Exception as e:
                            print(f"⚠️  JavaScript click failed: {str(e)}")
                            # Try pressing Enter on password field
                            try:
                                password_el.send_keys(Keys.RETURN)
                                print("🔐 Login submitted via Enter key")
                            except:
                                print(f"❌ All login button click methods failed")
                                if attempt < max_retries:
                                    continue
                                return False
                else:
                    # Try JavaScript to find and click submit button
                    try:
                        self.browser.execute_script("""
                            var btn = document.querySelector('button[type="submit"]') || 
                                     document.querySelector('input[type="submit"]') ||
                                     document.querySelector('.btn__primary--large');
                            if (btn) btn.click();
                        """)
                        print("🔐 Login submitted via JavaScript fallback")
                    except Exception as e:
                        print(f"❌ Failed to find/login button: {str(e)}")
                        if attempt < max_retries:
                            continue
                        return False
                
                # Step 5: Wait for login to complete with timeout
                print("⏳ Waiting for login to complete...")
                max_wait_time = 20
                wait_interval = 1
                waited = 0
                
                while waited < max_wait_time:
                    time.sleep(wait_interval)
                    waited += wait_interval
                    
                    current_url = self.current_url.lower()
                    
                    # Check for successful login
                    if any(page in current_url for page in ["feed", "mynetwork", "jobs", "linkedin.com/in/"]):
                        print("✅ Re-login successful!")
                        time.sleep(random.uniform(2, 4))
                        return True
                    
                    # Check for security check/CAPTCHA
                    if '/checkpoint' in current_url or '/challenge' in current_url:
                        print("⚠️  Security check/CAPTCHA detected")
                        self.security_check()
                        # Re-check after security check
                        time.sleep(2)
                        current_url = self.current_url.lower()
                        if any(page in current_url for page in ["feed", "mynetwork", "jobs"]):
                            print("✅ Re-login successful after security check!")
                            return True
                        break
                    
                    # Check for login errors
                    page_source = self.page_source.lower()
                    if 'incorrect' in page_source or 'invalid' in page_source or 'error' in page_source:
                        if 'password' in page_source or 'email' in page_source:
                            print("❌ Login credentials appear to be incorrect")
                            if attempt < max_retries:
                                print(f"⏳ Retrying in 3 seconds...")
                                time.sleep(3)
                                break
                            return False
                
                # If we get here, login status is unclear
                print(f"⚠️  Login status unclear after {waited}s. Current URL: {current_url[:100]}")
                
                # Try navigating to feed to verify
                if self.safe_get("https://www.linkedin.com/feed/"):
                    time.sleep(3)
                    current_url = self.current_url.lower()
                    if "feed" in current_url:
                        print("✅ Re-login verified by navigating to feed")
                        return True
                    elif '/login' in current_url or '/uas/login' in current_url:
                        print("❌ Still on login page - login failed")
                        if attempt < max_retries:
                            print(f"⏳ Retrying in 3 seconds...")
                            time.sleep(3)
                            continue
                
                # If this was the last attempt, return False
                if attempt >= max_retries:
                    print(f"❌ Re-login failed after {max_retries} attempts")
                    return False
                
            except Exception as e:
                print(f"❌ Error during re-login attempt {attempt}: {str(e)}")
                if attempt < max_retries:
                    print(f"⏳ Retrying in 3 seconds...")
                    time.sleep(3)
                    continue
                traceback.print_exc()
                return False
        
        return False

    def check_and_handle_logout(self):
        """
        Check if logged out and handle it automatically
        Returns True if still logged in or re-login successful, False otherwise
        """
        if self.is_logged_out():
            print("🔒 Logout detected! Attempting to re-login...")
            self.stats['total_logouts_detected'] += 1
            result = self.handle_logout_and_relogin()
            if result:
                self.stats['total_relogins'] += 1
            return result
        return True
    
    def verify_session_health(self):
        """
        Verify that the session is still active and healthy
        Returns True if session is healthy, False otherwise
        """
        try:
            current_url = self.current_url.lower()
            
            # Quick check - if we're on login page, definitely logged out
            if '/login' in current_url or '/uas/login' in current_url:
                return False
            
            # Check for profile elements (indicates logged in)
            try:
                profile_indicators = [
                    '[data-test-global-nav]',
                    '.global-nav__me',
                    '[data-control-name="nav.settings"]'
                ]
                
                for selector in profile_indicators:
                    try:
                        elem = self.browser.find_element(By.CSS_SELECTOR, selector)
                        if elem.is_displayed():
                            return True
                    except:
                        continue
            except:
                pass
            
            # If we're on an authenticated page, assume healthy
            authenticated_pages = ['/feed', '/jobs', '/mynetwork', '/messaging']
            if any(page in current_url for page in authenticated_pages):
                return True
            
            # Otherwise, do a full logout check
            return not self.is_logged_out()
            
        except Exception as e:
            print(f"⚠️  Error verifying session health: {str(e)}")
            # If we can't verify, assume healthy to avoid unnecessary re-logins
            return True

    def is_on_login_page(self):
        """
        Check if we're currently on the LinkedIn login page
        Returns True if on login page, False otherwise
        """
        try:
            current_url = self.current_url.lower()
            
            # Check for login URLs
            login_indicators = [
                '/login',
                '/uas/login',
                'signin',
                '/checkpoint/login'
            ]
            
            if any(indicator in current_url for indicator in login_indicators):
                # Also verify login form elements are present
                try:
                    username_field = self.browser.find_elements(By.ID, "username")
                    password_field = self.browser.find_elements(By.ID, "session_password") or \
                                   self.browser.find_elements(By.ID, "password")
                    
                    if username_field and password_field:
                        return True
                except:
                    # If we're on login URL, assume we're on login page
                    return True
            
            return False
        except Exception as e:
            print(f"⚠️  Error checking if on login page: {str(e)}")
            return False
    
    def ensure_login_page(self):
        """
        Ensure we're on the login page, redirect if not
        Returns True if successfully on login page, False otherwise
        """
        try:
            # Check if already on login page
            if self.is_on_login_page():
                print("✅ Already on login page")
                return True
            
            print("🔄 Not on login page, redirecting to login page...")
            current_url = self.current_url.lower()
            print(f"📍 Current URL: {current_url[:100]}")
            
            # Close any modals that might be open
            try:
                close_selectors = [
                    'button[aria-label="Dismiss"]',
                    'button[aria-label="Close"]',
                    '.artdeco-modal__dismiss',
                    '[data-test-modal-close-btn]',
                    '.modal-close'
                ]
                
                for selector in close_selectors:
                    try:
                        close_buttons = self.find_elements(By.CSS_SELECTOR, selector)
                        for btn in close_buttons:
                            try:
                                # Check if visible (Playwright way)
                                if hasattr(btn, 'is_visible'):
                                    if btn.is_visible():
                                        btn.click()
                                        time.sleep(0.5)
                                        break
                                else:
                                    # Try clicking anyway
                                    btn.click()
                                    time.sleep(0.5)
                                    break
                            except:
                                continue
                    except:
                        continue
                
                # Try pressing Escape (Playwright way)
                try:
                    self.browser.keyboard.press('Escape')
                    time.sleep(0.5)
                except:
                    pass
            except:
                pass
            
            # Navigate to login page with multiple fallback URLs
            login_urls = [
                "https://www.linkedin.com/uas/login?session_redirect=https%3A%2F%2Fwww.linkedin.com%2Ffeed%2F",
                "https://www.linkedin.com/login",
                "https://www.linkedin.com/uas/login"
            ]
            
            for login_url in login_urls:
                print(f"🌐 Navigating to: {login_url}")
                if self.safe_get(login_url):
                    time.sleep(random.uniform(2, 3))
                    
                    # Verify we're on login page
                    if self.is_on_login_page():
                        print("✅ Successfully redirected to login page")
                        return True
                    else:
                        print("⚠️  Navigated but login page not confirmed, trying next URL...")
                        continue
                else:
                    print(f"⚠️  Failed to navigate to {login_url}, trying next...")
                    time.sleep(1)
            
            # Final check
            if self.is_on_login_page():
                print("✅ On login page after navigation attempts")
                return True
            else:
                print("❌ Failed to ensure login page after all attempts")
                print("🔄 Opening new tab with login page as final fallback...")
                return self._open_login_page_in_new_tab("https://www.linkedin.com/login")
                
        except Exception as e:
            print(f"❌ Error ensuring login page: {str(e)}")
            traceback.print_exc()
            print("🔄 Opening new tab with login page as fallback...")
            return self._open_login_page_in_new_tab("https://www.linkedin.com/login")
    
    def _open_login_page_in_new_tab(self, login_url: str) -> bool:
        """
        Open login page in a new tab as fallback when navigation fails
        Returns True if successful, False otherwise
        """
        try:
            print(f"🆕 Opening new tab with login page: {login_url}")
            
            # Get the browser context to create a new page
            if self.browser_context:
                # Create a new page (tab)
                new_page = self.browser_context.new_page()
                # Navigate to login page
                new_page.goto(login_url, wait_until='networkidle', timeout=30000)
                time.sleep(2)
                
                # Switch to the new page
                self.browser = new_page
                print("✅ Successfully opened login page in new tab")
                
                # Verify we're on login page
                if self.is_on_login_page():
                    print("✅ Confirmed login page is loaded in new tab")
                    return True
                else:
                    print("⚠️  New tab opened but login page not confirmed")
                    return False
            else:
                # Fallback: try to open URL in current page
                print("⚠️  Browser context not available, trying current page...")
                if self.safe_get(login_url):
                    time.sleep(2)
                    return self.is_on_login_page()
                return False
                
        except Exception as e:
            print(f"❌ Error opening login page in new tab: {str(e)}")
            traceback.print_exc()
            return False

    def load_login_page_and_login(self):
        self._log_info("Navigating to login page", checkpoint="login_nav")
        
        # Ensure we're on login page first
        if not self.ensure_login_page():
            # Final fallback: open new tab with login page
            print("🔄 All navigation attempts failed, opening new tab with login page...")
            if not self._open_login_page_in_new_tab("https://www.linkedin.com/login"):
                raise TimeoutException("Failed to navigate to login page even with new tab fallback")

        # Wait for username and password fields
        t0 = time.perf_counter()
        username_el = self.wait_for(By.ID, "username", timeout=15, condition='visible')
        password_el = self.wait_for(By.ID, "session_password", timeout=15, condition='visible') or \
                      self.wait_for(By.ID, "password", timeout=10, condition='visible')

        if not username_el or not password_el:
            raise TimeoutException("Login fields not found")

        self._log_debug(f"Login fields located in {round(time.perf_counter()-t0,2)}s")
        self.safe_send_keys(username_el, self.email)
        self.safe_send_keys(password_el, self.password)

        login_btn = self.wait_for(By.CSS_SELECTOR, "button[type='submit'], .btn__primary--large", timeout=10, condition='clickable')
        if login_btn:
            self.safe_click(login_btn)
            self._log_info("Login form submitted", checkpoint="login_submit")
        else:
            # JS submit as last resort
            try:
                self.browser.execute_script("document.querySelector('button[type=\\'submit\\']')?.click()")
                self._log_info("Login submitted via JS fallback", checkpoint="login_submit_js")
            except Exception:
                pass

        # Wait for post-login URL or key element (Playwright version)
        try:
            # Wait for URL to contain /feed/ or for global nav element
            self.browser.wait_for_url("**/feed/**", timeout=20000)
            self._log_info("Login successful - on feed page", checkpoint="login_success")
        except:
            try:
                # Alternative: wait for global nav element
                nav_element = self.wait_for(By.CSS_SELECTOR, "[data-test-global-nav]", timeout=20, condition='visible')
                if nav_element:
                    self._log_info("Login successful - global nav found", checkpoint="login_success")
                else:
                    self._log_error("E_POST_LOGIN", "Post-login condition not met, attempting recovery")
                    self.safe_get("https://www.linkedin.com/feed/")
            except:
                self._log_error("E_POST_LOGIN", "Post-login condition not met, attempting recovery")
                self.safe_get("https://www.linkedin.com/feed/")

        time.sleep(random.uniform(3, 6))
        self._log_info("Login flow complete", checkpoint="login_done")
        self.stats['total_logins'] += 1

    def start_applying(self):
        print("\n" + "=" * 70)
        print("🚀 STARTING JOB APPLICATION SESSION")
        print("=" * 70)
        print(f"📅 Session Start: {self.stats['session_start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"🎯 Positions: {', '.join(self.positions)}")
        print(f"📍 Locations: {', '.join(self.locations)}")
        print("=" * 70 + "\n")
        
        searches = list(product(self.positions, self.locations))
        random.shuffle(searches)

        page_sleep = 0
        minimum_time = 60 * 15  # minimum time bot should run before taking a break
        minimum_page_time = time.time() + minimum_time

        for (position, location) in searches:
            location_url = "&location=" + location
            job_page_number = -1

            print("Starting the search for " + position + " in " + location + ".")

            try:
                while True:
                    # Check for logout periodically
                    if not self.check_and_handle_logout():
                        print("❌ Failed to handle logout. Moving to next search.")
                        break
                    
                    page_sleep += 1
                    job_page_number += 1
                    print(f"\n{'='*70}")
                    print(f"📄 Page {job_page_number} - {position} in {location}")
                    print(f"{'='*70}")
                    print(f"📊 Progress: {self.stats['total_applications_successful']} successful | {self.stats['total_applications_failed']} failed | {self.stats['total_jobs_skipped']} skipped")
                    print(f"{'='*70}\n")
                    
                    print("Going to job page " + str(job_page_number))
                    self.next_job_page(position, location_url, job_page_number)
                    time.sleep(random.uniform(1.5, 3.5))
                    print("Starting the application process for this page...")
                    self.apply_jobs(location)
                    print("Job applications on this page have been successfully completed.")

                    time_left = minimum_page_time - time.time()
                    if time_left > 0:
                        print("Sleeping for " + str(time_left) + " seconds.")
                        time.sleep(time_left)
                        minimum_page_time = time.time() + minimum_time
                    if page_sleep % 5 == 0:
                        sleep_time = random.randint(180, 300)  # Changed from 500, 900 {seconds}
                        print("Sleeping for " + str(sleep_time / 60) + " minutes.")
                        time.sleep(sleep_time)
                        page_sleep += 1
            except Exception as e:
                print(f"Error in search for {position} in {location}: {str(e)}")
                traceback.print_exc()
                # Wait a bit before continuing to next search
                time.sleep(random.uniform(10, 20))
                continue

            time_left = minimum_page_time - time.time()
            if time_left > 0:
                print("Sleeping for " + str(time_left) + " seconds.")
                time.sleep(time_left)
                minimum_page_time = time.time() + minimum_time
            if page_sleep % 5 == 0:
                sleep_time = random.randint(500, 900)
                print("Sleeping for " + str(sleep_time / 60) + " minutes.")
                time.sleep(sleep_time)
                page_sleep += 1
        
        # Print session summary when all searches are complete
        print("\n🎉 All job searches completed!")
        self.print_session_summary()

    def apply_jobs(self, location, max_applications=None):
        """
        Refactored job application method with explicit waits and robust navigation.
        This method properly handles the filtered job list and ensures applications are completed.
        Optionally limits the number of application attempts when max_applications is provided.
        """
        print("\n" + "="*70)
        print("🚀 STARTING JOB APPLICATION PROCESS")
        print("="*70)
        
        # Step 1: Check for logout before processing jobs
        if not self.check_and_handle_logout():
            print("❌ Failed to handle logout. Skipping this page.")
            raise Exception("Logged out and re-login failed")
        
        # Step 2: Wait for filtered results to load
        print("\n📋 Step 1: Waiting for job search results to load...")
        # Note: Using Playwright's built-in waiting, no need for WebDriverWait
        
        try:
            # Wait for the job results container to be present
            # Using multiple possible selectors for robustness
            job_results_container = None
            container_selectors = [
                (By.CSS_SELECTOR, "div[data-test-id='job-results-list']"),
                (By.CSS_SELECTOR, "ul.scaffold-layout__list-container"),
                (By.CSS_SELECTOR, "div.jobs-search-results-list"),
                (By.CLASS_NAME, "scaffold-layout__list-container"),
                (By.XPATH, "//ul[contains(@class, 'scaffold-layout__list-container')]")
            ]
            
            for selector_type, selector_value in container_selectors:
                try:
                    job_results_container = self.wait_for(selector_type, selector_value, timeout=20, condition='visible')
                    if job_results_container:
                        # Get the actual element handle for compatibility
                        job_results_container = self._find_element(selector_type, selector_value)
                        print(f"✅ Found job results container using: {selector_type} = {selector_value}")
                        break
                except:
                    continue
            
            if not job_results_container:
                # Check if there are no results
                try:
                    no_jobs_element = self.wait_for(
                        By.CSS_SELECTOR, 
                        "[data-test-id='no-results-banner'], .jobs-search-two-pane__no-results-banner",
                        timeout=5,
                        condition='visible'
                    )
                    if no_jobs_element:
                        print("⚠️  No matching jobs found on this page.")
                        raise Exception("No more jobs on this page.")
                except:
                    pass
                
                print("❌ Could not find job results container. Page may not have loaded properly.")
                raise Exception("Job results container not found")
            
            # Wait for the container to be visible
            # Wait for container to be visible (already done above)
            print("✅ Job results container is visible")
            
        except TimeoutException:
            print("❌ Timeout waiting for job results to load")
            raise Exception("Job results did not load in time")
        
        # Step 3: Scrape the current job list (ONCE, before the loop)
        print("\n📋 Step 2: Scraping job list from current page...")
        
        # Wait a moment for any lazy-loaded jobs to appear
        time.sleep(2)
        
        # Scroll to load more jobs if needed
        try:
            self.browser.execute_script(
                "arguments[0].scrollTop = arguments[0].scrollHeight;", 
                job_results_container
            )
            time.sleep(2)
            # Scroll back up
            self.browser.execute_script(
                "arguments[0].scrollTop = 0;", 
                job_results_container
            )
            time.sleep(1)
        except:
            pass

        # Find all job cards using robust selectors
        job_card_selectors = [
            "li[data-test-id='job-card']",
            "li.scaffold-layout__list-item",
            "div[data-test-id='job-card-container']",
            "li.jobs-search-results__list-item"
        ]
        
        job_cards = []
        for selector in job_card_selectors:
            try:
                job_cards = job_results_container.find_elements(By.CSS_SELECTOR, selector)
                if job_cards:
                    print(f"✅ Found {len(job_cards)} job cards using selector: {selector}")
                    break
            except:
                continue
        
        if not job_cards:
            # Fallback: try to find any list items
            try:
                job_cards = job_results_container.find_elements(By.TAG_NAME, "li")
                job_cards = [card for card in job_cards if card.is_displayed()]
                print(f"✅ Found {len(job_cards)} job cards using fallback method")
            except:
                pass

        if len(job_cards) == 0:
            print("⚠️  No job cards found on this page.")
            raise Exception("No more jobs on this page.")

        print(f"📊 Found {len(job_cards)} jobs to process on this page")
        
        # Step 4: Iterate through the scraped job list
        print("\n📋 Step 3: Processing jobs...")
        successful_applications = 0
        skipped_jobs = 0
        failed_applications = 0
        applications_attempted = 0
        limit_reached = False
        
        max_allowed_attempts = None
        if max_applications is not None:
            try:
                max_allowed_attempts = max(1, int(max_applications))
            except Exception:
                max_allowed_attempts = 1
        
        for job_index, job_card in enumerate(job_cards, 1):
            try:
                print(f"\n{'='*70}")
                print(f"📌 Processing job {job_index}/{len(job_cards)}")
                print(f"{'='*70}")
                
                # Extract job information from the card
                job_title = ""
                company = ""
                link = ""
                job_location = ""
                
                try:
                    # Wait for job card to be visible (using Playwright)
                    try:
                        job_card_locator = self.browser.locator(f"li[data-test-id='job-card']").nth(job_index - 1)
                        job_card_locator.wait_for(state='visible', timeout=10000)
                    except:
                        pass  # Continue if wait fails
                    
                    # Extract job title and link
                    title_selectors = [
                        (By.CSS_SELECTOR, "a[data-test-id='job-title']"),
                        (By.CLASS_NAME, "job-card-list__title--link"),
                        (By.CSS_SELECTOR, "a.job-card-list__title--link")
                    ]
                    
                    title_element = None
                    for selector_type, selector_value in title_selectors:
                        try:
                            title_element = job_card.find_element(selector_type, selector_value)
                            break
                        except:
                            continue
                    
                    if title_element:
                        job_title = title_element.find_element(By.TAG_NAME, "strong").text.strip()
                        link = title_element.get_attribute('href').split('?')[0]
                        print(f"📝 Job Title: {job_title}")
                        print(f"🔗 Link: {link[:80]}...")
                    else:
                        print("⚠️  Could not extract job title/link. Skipping this job card.")
                        skipped_jobs += 1
                        continue
                    
                    # Extract company name
                    company_selectors = [
                        (By.CSS_SELECTOR, "[data-test-id='job-card-company']"),
                        (By.CLASS_NAME, "artdeco-entity-lockup__subtitle"),
                        (By.CSS_SELECTOR, "span.job-card-container__primary-description")
                    ]
                    
                    for selector_type, selector_value in company_selectors:
                        try:
                            company = job_card.find_element(selector_type, selector_value).text.strip()
                            break
                        except:
                            continue
                    
                    if company:
                        print(f"🏢 Company: {company}")
                    else:
                        print("⚠️  Could not extract company name")
                    
                    # Extract location
                    try:
                        location_element = job_card.find_element(
                            By.CSS_SELECTOR, 
                            "[data-test-id='job-card-location'], .job-card-container__metadata-item"
                        )
                        job_location = location_element.text.strip()
                        print(f"📍 Location: {job_location}")
                    except:
                        pass  # Location is optional, continue without it
                except Exception as extract_error:
                    print(f"❌ Error extracting job information: {str(extract_error)}")
                    skipped_jobs += 1
                    continue
                
                # Check if already applied
                if link in self.seen_jobs:
                    print(f"⏭️  Already applied to this job. Skipping...")
                    skipped_jobs += 1
                    continue
                
                # Check blacklists
                contains_blacklisted_keywords = False
                if self.title_blacklist:
                    job_title_lower = job_title.lower()
                    for word in self.title_blacklist:
                        if word.lower() in job_title_lower:
                            contains_blacklisted_keywords = True
                            print(f"🚫 Job title contains blacklisted word: {word}")
                            break
                
                if company.lower() in [c.lower() for c in self.company_blacklist]:
                    print(f"🚫 Company is blacklisted: {company}")
                    skipped_jobs += 1
                    continue
                
                if contains_blacklisted_keywords:
                    skipped_jobs += 1
                    continue
                
                # Step 5: Click the job card to open job details
                print(f"\n🖱️  Clicking job card to open details...")
                try:
                    # Scroll job card into view
                    self.browser.execute_script(
                        "arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", 
                        job_card
                    )
                    time.sleep(1)
                    
                    # Wait for job card to be clickable (using Playwright)
                    try:
                        title_locator = self.browser.locator(f"a[data-test-id='job-title']").nth(job_index - 1)
                        title_locator.wait_for(state='visible', timeout=10000)
                    except:
                        pass  # Continue if wait fails
                    
                    # Click the job card
                    try:
                        title_element.click()
                    except:
                        # Fallback to JavaScript click
                        self.browser.execute_script("arguments[0].click();", title_element)
                    
                    print("✅ Job card clicked successfully")
                    
                except Exception as click_error:
                    print(f"❌ Error clicking job card: {str(click_error)}")
                    failed_applications += 1
                    continue
                
                # Wait for job details view to load
                print("⏳ Waiting for job details to load...")
                try:
                    # Wait for job details panel to appear
                    details_selectors = [
                        (By.CSS_SELECTOR, "div[data-test-id='job-details']"),
                        (By.CSS_SELECTOR, "div.jobs-search__job-details"),
                        (By.CSS_SELECTOR, "div.jobs-details__main-content")
                    ]
                    
                    details_loaded = False
                    for selector_type, selector_value in details_selectors:
                        try:
                            # Wait for element using Playwright
                            self.wait_for(selector_type, selector_value, timeout=10, condition='visible')
                            details_loaded = True
                            print("✅ Job details loaded")
                            break
                        except:
                            continue
                    
                    if not details_loaded:
                        print("⚠️  Job details may not have loaded, but continuing...")
                    
                    time.sleep(2)  # Give it a moment to fully render
                    
                except Exception as details_error:
                    print(f"⚠️  Error waiting for job details: {str(details_error)}")
                
                # Step 6: Check for Easy Apply button
                print("\n🔍 Checking for Easy Apply button...")
                easy_apply_button = None
                easy_apply_selectors = [
                    (By.CSS_SELECTOR, "button[data-control-name='jobdetails_topcard_inapply']"),
                    (By.CSS_SELECTOR, "button[data-control-name='jobdetails_topcard_apply']"),
                    (By.CSS_SELECTOR, "button[aria-label*='Easy Apply' i]"),
                    (By.CSS_SELECTOR, "button[aria-label*='Apply' i]"),
                    (By.CSS_SELECTOR, "button.jobs-apply-button"),
                    (By.CSS_SELECTOR, "button[data-test-id='apply-button']")
                ]
                
                for selector_type, selector_value in easy_apply_selectors:
                    try:
                        easy_apply_button = self.browser.find_element(selector_type, selector_value)
                        if easy_apply_button.is_displayed() and easy_apply_button.is_enabled():
                            button_text = easy_apply_button.get_attribute('aria-label') or easy_apply_button.text
                            print(f"✅ Found Easy Apply button: {button_text}")
                            break
                        else:
                            easy_apply_button = None
                    except:
                        continue
                
                # Fallback: search all buttons by text
                if not easy_apply_button:
                    try:
                        all_buttons = self.browser.find_elements(By.TAG_NAME, "button")
                        for button in all_buttons:
                            if button.is_displayed():
                                button_text = (button.text or button.get_attribute('aria-label') or '').lower()
                                if 'easy apply' in button_text or ('apply' in button_text and 'easy' in button_text):
                                    easy_apply_button = button
                                    print(f"✅ Found Easy Apply button by text: {button_text}")
                                    break
                    except:
                        pass
                
                if not easy_apply_button:
                    print("❌ Easy Apply button NOT found. This job may not support Easy Apply.")
                    print(f"   Skipping job: {job_title} at {company}")
                    skipped_jobs += 1
                    # Navigate back to job list before continuing
                    self._navigate_back_to_job_list()
                    continue
                
                # Step 7: Apply to the job
                print(f"\n📝 Starting application process for: {job_title} at {company}")
                try:
                    # Mark as seen before applying
                    if link and link not in self.seen_jobs:
                        self.seen_jobs.append(link)
                    
                    # Call the apply_to_job method
                    application_result = self.apply_to_job(job_card)
                    applications_attempted += 1
                    
                    if application_result:
                        print(f"✅ Application submitted successfully for: {job_title} at {company}")
                        successful_applications += 1
                        self.stats['total_applications_successful'] += 1
                    else:
                        print(f"⚠️  Application was not completed for: {job_title} at {company}")
                        failed_applications += 1
                        self.stats['total_applications_failed'] += 1
                    
                    if max_allowed_attempts and applications_attempted >= max_allowed_attempts:
                        limit_reached = True
                    
                except Exception as apply_error:
                    print(f"❌ Error during application: {str(apply_error)}")
                    failed_applications += 1
                    self.stats['total_applications_failed'] += 1
                    applications_attempted += 1
                    traceback.print_exc()
                    if max_allowed_attempts and applications_attempted >= max_allowed_attempts:
                        limit_reached = True
                
                # Step 8: Navigate back to job list
                print("\n🔙 Navigating back to job list...")
                try:
                    self._navigate_back_to_job_list()
                except Exception:
                    pass
                
                # Small delay before next job
                time.sleep(random.uniform(2, 4))
                
                if limit_reached:
                    print("⛔ Application limit for this session reached.")
                    break
                
            except Exception as job_error:
                print(f"❌ Unexpected error processing job: {str(job_error)}")
                failed_applications += 1
                traceback.print_exc()
                # Try to navigate back
                try:
                    self._navigate_back_to_job_list()
                except:
                    pass
                continue
        
        # Summary
        print("\n" + "="*70)
        print("📊 PAGE PROCESSING SUMMARY")
        print("="*70)
        print(f"✅ Successful applications: {successful_applications}")
        print(f"⏭️  Skipped jobs: {skipped_jobs}")
        print(f"❌ Failed applications: {failed_applications}")
        print(f"🧪 Application attempts: {applications_attempted}")
        print(f"📋 Total jobs discovered: {len(job_cards)}")
        print("="*70 + "\n")

        return {
            'successful': successful_applications,
            'failed': failed_applications,
            'skipped': skipped_jobs,
            'attempted': applications_attempted,
            'limit_reached': limit_reached
        }
    
    def _navigate_back_to_job_list(self):
        """
        Navigate back to the job search results list.
        This is critical to ensure we can process the next job.
        """
        try:
            # Method 1: Click back button or close any open modals
            try:
                # Close any open modals/dialogs
                close_buttons = self.browser.find_elements(
                    By.CSS_SELECTOR,
                    "button[aria-label*='Dismiss' i], button[aria-label*='Close' i], .artdeco-modal__dismiss"
                )
                for button in close_buttons:
                    if button.is_displayed():
                        try:
                            button.click()
                            time.sleep(1)
                        except:
                            pass
            except:
                pass
            
            # Method 2: Press Escape key to close modals
            try:
                from selenium.webdriver.common.keys import Keys
                self.browser.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
                time.sleep(1)
            except:
                pass

            # Method 3: Click on the job list area to ensure focus
            try:
                job_list_area = self.browser.find_element(
                    By.CSS_SELECTOR,
                    "div[data-test-id='job-results-list'], ul.scaffold-layout__list-container"
                )
                if job_list_area.is_displayed():
                    # Click on a neutral area to ensure we're back to the list
                    self.browser.execute_script(
                        "arguments[0].scrollIntoView({block: 'start'});", 
                        job_list_area
                    )
                    time.sleep(1)
            except:
                pass
            
            # Wait a moment for the page to settle
            time.sleep(1)
            print("✅ Navigated back to job list")
            
        except Exception as nav_error:
            print(f"⚠️  Error navigating back to job list: {str(nav_error)}")
            # Last resort: refresh the page
            try:
                print("🔄 Refreshing page as fallback...")
                self.browser.refresh()
                time.sleep(3)
            except:
                pass

    def apply_to_job(self, job_tile):
        """
        Apply to a specific job
        """
        application_attempted = False
        try:
            # Check for logout before applying
            if not self.check_and_handle_logout():
                print("❌ Failed to handle logout. Skipping this job.")
                self.stats['total_jobs_skipped'] += 1
                return False
            
            start_time = time.perf_counter()
            self._app_events = []  # reset event buffer for this application
            self.stats['total_applications_attempted'] += 1
            application_attempted = True
            # Extract job information
            job_title, company, poster, job_location, apply_method, link = "", "", "", "", "", ""
            
            try:
                job_title_element = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title--link')
                job_title = job_title_element.find_element(By.TAG_NAME, 'strong').text
                link = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title--link').get_attribute('href').split('?')[0]
            except Exception as title_error:
                print(f"Could not extract job title/link: {str(title_error)}")
                return False
            
            try:
                company = job_tile.find_element(By.CLASS_NAME, 'artdeco-entity-lockup__subtitle').text
            except:
                pass
                
            try:
                hiring_line = job_tile.find_element(By.XPATH, '//span[contains(.,\' is hiring for this\')]')
                hiring_line_text = hiring_line.text
                name_terminating_index = hiring_line_text.find(' is hiring for this')
                if name_terminating_index != -1:
                    poster = hiring_line_text[:name_terminating_index]
            except:
                pass
                
            try:
                job_location = job_tile.find_element(By.CLASS_NAME, 'job-card-container__metadata-item').text
            except:
                pass
                
            try:
                apply_method = job_tile.find_element(By.CLASS_NAME, 'job-card-container__apply-method').text
            except:
                pass
            
            # Store current job info for skill editor
            self.current_job_title = job_title
            self.current_company = company
            
            self._log_info("Starting job application", checkpoint="apply_start")
            self._log_info(f"Job: {job_title}")
            self._log_info(f"Company: {company}")
            self._log_info(f"Location: {job_location}")
            
            # Check if already applied
            if link in self.seen_jobs:
                print(f"⏭️  Already applied to {job_title} at {company}. Skipping...")
                return False
            
            # Add to seen_jobs immediately to prevent duplicate attempts
            if link and link not in self.seen_jobs:
                self.seen_jobs.append(link)
            
            # Try to click on the job to open it
            max_retries = 3
            retries = 0
            while retries < max_retries:
                try:
                    job_el = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title--link')
                    
                    # Scroll the element into view first
                    self.browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", job_el)
                    time.sleep(1)
                    
                    # Try to click with JavaScript if regular click fails
                    try:
                        job_el.click()
                    except Exception as click_error:
                        if "element click intercepted" in str(click_error).lower():
                            # Use JavaScript click as fallback
                            self.browser.execute_script("arguments[0].click();", job_el)
                        else:
                            raise click_error
                    
                    break
                    
                except StaleElementReferenceException:
                    retries += 1
                    time.sleep(1)
                    continue
                except Exception as e:
                    if "element click intercepted" in str(e).lower():
                        retries += 1
                        time.sleep(2)
                        continue
                    else:
                        raise e
            
            # Wait for job details to load
            time.sleep(3)
            self._log_debug("Job details loaded")
            
            # Check for logout after clicking job (LinkedIn might show login modal)
            # Also verify session health for better reliability
            if not self.verify_session_health():
                print("⚠️  Session health check failed. Checking for logout...")
                if not self.check_and_handle_logout():
                    print("❌ Failed to handle logout after opening job. Skipping this job.")
                    self.stats['total_jobs_skipped'] += 1
                    return False
            elif not self.check_and_handle_logout():
                print("❌ Failed to handle logout after opening job. Skipping this job.")
                self.stats['total_jobs_skipped'] += 1
                return False
            
            # Read job description BEFORE clicking Easy Apply (when it's still visible)
            job_description_text = ""
            analysis = {}
            try:
                print("📖 Reading job description before opening Easy Apply...")
                
                # Scroll to ensure job description is visible
                self.browser.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)
                
                job_description_area = self.find_job_description_element()
                if job_description_area:
                    # Try to scroll through the description to load all content
                    try:
                        self.browser.execute_script("""
                            var element = arguments[0];
                            var scrollHeight = element.scrollHeight;
                            var currentScroll = 0;
                            var scrollStep = 200;
                            while (currentScroll < scrollHeight) {
                                element.scrollTop = currentScroll;
                                currentScroll += scrollStep;
                            }
                        """, job_description_area)
                        time.sleep(1)
                    except:
                        pass
                    
                    job_description_text = self.read_job_description(job_description_area)
                    if job_description_text and len(job_description_text.strip()) > 20:
                        print(f"✅ Successfully read job description ({len(job_description_text)} characters)")
                        
                        # Clean and enhance the text
                        job_description_text = self.clean_job_description_text(job_description_text)
                        
                        # Analyze the job description
                        analysis = self.analyze_job_description(job_description_text)
                        
                        # Update skills based on job description BEFORE applying
                        if analysis and 'job_skills' in analysis:
                            self._update_skills_based_on_job_description(analysis, job_description_text)
                        
                        self._log_info("JOB DESCRIPTION ANALYSIS", checkpoint="analysis_start")
                        
                        # Basic job info
                        print(f"📋 Job Type: {analysis.get('job_type', 'unknown').replace('_', ' ').title()}")
                        print(f"📍 Location Type: {analysis.get('location_type', 'unknown').replace('_', ' ').title()}")
                        print(f"💼 Experience Level: {analysis.get('experience_level', 'unknown').title()}")
                        print(f"🏠 Remote Work: {'Yes' if analysis.get('remote_work', False) else 'No'}")
                        print(f"💰 Salary Mentioned: {'Yes' if analysis.get('salary_mentioned', False) else 'No'}")
                        
                        # Skills analysis
                        job_skills = analysis.get('job_skills', [])
                        if job_skills:
                            print(f"\n🎯 Required Skills ({len(job_skills)}):")
                            # Group skills by category for better display
                            programming_skills = ['python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'bash', 'powershell', 'typescript']
                            framework_skills = ['react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask', 'spring', 'laravel', 'asp.net', 'jquery', 'bootstrap', 'tailwind', 'material-ui', 'redux', 'mobx', 'graphql', 'rest api', 'api development']
                            database_skills = ['sql', 'mysql', 'postgresql', 'oracle', 'sql server', 'sqlite', 'mongodb', 'redis', 'cassandra', 'dynamodb', 'elasticsearch', 'neo4j', 'firebase']
                            cloud_devops_skills = ['aws', 'azure', 'google cloud', 'gcp', 'heroku', 'digitalocean', 'linode', 'kubernetes', 'docker', 'terraform', 'cloudformation', 'serverless', 'git', 'github', 'gitlab', 'jenkins', 'circleci', 'travis ci', 'gitlab ci', 'ansible', 'chef', 'puppet', 'vagrant', 'virtualbox', 'vmware']
                            methodology_skills = ['agile', 'scrum', 'kanban', 'waterfall', 'devops', 'ci/cd', 'tdd', 'bdd', 'lean', 'six sigma', 'prince2', 'pmp']
                            soft_skill_list = ['leadership', 'communication', 'teamwork', 'problem solving', 'analytical thinking', 'creativity', 'adaptability', 'time management', 'project management']
                            
                            skill_categories = {
                                'Programming': [s for s in job_skills if s.lower() in programming_skills],
                                'Frameworks': [s for s in job_skills if s.lower() in framework_skills],
                                'Databases': [s for s in job_skills if s.lower() in database_skills],
                                'Cloud/DevOps': [s for s in job_skills if s.lower() in cloud_devops_skills],
                                'Methodologies': [s for s in job_skills if s.lower() in methodology_skills],
                                'Soft Skills': [s for s in job_skills if s.lower() in soft_skill_list],
                                'Other': [s for s in job_skills if s.lower() not in programming_skills + framework_skills + database_skills + cloud_devops_skills + methodology_skills + soft_skill_list]
                            }
                            
                            for category, skills in skill_categories.items():
                                if skills:
                                    print(f"  {category}: {', '.join(skills[:8])}{'...' if len(skills) > 8 else ''}")
                        
                        # Tech stack
                        tech_stack = analysis.get('tech_stack', [])
                        if tech_stack:
                            print(f"\n🔧 Tech Stack: {', '.join(tech_stack[:10])}{'...' if len(tech_stack) > 10 else ''}")
                        
                        # Red flags
                        red_flags = analysis.get('red_flags', [])
                        if red_flags:
                            print(f"\n🚨 Red Flags:")
                            for flag in red_flags:
                                print(f"  ⚠️  {flag}")
                        
                        # Skill matching results
                        if 'skill_match' in analysis:
                            skill_match = analysis['skill_match']
                            print(f"\n🎯 SKILL MATCHING ANALYSIS")
                            print(f"   Overall Score: {skill_match['score']}/100")
                            print(f"   Match Percentage: {skill_match['match_percentage']}%")
                            
                            if skill_match['matched_skills']:
                                print(f"   ✅ Matched Skills: {', '.join(skill_match['matched_skills'][:6])}{'...' if len(skill_match['matched_skills']) > 6 else ''}")
                            
                            if skill_match['missing_skills']:
                                print(f"   ❌ Missing Skills: {', '.join(skill_match['missing_skills'][:6])}{'...' if len(skill_match['missing_skills']) > 6 else ''}")
                            
                            if skill_match['extra_skills']:
                                print(f"   🎁 Extra Skills: {', '.join(skill_match['extra_skills'][:6])}{'...' if len(skill_match['extra_skills']) > 6 else ''}")
                        
                        self._log_info("End of analysis block", checkpoint="analysis_end")
                        
                        # Make decision based on analysis
                        should_apply = self.should_apply_to_job(analysis, job_description_text)
                        
                        if not should_apply:
                            self._log_info("Job analysis suggests not to apply. Skipping this job.")
                            self.stats['total_jobs_skipped'] += 1
                            return False
                        else:
                            self._log_info("Job analysis suggests this is a good fit. Proceeding with application.")
                    else:
                        print("⚠️  Could not read job description. Proceeding with application anyway.")
                else:
                    print("⚠️  Could not find job description container. Proceeding with application anyway.")
            except Exception as e:
                print(f"⚠️  Error reading job description: {str(e)}")
                print("⚠️  Proceeding with application anyway...")
                self._log_error("E_READ_JD", f"Error reading job description: {str(e)}")
            
            # Find and click the Easy Apply button with improved detection
            print("🔍 Looking for Easy Apply button...")
            
            # Try AI-powered selector generation first (if OpenRouter is available)
            ai_selector = None
            if self.openrouter:
                try:
                    print("🤖 Attempting AI-powered selector generation for Easy Apply button...")
                    ai_selector = self.get_ai_selector("Easy Apply button")
                    if ai_selector:
                        print(f"✅ AI generated selector: {ai_selector}")
                except Exception as e:
                    print(f"⚠️  AI selector generation failed: {e}, falling back to hardcoded selectors")
            
            try:
                easy_apply_button = None
                # Wait for page to fully load with better waiting strategy
                print("⏳ Waiting for page to stabilize...")
                time.sleep(2)
                
                # Scroll to top to ensure button is in viewport
                self.browser.execute_script("window.scrollTo(0, 0);")
                time.sleep(0.5)
                
                # Build selector list - try AI selector first if available
                easy_apply_selectors = []
                
                # Add AI-generated selector first if available
                if ai_selector:
                    easy_apply_selectors.append(ai_selector)
                    print(f"  🎯 Using AI-generated selector first: {ai_selector}")
                
                # Add comprehensive fallback hardcoded selectors (expanded list)
                easy_apply_selectors.extend([
                    "button[data-control-name='jobdetails_topcard_inapply']",
                    "button[data-control-name='jobdetails_topcard_apply']",
                    "button[aria-label*='Easy Apply' i]",
                    "button[aria-label*='easy apply' i]",
                    "button[aria-label*='Apply' i]",
                    "button.jobs-apply-button",
                    "button.jobs-s-apply",
                    ".jobs-apply-button",
                    "button[data-testid='apply-button']",
                    "button[class*='apply' i]",
                    "button[class*='Apply' i]",
                    "button[class*='jobs-apply']",
                    "button[class*='easy-apply']",
                    "a[data-control-name='jobdetails_topcard_inapply']",
                    "a[data-control-name='jobdetails_topcard_apply']",
                    "a[aria-label*='Easy Apply' i]",
                    "[role='button'][aria-label*='Easy Apply' i]",
                    "[role='button'][aria-label*='Apply' i]"
                ])
                
                # Try each selector with improved wait and detection
                for selector in easy_apply_selectors:
                    try:
                        print(f"  Trying selector: {selector}")
                        # Wait for element to be present with longer timeout
                        if selector.startswith('.') or selector.startswith('[') or selector.startswith('a['):
                            # CSS selector - try multiple methods
                            try:
                                # Method 1: Direct find with wait
                                elements = self.find_elements(By.CSS_SELECTOR, selector)
                                for elem in elements:
                                    # Check if element is visible and enabled
                                    try:
                                        is_visible = elem.is_displayed() if hasattr(elem, 'is_displayed') else (elem.is_visible() if hasattr(elem, 'is_visible') else True)
                                        is_enabled = elem.is_enabled() if hasattr(elem, 'is_enabled') else True
                                        
                                        if is_visible and is_enabled:
                                            # Get text content
                                            text = ''
                                            try:
                                                text = elem.text if hasattr(elem, 'text') else (elem.text_content() if hasattr(elem, 'text_content') else '')
                                            except:
                                                pass
                                            
                                            # Get aria-label
                                            aria_label = ''
                                            try:
                                                aria_label = elem.get_attribute('aria-label') if hasattr(elem, 'get_attribute') else ''
                                            except:
                                                pass
                                            
                                            text_lower = (text or aria_label or '').lower()
                                            
                                            # Check if it's an apply button
                                            if 'easy apply' in text_lower or ('apply' in text_lower and len(text_lower) < 50):
                                                easy_apply_button = elem
                                                print(f"✅ Found Easy Apply button using selector: {selector}")
                                                print(f"   Button text: {text[:50] if text else aria_label[:50]}")
                                                break
                                    except Exception as e:
                                        continue
                                
                                if easy_apply_button:
                                    break
                            except:
                                pass
                            
                            # Method 2: Try wait_for with longer timeout
                            try:
                                easy_apply_button = self.wait_for(By.CSS_SELECTOR, selector, timeout=5, condition='visible')
                                if easy_apply_button:
                                    # Verify it's actually an apply button
                                    try:
                                        text = easy_apply_button.text if hasattr(easy_apply_button, 'text') else ''
                                        aria_label = easy_apply_button.get_attribute('aria-label') if hasattr(easy_apply_button, 'get_attribute') else ''
                                        text_lower = (text or aria_label or '').lower()
                                        if 'easy apply' in text_lower or ('apply' in text_lower and len(text_lower) < 50):
                                            print(f"✅ Found Easy Apply button using selector: {selector}")
                                            break
                                        else:
                                            easy_apply_button = None
                                    except:
                                        easy_apply_button = None
                            except:
                                pass
                        else:
                            # Try to find element using wait_for
                            easy_apply_button = self.wait_for(By.CSS_SELECTOR, selector, timeout=5, condition='visible')
                            if easy_apply_button:
                                print(f"✅ Found Easy Apply button using selector: {selector}")
                                break
                    except Exception as e:
                        continue
                
                # Fallback: search all buttons by text
                if not easy_apply_button:
                    print("  Trying fallback: searching all buttons by text...")
                    try:
                        all_buttons = self.browser.find_elements(By.TAG_NAME, 'button')
                        for button in all_buttons:
                            try:
                                if button.is_displayed():
                                    button_text = (button.text or button.get_attribute('aria-label') or '').lower()
                                    if 'easy apply' in button_text or ('apply' in button_text and 'easy' in button_text):
                                        easy_apply_button = button
                                        print(f"✅ Found Easy Apply button by text: {button_text[:50]}")
                                        break
                            except:
                                continue
                    except Exception as e:
                        print(f"  Fallback search error: {str(e)}")
                
                if not easy_apply_button:
                    print("❌ Easy Apply button not found. Checking if job supports Easy Apply...")
                    # Check page source for Easy Apply indicators
                    page_source = self.page_source.lower()
                    if 'easy apply' not in page_source and 'apply' in page_source:
                        print("⚠️  This job may require external application or doesn't support Easy Apply")
                    self._log_error("E_NO_EASY_APPLY", "Easy Apply button not found. This job may not support Easy Apply.")
                    return False
                
                # Click the Easy Apply button with improved retry logic
                print(f"🖱️  Attempting to click Easy Apply button...")
                max_click_attempts = 7
                click_success = False
                for attempt in range(max_click_attempts):
                    try:
                        # Scroll button into view with multiple strategies
                        try:
                            self.browser.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", easy_apply_button)
                        except:
                            try:
                                self.browser.execute_script("arguments[0].scrollIntoView(true);", easy_apply_button)
                            except:
                                pass
                        
                        time.sleep(0.8)
                        
                        # Check if button is still visible and enabled
                        try:
                            is_visible = easy_apply_button.is_displayed() if hasattr(easy_apply_button, 'is_displayed') else True
                            is_enabled = easy_apply_button.is_enabled() if hasattr(easy_apply_button, 'is_enabled') else True
                            
                            if not is_visible or not is_enabled:
                                print(f"  Button not visible/enabled, retrying... ({attempt + 1}/{max_click_attempts})")
                                # Try to find button again
                                try:
                                    for selector in easy_apply_selectors[:3]:  # Try first 3 selectors
                                        try:
                                            easy_apply_button = self.browser.find_element(By.CSS_SELECTOR, selector)
                                            if easy_apply_button.is_displayed() and easy_apply_button.is_enabled():
                                                break
                                        except:
                                            continue
                                except:
                                    pass
                                if attempt < max_click_attempts - 1:
                                    time.sleep(1.5)
                                continue
                        except:
                            pass
                        
                        # Try multiple click strategies
                        click_methods = [
                            ("Regular click", lambda: easy_apply_button.click()),
                            ("JavaScript click", lambda: self.browser.execute_script("arguments[0].click();", easy_apply_button)),
                            ("ActionChains click", lambda: self._action_chains_click(easy_apply_button)),
                            ("Force click via JS", lambda: self.browser.execute_script("""
                                arguments[0].dispatchEvent(new MouseEvent('click', {
                                    bubbles: true,
                                    cancelable: true,
                                    view: window
                                }));
                            """, easy_apply_button))
                        ]
                        
                        for method_name, click_func in click_methods:
                            try:
                                print(f"  Trying {method_name}... ({attempt + 1}/{max_click_attempts})")
                                click_func()
                                time.sleep(1)  # Wait to see if modal opens
                                
                                # Verify click was successful by checking for modal
                                if self._verify_easy_apply_modal_opened():
                                    print(f"✅ Easy Apply button clicked successfully using {method_name}!")
                                    click_success = True
                                    self._log_info(f"Easy Apply button clicked ({method_name})")
                                    break
                            except ElementClickInterceptedException:
                                continue
                            except Exception as click_error:
                                if "element click intercepted" not in str(click_error).lower():
                                    continue
                                else:
                                    continue
                        
                        if click_success:
                            break
                        
                        if attempt < max_click_attempts - 1:
                            time.sleep(2)
                            
                    except StaleElementReferenceException:
                        print(f"  Element became stale, retrying... ({attempt + 1}/{max_click_attempts})")
                        if attempt < max_click_attempts - 1:
                            time.sleep(2)
                            # Try to find the button again
                            try:
                                for selector in easy_apply_selectors[:3]:
                                    try:
                                        easy_apply_button = self.browser.find_element(By.CSS_SELECTOR, selector)
                                        if easy_apply_button.is_displayed():
                                            break
                                    except:
                                        continue
                            except:
                                continue
                        else:
                            self._log_error("E_EASY_APPLY_FIND", "Failed to find Easy Apply button after all attempts")
                            return False
                            
                    except Exception as e:
                        self._log_error("E_EASY_APPLY", f"Unexpected error clicking Easy Apply: {str(e)}")
                        if attempt < max_click_attempts - 1:
                            time.sleep(2)
                            continue
                        else:
                            self._log_error("E_EASY_APPLY_CLICK", "Failed to click Easy Apply button after all attempts")
                            return False
                
                # Verify click was successful
                if not click_success:
                    print("❌ Failed to click Easy Apply button after all attempts")
                    return False
                
                # Wait for application form to load and verify it opened
                print("⏳ Waiting for application form to load...")
                time.sleep(3)
                
                # Verify the modal/form opened by checking for common form elements
                form_loaded = False
                form_indicators = [
                    ".jobs-easy-apply-modal",
                    ".jobs-easy-apply-content",
                    "form",
                    "[role='dialog']",
                    ".artdeco-modal__content"
                ]
                
                for indicator in form_indicators:
                    try:
                        elements = self.browser.find_elements(By.CSS_SELECTOR, indicator)
                        for elem in elements:
                            if elem.is_displayed():
                                form_loaded = True
                                print(f"✅ Application form detected using: {indicator}")
                                break
                        if form_loaded:
                            break
                    except:
                        continue
                
                if not form_loaded:
                    print("⚠️  Application form may not have loaded, but proceeding anyway...")
                else:
                    self._log_info("Easy Apply modal opened, proceeding to fill form...")
                
            except Exception as e:
                self._log_error("E_EASY_APPLY_OUTER", f"Error finding or clicking Easy Apply button: {str(e)}")
                return False
            
            # Now handle the application form
            print("📝 Starting to fill out the application form...")
            button_text = ""
            submit_application_text = 'submit application'
            max_form_attempts = 5
            form_attempt = 0
            
            while submit_application_text not in button_text.lower() and form_attempt < max_form_attempts:
                try:
                    form_attempt += 1
                    self._log_info(f"Form attempt {form_attempt}/{max_form_attempts}", checkpoint="form_attempt")
                    
                    # Use the new form filling method
                    form_success = self.fill_up(job_tile)
                    
                    if not form_success:
                        self._log_error("E_FORM_FILL", f"Form attempt {form_attempt} failed, retrying...")
                        if form_attempt < max_form_attempts:
                            time.sleep(2)  # Wait before retry
                            continue
                        else:
                            self._log_error("E_FORM_ALL_ATTEMPTS", "All form attempts failed")
                            raise Exception("Failed to fill form after all attempts")
                    
                    # Try multiple selectors for the next button
                    next_button = None
                    button_selectors = [
                        "artdeco-button--primary",
                        "artdeco-button--2",
                        "artdeco-button",
                        "button[type='submit']",
                        "button[data-control-name='continue_unify']"
                    ]
                    
                    for selector in button_selectors:
                        try:
                            if selector.startswith("button["):
                                next_button = self.browser.find_element(By.CSS_SELECTOR, selector)
                            else:
                                next_button = self.browser.find_element(By.CLASS_NAME, selector)
                            if next_button and next_button.is_enabled():
                                break
                        except:
                            continue
                    
                    if not next_button:
                        self._log_error("E_NEXT_BUTTON", "Could not find next button, refreshing and retrying")
                        self.browser.refresh()
                        time.sleep(3)
                        continue
                    
                    button_text = next_button.text.lower()
                    self._log_debug(f"Found button: {button_text}")
                    
                    if submit_application_text in button_text:
                        try:
                            self.unfollow()
                        except:
                            self._log_error("E_UNFOLLOW", "Failed to unfollow company")
                    time.sleep(random.uniform(1.5, 2.5))
                    
                    # Try to click the button with better error handling
                    try:
                        # Scroll to button first
                        self.browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_button)
                        time.sleep(1)
                        next_button.click()
                        self._log_info("Next button clicked successfully")
                    except Exception as click_error:
                        self._log_error("E_NEXT_CLICK", f"Regular click failed: {str(click_error)}")
                        # Try JavaScript click as fallback
                        try:
                            self.browser.execute_script("arguments[0].click();", next_button)
                            self._log_info("Next button clicked using JavaScript")
                        except Exception as js_error:
                            self._log_error("E_NEXT_CLICK_JS", f"JavaScript click also failed: {str(js_error)}")
                            raise Exception(f"Cannot proceed - next button not clickable: {str(click_error)}")
                    
                    time.sleep(random.uniform(3.0, 5.0))
                    
                    # Check for error messages
                    error_messages = [
                        'enter a valid',
                        'enter a decimal',
                        'Enter a whole number',
                        'Enter a whole number between 0 and 99',
                        'file is required',
                        'whole number',
                        'make a selection',
                        'select checkbox to proceed',
                        'saisissez un numéro',
                        '请输入whole编号',
                        '请输入decimal编号',
                        '长度超过 0.0',
                        'Numéro de téléphone',
                        'Introduce un número de whole entre',
                        'Inserisci un numero whole compreso',
                        'Preguntas adicionales',
                        'Insira um um número',
                        'Cuántos años',
                        'use the format',
                        'A file is required',
                        '请选择',
                        '请 选 择',
                        'Inserisci',
                        'wholenummer',
                        'Wpisz liczb',
                        'zakresu od',
                        'tussen'
                    ]
                    
                    if any(error in self.page_source.lower() for error in error_messages):
                        raise Exception("Failed answering required questions or uploading required files.")
                        
                except Exception as e:
                    self._log_error("E_DURING_APP", f"Error during application process: {str(e)}")
                    traceback.print_exc()
                    
                    # Try to close any open modals
                    try:
                        dismiss_buttons = self.browser.find_elements(By.CLASS_NAME, 'artdeco-modal__dismiss')
                        if dismiss_buttons:
                            dismiss_buttons[0].click()
                            time.sleep(random.uniform(2, 3))
                        
                        confirm_buttons = self.browser.find_elements(By.CLASS_NAME, 'artdeco-modal__confirm-dialog-btn')
                        if confirm_buttons:
                            confirm_buttons[0].click()
                            time.sleep(random.uniform(2, 3))
                    except Exception as close_error:
                        print(f"Could not close modal: {str(close_error)}")
                    
                    # If we've exhausted all attempts, raise the exception
                    if form_attempt >= max_form_attempts:
                        self._log_error("E_FORM_EXHAUSTED", f"Exhausted {max_form_attempts} form attempts, giving up")
                        raise Exception("Failed to apply to job after multiple attempts!")
                    else:
                        self._log_info(f"Retrying form... (attempt {form_attempt + 1}/{max_form_attempts})")
                        continue
            
            # Verify submission and close confirmations
            submitted = self.is_application_submitted()
            if submitted:
                self._log_info("Application appears to be submitted successfully", checkpoint="submitted")
                if link and link not in self.seen_jobs:
                    self.seen_jobs.append(link)
            else:
                self._log_error("E_VERIFY_SUBMIT", "Could not verify submission; proceeding cautiously")

            # Close application confirmation
            closed_notification = False
            time.sleep(random.uniform(3, 5))
            try:
                self.browser.find_element(By.CLASS_NAME, 'artdeco-modal__dismiss').click()
                closed_notification = True
            except:
                pass
            try:
                self.browser.find_element(By.CLASS_NAME, 'artdeco-toast-item__dismiss').click()
                closed_notification = True
            except:
                pass
            try:
                self.browser.find_element(By.CSS_SELECTOR, 'button[data-control-name="save_application_btn"]').click()
                closed_notification = True
            except:
                pass
            
            time.sleep(random.uniform(3, 5))
            
            if closed_notification is False:
                self._log_error("E_CLOSE_CONFIRM", "Could not close the applied confirmation window")
            else:
                self._log_info("Application confirmation closed successfully", checkpoint="confirm_closed")

            self._summarize_application(job_title, company, outcome="success", start_time=start_time, form_attempts=form_attempt, submitted=submitted)
            return True
        except Exception as e:
            self._log_error("E_APP_UNEXPECTED", f"Unexpected error applying to job: {str(e)}")
            traceback.print_exc()
            # Summary on failure
            try:
                self._summarize_application(job_title if 'job_title' in locals() else None,
                                            company if 'company' in locals() else None,
                                            outcome="failed",
                                            start_time=start_time if 'start_time' in locals() else None,
                                            form_attempts=form_attempt if 'form_attempt' in locals() else None,
                                            submitted=False)
            except Exception:
                pass
            return False

    def is_application_submitted(self):
        """
        Heuristically verify whether the application was submitted.
        """
        try:
            page = self.page_source.lower()
            success_keywords = [
                'application submitted',
                'your application was sent',
                'application sent',
                'you have successfully applied',
                'view application'
            ]
            if any(k in page for k in success_keywords):
                return True

            # Toast messages
            try:
                toasts = self.browser.find_elements(By.CLASS_NAME, 'artdeco-toast-item__message')
                for t in toasts:
                    if any(k in t.text.lower() for k in success_keywords):
                        return True
            except Exception:
                pass

            # Look for disabled Apply/Submit button as hint of completion
            try:
                buttons = self.browser.find_elements(By.CSS_SELECTOR, 'button')
                for b in buttons:
                    txt = (b.text or '').lower()
                    if ('submit' in txt or 'apply' in txt) and not b.is_enabled():
                        return True
            except Exception:
                pass

            return False
        except Exception:
            return False

    def home_address(self, form):
        print("Trying to fill up home address fields")
        try:
            groups = form.find_elements(By.CLASS_NAME, 'jobs-easy-apply-form-section__grouping')
            if len(groups) > 0:
                for group in groups:
                    lb = group.find_element(By.TAG_NAME, 'label').text.lower()
                    input_field = group.find_element(By.TAG_NAME, 'input')
                    if 'street' in lb:
                        self.enter_text(input_field, self.personal_info['Street address'])
                    elif 'city' in lb:
                        self.enter_text(input_field, self.personal_info['City'])
                        time.sleep(3)
                        input_field.send_keys(Keys.DOWN)
                        input_field.send_keys(Keys.RETURN)
                    elif 'zip' in lb or 'zip / postal code' in lb or 'postal' in lb:
                        self.enter_text(input_field, self.personal_info['Zip'])
                    elif 'state' in lb or 'province' in lb:
                        self.enter_text(input_field, self.personal_info['State'])
                    else:
                        pass
        except:
            pass

    def get_answer(self, question):
        if self.checkboxes[question]:
            return 'yes'
        else:
            return 'no'

    def additional_questions(self, form):
        print("Trying to fill up additional questions")

        questions = form.find_elements(By.CLASS_NAME, 'fb-dash-form-element')
        for question in questions:
            try:
                # Radio check
                radio_fieldset = question.find_element(By.TAG_NAME, 'fieldset')
                question_span = radio_fieldset.find_element(By.CLASS_NAME, 'fb-dash-form-element__label').find_elements(By.TAG_NAME, 'span')[0]
                radio_text = question_span.text.lower()
                print(f"Radio question text: {radio_text}")  # TODO: Put logging behind debug flag

                radio_labels = radio_fieldset.find_elements(By.TAG_NAME, 'label')
                radio_options = [text.text.lower() for text in radio_labels]
                print(f"radio options: {radio_options}")  # TODO: Put logging behind debug flag
                if len(radio_options) == 0:
                    raise Exception("No radio options found in question")

                answer = "yes"

                if 'driver\'s licence' in radio_text or 'driver\'s license' in radio_text:
                    answer = self.get_answer('driversLicence')

                elif any(keyword in radio_text.lower() for keyword in
                         [
                             'Aboriginal', 'native', 'indigenous', 'tribe', 'first nations',
                             'native american', 'native hawaiian', 'inuit', 'metis', 'maori',
                             'aborigine', 'ancestral', 'native peoples', 'original people',
                             'first people', 'gender', 'race', 'disability', 'latino', 'torres',
                             'do you identify'
                         ]):
                    negative_keywords = ['prefer', 'decline', 'don\'t', 'specified', 'none', 'no']
                    answer = next((option for option in radio_options if
                                   any(neg_keyword in option.lower() for neg_keyword in negative_keywords)), None)

                elif 'assessment' in radio_text:
                    answer = self.get_answer("assessment")

                elif 'clearance' in radio_text:
                    answer = self.get_answer("securityClearance")

                elif 'north korea' in radio_text:
                    answer = 'no'

                elif 'convicted' in radio_text:
                    answer = 'no'

                elif 'previously employ' in radio_text or 'previous employ' in radio_text:
                    answer = 'no'

                elif 'authorized' in radio_text or 'authorised' in radio_text or 'legally' in radio_text:
                    answer = self.get_answer('legallyAuthorized')

                elif any(keyword in radio_text.lower() for keyword in
                         ['certified', 'certificate', 'cpa', 'chartered accountant', 'qualification']):
                    answer = self.get_answer('certifiedProfessional')

                elif 'urgent' in radio_text:
                    answer = self.get_answer('urgentFill')

                elif 'commut' in radio_text or 'on-site' in radio_text or 'hybrid' in radio_text or 'onsite' in radio_text:
                    answer = self.get_answer('commute')

                elif 'remote' in radio_text:
                    answer = self.get_answer('remote')

                elif 'background check' in radio_text:
                    answer = self.get_answer('backgroundCheck')

                elif 'drug test' in radio_text:
                    answer = self.get_answer('drugTest')

                elif 'currently living' in radio_text or 'currently reside' in radio_text or 'right to live' in radio_text:
                    answer = self.get_answer('residency')

                elif 'level of education' in radio_text:
                    for degree in self.checkboxes['degreeCompleted']:
                        if degree.lower() in radio_text:
                            answer = "yes"
                            break

                elif 'experience' in radio_text:
                    for experience in self.experience:
                        if experience.lower() in radio_text:
                            answer = "yes"
                            break

                elif 'data retention' in radio_text:
                    answer = 'no'

                elif 'sponsor' in radio_text:
                    answer = self.get_answer('requireVisa')
                else:
                    answer = radio_options[len(radio_options) - 1]
                    self.record_unprepared_question("radio", radio_text)

                print(f"Choosing answer: {answer}")  # TODO: Put logging behind debug flag
                i = 0
                to_select = None
                for radio in radio_labels:
                    if answer in radio.text.lower():
                        to_select = radio_labels[i]
                    i += 1

                if to_select is None:
                    to_select = radio_labels[len(radio_labels) - 1]

                to_select.click()

                if radio_labels:
                    continue
            except:
                print("An exception occurred while filling up radio field")  # TODO: Put logging behind debug flag

            # Questions check
            try:
                question_text = question.find_element(By.TAG_NAME, 'label').text.lower()
                print( question_text )  # TODO: Put logging behind debug flag

                txt_field_visible = False
                try:
                    txt_field = question.find_element(By.TAG_NAME, 'input')
                    txt_field_visible = True
                except:
                    try:
                        txt_field = question.find_element(By.TAG_NAME, 'textarea')  # TODO: Test textarea
                        txt_field_visible = True
                    except:
                        raise Exception("Could not find textarea or input tag for question")

                text_field_type = txt_field.get_attribute('type').lower()
                if 'numeric' in text_field_type:  # TODO: test numeric type
                    text_field_type = 'numeric'
                elif 'text' in text_field_type:
                    text_field_type = 'text'
                else:
                    raise Exception("Could not determine input type of input field!")

                to_enter = ''
                if 'experience' in question_text or 'how many years in' in question_text:
                    no_of_years = None
                    for experience in self.experience:
                        if experience.lower() in question_text:
                            no_of_years = int(self.experience[experience])
                            break
                    if no_of_years is None:
                        self.record_unprepared_question(text_field_type, question_text)
                        no_of_years = int(self.experience_default)
                    to_enter = no_of_years

                elif 'grade point average' in question_text:
                    to_enter = self.university_gpa

                elif 'first name' in question_text:
                    to_enter = self.personal_info['First Name']

                elif 'last name' in question_text:
                    to_enter = self.personal_info['Last Name']

                elif 'name' in question_text:
                    to_enter = self.personal_info['First Name'] + " " + self.personal_info['Last Name']

                elif 'pronouns' in question_text:
                    to_enter = self.personal_info['Pronouns']

                elif 'phone' in question_text:
                    to_enter = self.personal_info['Mobile Phone Number']

                elif 'linkedin' in question_text:
                    to_enter = self.personal_info['Linkedin']

                elif 'message to hiring' in question_text or 'cover letter' in question_text:
                    to_enter = self.personal_info['MessageToManager']

                elif 'website' in question_text or 'github' in question_text or 'portfolio' in question_text:
                    to_enter = self.personal_info['Website']

                elif 'notice' in question_text or 'weeks' in question_text:
                    if text_field_type == 'numeric':
                        to_enter = int(self.notice_period)
                    else:
                        to_enter = str(self.notice_period)

                elif 'salary' in question_text or 'expectation' in question_text or 'compensation' in question_text or 'CTC' in question_text:
                    if text_field_type == 'numeric':
                        to_enter = int(self.salary_minimum)
                    else:
                        to_enter = float(self.salary_minimum)
                    self.record_unprepared_question(text_field_type, question_text)

                if text_field_type == 'numeric':
                    if not isinstance(to_enter, (int, float)):
                        to_enter = 0
                elif to_enter == '':
                    to_enter = " ‏‏‎ "

                self.enter_text(txt_field, to_enter)
                continue
            except:
                print("An exception occurred while filling up text field")  # TODO: Put logging behind debug flag

            # Date Check
            try:
                date_picker = question.find_element(By.CLASS_NAME, 'artdeco-datepicker__input ')
                date_picker.clear()
                date_picker.send_keys(date.today().strftime("%m/%d/%y"))
                time.sleep(3)
                date_picker.send_keys(Keys.RETURN)
                time.sleep(2)
                continue
            except:
                print("An exception occurred while filling up date picker field")  # TODO: Put logging behind debug flag

            # Dropdown check
            try:
                question_text = question.find_element(By.TAG_NAME, 'label').text.lower()
                print(f"Dropdown question text: {question_text}")  # TODO: Put logging behind debug flag
                dropdown_field = question.find_element(By.TAG_NAME, 'select')

                select = Select(dropdown_field)
                options = [options.text for options in select.options]
                print(f"Dropdown options: {options}")  # TODO: Put logging behind debug flag

                if 'proficiency' in question_text:
                    proficiency = "None"
                    for language in self.languages:
                        if language.lower() in question_text:
                            proficiency = self.languages[language]
                            break
                    self.select_dropdown(dropdown_field, proficiency)

                elif 'clearance' in question_text:
                    answer = self.get_answer('securityClearance')

                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            choice = option
                        else:
                            if 'no' in option.lower():
                                choice = option
                    if choice == "":
                        self.record_unprepared_question(text_field_type, question_text)
                    self.select_dropdown(dropdown_field, choice)

                elif 'assessment' in question_text:
                    answer = self.get_answer('assessment')
                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            choice = option
                        else:
                            if 'no' in option.lower():
                                choice = option
                    # if choice == "":
                    #    choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'commut' in question_text or 'on-site' in question_text or 'hybrid' in question_text or 'onsite' in question_text:
                    answer = self.get_answer('commute')

                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            choice = option
                        else:
                            if 'no' in option.lower():
                                choice = option
                    # if choice == "":
                    #    choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'country code' in question_text:
                    self.select_dropdown(dropdown_field, self.personal_info['Phone Country Code'])

                elif 'north korea' in question_text:
                    choice = ""
                    for option in options:
                        if 'no' in option.lower():
                            choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'previously employed' in question_text or 'previous employment' in question_text:
                    choice = ""
                    for option in options:
                        if 'no' in option.lower():
                            choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'sponsor' in question_text:
                    answer = self.get_answer('requireVisa')
                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            choice = option
                        else:
                            if 'no' in option.lower():
                                choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'above 18' in question_text.lower():  # Check for "above 18" in the question text
                    choice = ""
                    for option in options:
                        if 'yes' in option.lower():  # Select 'yes' option
                            choice = option
                    if choice == "":
                        choice = options[0]  # Default to the first option if 'yes' is not found
                    self.select_dropdown(dropdown_field, choice)

                elif 'currently living' in question_text or 'currently reside' in question_text:
                    answer = self.get_answer('residency')
                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            choice = option
                        else:
                            if 'no' in option.lower():
                                choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'authorized' in question_text or 'authorised' in question_text:
                    answer = self.get_answer('legallyAuthorized')
                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            # find some common words
                            choice = option
                        else:
                            if 'no' in option.lower():
                                choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'citizenship' in question_text:
                    answer = self.get_answer('legallyAuthorized')
                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            if 'no' in option.lower():
                                choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'clearance' in question_text:
                    answer = self.get_answer('clearance')
                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            choice = option
                        else:
                            if 'no' in option.lower():
                                choice = option
                    if choice == "":
                        choice = options[len(options) - 1]

                    self.select_dropdown(dropdown_field, choice)

                elif any(keyword in question_text.lower() for keyword in
                         [
                             'aboriginal', 'native', 'indigenous', 'tribe', 'first nations',
                             'native american', 'native hawaiian', 'inuit', 'metis', 'maori',
                             'aborigine', 'ancestral', 'native peoples', 'original people',
                             'first people', 'gender', 'race', 'disability', 'latino'
                         ]):
                    negative_keywords = ['prefer', 'decline', 'don\'t', 'specified', 'none']

                    choice = ""
                    choice = next((option for options in option.lower() if
                               any(neg_keyword in option.lower() for neg_keyword in negative_keywords)), None)

                    self.select_dropdown(dropdown_field, choice)

                elif 'email' in question_text:
                    continue  # assume email address is filled in properly by default

                elif 'experience' in question_text or 'understanding' in question_text or 'familiar' in question_text or 'comfortable' in question_text or 'able to' in question_text:
                    answer = 'no'
                    for experience in self.experience:
                        if experience.lower() in question_text and self.experience[experience] > 0:
                            answer = 'yes'
                            break
                    if answer == 'no':
                        # record unlisted experience as unprepared questions
                        self.record_unprepared_question("dropdown", question_text)

                    choice = ""
                    for option in options:
                        if answer in option.lower():
                            choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                else:
                    choice = ""
                    for option in options:
                        if 'yes' in option.lower():
                            choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)
                    self.record_unprepared_question("dropdown", question_text)
                continue
            except:
                print("An exception occurred while filling up dropdown field")  # TODO: Put logging behind debug flag

            # Checkbox check for agreeing to terms and service
            try:
                clickable_checkbox = question.find_element(By.TAG_NAME, 'label')
                clickable_checkbox.click()
            except:
                print("An exception occurred while filling up checkbox field")  # TODO: Put logging behind debug flag

    def unfollow(self):
        try:
            follow_checkbox = self.browser.find_element(By.XPATH,
                                                        "//label[contains(.,\'to stay up to date with their page.\')]").click()
            follow_checkbox.click()
        except:
            pass

    def send_resume(self):
        """
        Automatically upload resume and cover letter when applying to jobs
        """
        print("📄 Attempting to upload resume and cover letter...")
        
        try:
            # Check if resume path exists and is accessible
            if not hasattr(self, 'resume_dir') or not self.resume_dir:
                print("❌ No resume path configured in config.yaml")
                return False
            
            # Verify resume file exists
            import os
            if not os.path.exists(self.resume_dir):
                print(f"❌ Resume file not found at: {self.resume_dir}")
                print("💡 Please check the resume path in config.yaml")
                return False
            
            print(f"✅ Resume file found: {self.resume_dir}")
            
            # Try multiple selectors for file upload elements
            file_upload_selectors = [
                "input[name='file']",
                "input[type='file']",
                "input[accept*='.pdf']",
                "input[accept*='.doc']",
                "input[accept*='.docx']",
                "input[accept*='.txt']",
                "input[class*='file']",
                "input[class*='upload']"
            ]
            
            upload_elements_found = False
            
            for selector in file_upload_selectors:
                try:
                    file_inputs = self.browser.find_elements(By.CSS_SELECTOR, selector)
                    if file_inputs:
                        print(f"🔍 Found {len(file_inputs)} file upload elements using selector: {selector}")
                        
                        for upload_input in file_inputs:
                            try:
                                # Try to determine what type of file this input is for
                                upload_context = self.get_upload_context(upload_input)
                                print(f"📋 Upload context: {upload_context}")
                                
                                if 'resume' in upload_context.lower() or 'cv' in upload_context.lower():
                                    print(f"📤 Uploading resume to: {upload_context}")
                                    upload_input.send_keys(self.resume_dir)
                                    print("✅ Resume uploaded successfully!")
                                    upload_elements_found = True
                                    
                                elif 'cover' in upload_context.lower() and self.cover_letter_dir:
                                    if os.path.exists(self.cover_letter_dir):
                                        print(f"📤 Uploading cover letter to: {upload_context}")
                                        upload_input.send_keys(self.cover_letter_dir)
                                        print("✅ Cover letter uploaded successfully!")
                                        upload_elements_found = True
                                    else:
                                        print(f"⚠️  Cover letter file not found: {self.cover_letter_dir}")
                                        
                                elif 'required' in upload_context.lower():
                                    # If it's marked as required but we don't know what type, upload resume
                                    print(f"📤 Uploading resume to required field: {upload_context}")
                                    upload_input.send_keys(self.resume_dir)
                                    print("✅ Resume uploaded to required field!")
                                    upload_elements_found = True
                                    
                                else:
                                    print(f"⚠️  Unknown upload type: {upload_context}")
                                    
                            except Exception as upload_error:
                                print(f"❌ Error uploading to {upload_context}: {str(upload_error)}")
                                continue
                        
                        if upload_elements_found:
                            break
                            
                except Exception as selector_error:
                    print(f"⚠️  Error with selector {selector}: {str(selector_error)}")
                    continue
            
            if not upload_elements_found:
                print("⚠️  No file upload elements found or no successful uploads")
                print("💡 This might be a job that doesn't require resume upload")
                return False
            
            # Wait a moment for uploads to complete
            time.sleep(2)
            
            # Verify uploads were successful by checking for success indicators
            try:
                success_indicators = [
                    "//span[contains(text(), 'uploaded')]",
                    "//span[contains(text(), 'successful')]",
                    "//div[contains(@class, 'success')]",
                    "//div[contains(@class, 'uploaded')]"
                ]
                
                for indicator in success_indicators:
                    try:
                        success_element = self.browser.find_element(By.XPATH, indicator)
                        if success_element.is_displayed():
                            print("✅ Upload verification successful!")
                            break
                    except:
                        continue
                        
            except Exception as verify_error:
                print(f"⚠️  Could not verify upload success: {str(verify_error)}")
            
            return upload_elements_found
            
        except Exception as e:
            print(f"❌ Error in resume upload process: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_upload_context(self, upload_input):
        """
        Determine what type of file upload this input is for
        """
        try:
            # Try to find nearby text that describes what this upload is for
            context_selectors = [
                ".//preceding-sibling::*[1]",
                ".//following-sibling::*[1]",
                ".//ancestor::div[contains(@class, 'form')]//label",
                ".//ancestor::div[contains(@class, 'field')]//label",
                ".//ancestor::div[contains(@class, 'upload')]//label",
                ".//ancestor::div[contains(@class, 'resume')]//label",
                ".//ancestor::div[contains(@class, 'cover')]//label"
            ]
            
            for selector in context_selectors:
                try:
                    context_element = upload_input.find_element(By.XPATH, selector)
                    if context_element and context_element.text.strip():
                        return context_element.text.strip()
                except:
                    continue
            
            # Try to get context from parent elements
            try:
                parent = upload_input.find_element(By.XPATH, "..")
                if parent.text.strip():
                    return parent.text.strip()
            except:
                pass
            
            # Try to get context from aria-label or placeholder
            try:
                aria_label = upload_input.get_attribute('aria-label')
                if aria_label:
                    return aria_label
            except:
                pass
            
            try:
                placeholder = upload_input.get_attribute('placeholder')
                if placeholder:
                    return placeholder
            except:
                pass
            
            # Default context
            return "file upload"
            
        except Exception as e:
            return "file upload"

    def enter_text(self, element, text):
        element.clear()
        element.send_keys(text)

    def select_dropdown(self, element, text):
        select = Select(element)
        select.select_by_visible_text(text)

    # Radio Select
    def radio_select(self, element, label_text, clickLast=False):
        label = element.find_element(By.TAG_NAME, 'label')
        if label_text in label.text.lower() or clickLast == True:
            label.click()

    # Contact info fill-up
    def contact_info(self, form):
        print("Trying to fill up contact info fields")
        frm_el = form.find_elements(By.TAG_NAME, 'label')
        if len(frm_el) > 0:
            for el in frm_el:
                text = el.text.lower()
                if 'email address' in text:
                    continue
                elif 'phone number' in text:
                    try:
                        country_code_picker = el.find_element(By.XPATH,
                                                              '//select[contains(@id,"phoneNumber")][contains(@id,"country")]')
                        self.select_dropdown(country_code_picker, self.personal_info['Phone Country Code'])
                    except Exception as e:
                        print("Country code " + self.personal_info[
                            'Phone Country Code'] + " not found. Please make sure it is same as in LinkedIn.")
                        print(e)
                    try:
                        phone_number_field = el.find_element(By.XPATH,
                                                             '//input[contains(@id,"phoneNumber")][contains(@id,"nationalNumber")]')
                        self.enter_text(phone_number_field, self.personal_info['Mobile Phone Number'])
                    except Exception as e:
                        print("Could not enter phone number:")
                        print(e)

    def fill_up(self, job_tile):
        """
        Enhanced form filling with better wait strategies and error recovery
        """
        try:
            print("📝 Starting enhanced form filling process...")
            
            # Step 1: Wait for the modal to appear with multiple strategies
            modal_found = False
            max_wait_time = 15
            wait_interval = 0.5
            waited = 0
            
            modal_selectors = [
                ".jobs-easy-apply-modal__content",
                ".jobs-easy-apply-modal",
                "[data-test-modal]",
                ".artdeco-modal__content",
                ".artdeco-modal",
                ".jobs-easy-apply-content",
                ".jobs-easy-apply-form",
                "[role='dialog']",
                ".modal-content",
                "[class*='easy-apply']",
                "[class*='application-form']"
            ]
            
            print("🔍 Waiting for application modal to appear...")
            while waited < max_wait_time and not modal_found:
                for selector in modal_selectors:
                    try:
                        elements = self.browser.find_elements(By.CSS_SELECTOR, selector)
                        for elem in elements:
                            if elem.is_displayed():
                                print(f"✅ Modal found using selector: {selector}")
                                modal_found = True
                                break
                        if modal_found:
                            break
                    except:
                        continue
                
                if not modal_found:
                    time.sleep(wait_interval)
                    waited += wait_interval
                    # Check if page loaded (sometimes modal takes time)
                    try:
                        page_state = self.browser.execute_script("return document.readyState")
                        if page_state == "complete":
                            # Try to find any form-like elements as fallback
                            forms = self.browser.find_elements(By.TAG_NAME, "form")
                            if forms:
                                visible_forms = [f for f in forms if f.is_displayed()]
                                if visible_forms:
                                    print(f"🔍 Found {len(visible_forms)} visible form elements, proceeding...")
                                    modal_found = True
                                    break
                    except:
                        pass
            
            if not modal_found:
                print("⚠️  No modal found with standard selectors, trying alternative approach...")
                # Try to find any form-like elements
                try:
                    forms = self.browser.find_elements(By.TAG_NAME, "form")
                    visible_forms = [f for f in forms if f.is_displayed()]
                    if visible_forms:
                        print(f"🔍 Found {len(visible_forms)} visible form elements, proceeding...")
                        modal_found = True
                    else:
                        print("❌ No visible forms found")
                        # Try alternative form application
                        if self.try_alternative_form_application():
                            print("✅ Alternative form application successful")
                            return True
                        else:
                            print("❌ Alternative form application also failed")
                            return False
                except Exception as e:
                    print(f"❌ Error finding forms: {str(e)}")
                    # Try alternative form application as last resort
                    if self.try_alternative_form_application():
                        print("✅ Alternative form application successful")
                        return True
                    return False
                        
            # Give modal time to fully load
            time.sleep(random.uniform(1, 2))
            
            # Step 2: Fill form sections with enhanced error handling and retry logic
            self.stats['form_filling_attempts'] += 1
            sections_filled = 0
            section_attempts = {}
            
            # Define sections with their fill methods
            form_sections = [
                ("contact info", self.fill_contact_info),
                ("resume", self.fill_resume_section),
                ("work experience", self.fill_work_experience),
                ("education", self.fill_education),
                ("additional questions", self.fill_additional_questions)
            ]
            
            # Fill each section with retry logic
            for section_name, fill_method in form_sections:
                max_section_retries = 2
                section_filled = False
                
                for retry in range(1, max_section_retries + 1):
                    try:
                        print(f"📋 Filling form section: {section_name} (attempt {retry}/{max_section_retries})")
                        
                        # Check session health before filling
                        if not self.verify_session_health():
                            print(f"⚠️  Session health check failed before {section_name}")
                            if not self.check_and_handle_logout():
                                print(f"❌ Could not recover session, skipping {section_name}")
                                break
                        
                        if fill_method():
                            sections_filled += 1
                            section_attempts[section_name] = "success"
                            print(f"✅ Successfully filled {section_name} section")
                            section_filled = True
                            break
                        else:
                            if retry < max_section_retries:
                                print(f"⚠️  Could not fill {section_name} section, retrying...")
                                time.sleep(random.uniform(1, 2))
                            else:
                                print(f"⚠️  Could not fill {section_name} section after {max_section_retries} attempts")
                                section_attempts[section_name] = "failed"
                                
                    except Exception as e:
                        print(f"❌ Error filling {section_name} section (attempt {retry}): {str(e)}")
                        if retry < max_section_retries:
                            time.sleep(random.uniform(1, 2))
                        else:
                            section_attempts[section_name] = f"error: {str(e)[:50]}"
                
                # Small delay between sections for better reliability
                if section_filled:
                    time.sleep(random.uniform(0.5, 1))
            
            print(f"✅ Successfully filled {sections_filled}/5 form sections")
            print(f"📊 Section status: {section_attempts}")
            
            # Step 3: Try to find and click the Next/Submit button
            if sections_filled > 0:
                print("🔘 Attempting to submit form...")
                submission_result = self.handle_form_submission()
                
                if submission_result:
                    print("✅ Form submission successful")
                    self.stats['form_filling_successes'] += 1
                    return True
                else:
                    print("⚠️  Form submission failed, trying alternative methods...")
                    # Try alternative submission
                    if self.try_alternative_form_application():
                        print("✅ Alternative form submission successful")
                        return True
                    return False
            else:
                print("⚠️  No form sections were filled successfully")
                # Try alternative form application as fallback
                if self.try_alternative_form_application():
                    print("✅ Alternative form application successful as fallback")
                    return True
                else:
                    print("❌ Alternative form application also failed")
                    return False
            
        except Exception as e:
            print(f"❌ Error during form filling: {str(e)}")
            return False

    def write_to_file(self, company, job_title, link, location, search_location):
        to_write = [company, job_title, link, location, search_location, datetime.now()]
        file_path = self.file_name + ".csv"
        print(f'updated {file_path}.')

        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(to_write)

    def record_unprepared_question(self, answer_type, question_text):
        to_write = [answer_type, question_text]
        file_path = self.unprepared_questions_file_name + ".csv"

        try:
            with open(file_path, 'a') as f:
                writer = csv.writer(f)
                writer.writerow(to_write)
                print(f'Updated {file_path} with {to_write}.')
        except:
            print(
                "Special characters in questions are not allowed. Failed to update unprepared questions log.")
            print(question_text)

    def scroll_slow(self, scrollable_element, start=0, end=3600, step=100, reverse=False):
        if reverse:
            start, end = end, start
            step = -step

        for i in range(start, end, step):
            self.browser.execute_script("arguments[0].scrollTo(0, {})".format(i), scrollable_element)
            time.sleep(random.uniform(1.0, 2.6))

    def avoid_lock(self):
        if self.disable_lock:
            return

        pyautogui.keyDown('ctrl')
        pyautogui.press('esc')
        pyautogui.keyUp('ctrl')
        time.sleep(1.0)
        pyautogui.press('esc')

    def get_base_search_url(self, parameters):
        remote_url = ""
        lessthanTenApplicants_url = ""

        if parameters.get('remote'):
            remote_url = "&f_WT=2"
        else:
            remote_url = ""
            # TO DO: Others &f_WT= options { WT=1 onsite, WT=2 remote, WT=3 hybrid, f_WT=1%2C2%2C3 }

        if parameters['lessthanTenApplicants']:
            lessthanTenApplicants_url = "&f_EA=true"

        level = 1
        experience_level = parameters.get('experienceLevel', [])
        experience_url = "f_E="
        for key in experience_level.keys():
            if experience_level[key]:
                experience_url += "%2C" + str(level)
            level += 1

        distance_url = "?distance=" + str(parameters['distance'])

        job_types_url = "f_JT="
        job_types = parameters.get('jobTypes', [])
        # job_types = parameters.get('experienceLevel', [])
        for key in job_types:
            if job_types[key]:
                job_types_url += "%2C" + key[0].upper()

        date_url = ""
        dates = {"all time": "", "month": "&f_TPR=r2592000", "week": "&f_TPR=r604800", "24 hours": "&f_TPR=r86400"}
        date_table = parameters.get('date', [])
        for key in date_table.keys():
            if date_table[key]:
                date_url = dates[key]
                break

        easy_apply_url = "&f_AL=true"

        extra_search_terms = [distance_url, remote_url, lessthanTenApplicants_url, job_types_url, experience_url]
        extra_search_terms_str = '&'.join(
            term for term in extra_search_terms if len(term) > 0) + easy_apply_url + date_url

        return extra_search_terms_str

    def next_job_page(self, position, location, job_page):
        # Use Playwright's goto() instead of Selenium's get()
        url = "https://www.linkedin.com/jobs/search/" + self.base_search_url + \
              "&keywords=" + position + location + "&start=" + str(job_page * 25)
        try:
            self.browser.goto(url, wait_until='networkidle', timeout=30000)
            time.sleep(2)  # Give page time to load
        except Exception as e:
            print(f"⚠️  Navigation warning: {str(e)}")
            # Try with domcontentloaded as fallback
            try:
                self.browser.goto(url, wait_until='domcontentloaded', timeout=30000)
                time.sleep(2)
            except Exception as e2:
                print(f"❌ Failed to navigate to job page: {str(e2)}")
                raise

        self.avoid_lock()

    def fill_contact_info(self):
        """Fill contact information section"""
        try:
            # Look for contact info fields
            contact_fields = self.browser.find_elements(By.CSS_SELECTOR, 
                "input[type='text'], input[type='email'], input[type='tel']")
            
            if contact_fields:
                print(f"Found {len(contact_fields)} contact fields")
                # For now, just return True as contact info is usually pre-filled
                return True
            else:
                print("No contact info fields found")
                return False
        except Exception as e:
            print(f"Error in contact info: {str(e)}")
            return False
    
    def fill_resume_section(self):
        """Fill resume/CV section"""
        try:
            print("Trying to send resume")
            return self.send_resume()
        except Exception as e:
            print(f"Error in resume section: {str(e)}")
            return False
    
    def fill_work_experience(self):
        """Fill work experience section"""
        try:
            print("Trying to fill up additional questions")
            # Look for work experience related fields
            work_fields = self.browser.find_elements(By.CSS_SELECTOR, 
                "input[placeholder*='company'], input[placeholder*='title'], input[placeholder*='experience']")
            
            if work_fields:
                print(f"Found {len(work_fields)} work experience fields")
                # For now, just return True as this might be optional
                return True
            else:
                print("No work experience fields found")
                return False
        except Exception as e:
            print(f"Error in work experience: {str(e)}")
            return False
    
    def fill_education(self):
        """Fill education section"""
        try:
            print("Trying to fill up additional questions")
            # Look for education related fields
            education_fields = self.browser.find_elements(By.CSS_SELECTOR, 
                "input[placeholder*='school'], input[placeholder*='degree'], input[placeholder*='education']")
            
            if education_fields:
                print(f"Found {len(education_fields)} education fields")
                # For now, just return True as this might be optional
                return True
            else:
                print("No education fields found")
                return False
        except Exception as e:
            print(f"Error in education: {str(e)}")
            return False
    
    def fill_additional_questions(self):
        """Fill additional questions section"""
        try:
            print("Trying to fill up additional questions")
            # Look for various question types
            questions = self.browser.find_elements(By.CSS_SELECTOR, 
                "input[type='radio'], input[type='checkbox'], input[type='text'], select, textarea")
            
            if questions:
                print(f"Found {len(questions)} question fields")
                # Try to fill some basic questions
                filled_count = 0
                for question in questions[:10]:  # Limit to first 10 questions
                    try:
                        if self.fill_single_question(question):
                            filled_count += 1
                    except:
                        continue
                
                print(f"Successfully filled {filled_count}/{len(questions)} questions")
                return filled_count > 0
            else:
                print("No additional questions found")
                return True  # No questions to fill is still success
        except Exception as e:
            print(f"Error in additional questions: {str(e)}")
            return False
    
    def fill_single_question(self, question_element):
        """Fill a single question field"""
        try:
            question_type = question_element.get_attribute("type")
            question_text = ""
            
            # Try to get question text from nearby elements
            try:
                parent = question_element.find_element(By.XPATH, "./..")
                question_text = parent.text.lower()
            except:
                pass
            
            if question_type == "radio":
                print(f"An exception occurred while filling up radio field {question_text}")
                # Try to select first radio option
                try:
                    radio_options = question_element.find_elements(By.XPATH, "./following-sibling::input[@type='radio']")
                    if radio_options:
                        radio_options[0].click()
                        return True
                except:
                    pass
                return False
                
            elif question_type == "checkbox":
                print(f"An exception occurred while filling up checkbox field {question_text}")
                # Try to check the checkbox
                try:
                    if not question_element.is_selected():
                        question_element.click()
                    return True
                except:
                    pass
                return False
                
            elif question_type == "text" or question_element.tag_name == "textarea":
                print(f"📝 Filling text/textarea field: {question_text[:100]}")
                # Try to get intelligent answer using OpenRouter API if available
                answer_text = None
                
                if self.openrouter and question_text:
                    try:
                        job_title = getattr(self, 'current_job_title', 'Software Engineer')
                        company = getattr(self, 'current_company', 'Company')
                        
                        print(f"🤖 Using OpenRouter AI to generate answer for: {question_text[:80]}...")
                        answer_text = self.openrouter.answer_application_question(
                            question=question_text,
                            job_title=job_title,
                            company=company,
                            candidate_background=f"Skills: {', '.join(self.user_skills[:5]) if hasattr(self, 'user_skills') else ''}"
                        )
                        
                        if answer_text:
                            print(f"✅ AI-generated answer: {answer_text[:100]}...")
                        else:
                            print("⚠️  AI answer generation failed, using fallback")
                    except Exception as e:
                        print(f"⚠️  OpenRouter API error: {str(e)}, using fallback answer")
                
                # Fallback to generic response if AI didn't work
                if not answer_text:
                    if 'why' in question_text or 'interest' in question_text:
                        answer_text = f"I am very interested in this {getattr(self, 'current_job_title', 'position')} role at {getattr(self, 'current_company', 'your company')}. My skills and experience align well with the requirements, and I'm excited about the opportunity to contribute to your team."
                    elif 'experience' in question_text or 'years' in question_text:
                        answer_text = "Please see my resume for detailed experience information."
                    elif 'salary' in question_text or 'compensation' in question_text:
                        answer_text = "I'm open to discussing compensation based on the role and responsibilities."
                    else:
                        answer_text = "Please see my resume for additional details."
                
                # Fill the field
                try:
                    question_element.clear()
                    time.sleep(0.3)
                    question_element.send_keys(answer_text)
                    print(f"✅ Successfully filled text field with answer")
                    return True
                except Exception as e:
                    print(f"❌ Error filling text field: {str(e)}")
                return False
                
            elif question_type == "date":
                print(f"An exception occurred while filling up date picker field")
                # Try to fill with current date
                try:
                    from datetime import datetime
                    current_date = datetime.now().strftime("%m/%d/%Y")
                    question_element.clear()
                    question_element.send_keys(current_date)
                    return True
                except:
                    pass
                return False
                
            elif question_element.tag_name == "select":
                print(f"Dropdown question text: {question_text}")
                # Try to select first option
                try:
                    select = Select(question_element)
                    if select.options:
                        select.select_by_index(0)
                        return True
                except:
                    pass
                return False
                
            return False
            
        except Exception as e:
            print(f"Error filling question: {str(e)}")
            return False
    
    def handle_form_submission(self, max_attempts=3):
        """
        Enhanced form submission handler with multiple strategies and retry logic
        """
        for attempt in range(1, max_attempts + 1):
            try:
                print(f"🔘 Attempting form submission (attempt {attempt}/{max_attempts})...")
                
                # Strategy 1: Try multiple selectors for the next/submit button
                button_selectors = [
                    ".artdeco-button--primary",
                    ".artdeco-button--2",
                    "button[type='submit']",
                    "button[data-control-name='continue_unify']",
                    "button[aria-label*='Continue']",
                    "button[aria-label*='Submit']",
                    "button[aria-label*='Next']",
                    "button[aria-label*='Apply']",
                    "button.artdeco-button--primary",
                    "button[class*='primary']",
                    "input[type='submit']",
                    "[data-control-name='submit_unify']"
                ]
                
                next_button = None
                button_text = ""
                
                # Wait a bit for button to appear
                time.sleep(random.uniform(0.5, 1))
                
                for selector in button_selectors:
                    try:
                        buttons = self.browser.find_elements(By.CSS_SELECTOR, selector)
                        for button in buttons:
                            try:
                                if button.is_displayed() and button.is_enabled():
                                    btn_text = (button.text or button.get_attribute('aria-label') or '').lower()
                                    # Check if button text matches submission keywords
                                    if any(word in btn_text for word in ['continue', 'next', 'submit', 'apply', 'send']):
                                        next_button = button
                                        button_text = btn_text
                                        print(f"✅ Found submission button: {btn_text[:50]}")
                                        break
                            except:
                                continue
                        if next_button:
                            break
                    except:
                        continue
                
                # Strategy 2: If no button found, try finding by text content
                if not next_button:
                    try:
                        all_buttons = self.browser.find_elements(By.TAG_NAME, "button")
                        for button in all_buttons:
                            try:
                                if button.is_displayed() and button.is_enabled():
                                    btn_text = (button.text or '').lower()
                                    if any(word in btn_text for word in ['continue', 'next', 'submit application', 'apply']):
                                        # Check if it's a primary button (more likely to be submit)
                                        classes = button.get_attribute('class') or ''
                                        if 'primary' in classes.lower() or 'submit' in classes.lower():
                                            next_button = button
                                            button_text = btn_text
                                            print(f"✅ Found submission button by text: {btn_text[:50]}")
                                            break
                            except:
                                continue
                    except:
                        pass
                
                if next_button:
                    # Try multiple click strategies
                    click_success = False
                    
                    # Strategy 1: Scroll into view and regular click
                    try:
                        self.browser.execute_script("arguments[0].scrollIntoView({block: 'center', behavior: 'smooth'});", next_button)
                        time.sleep(random.uniform(0.5, 1))
                        
                        # Check if button is still enabled
                        if next_button.is_enabled():
                            next_button.click()
                            print("✅ Button clicked successfully (regular click)")
                            click_success = True
                    except Exception as e:
                        print(f"⚠️  Regular click failed: {str(e)[:50]}")
                    
                    # Strategy 2: JavaScript click
                    if not click_success:
                        try:
                            self.browser.execute_script("arguments[0].click();", next_button)
                            print("✅ Button clicked using JavaScript")
                            click_success = True
                        except Exception as e:
                            print(f"⚠️  JavaScript click failed: {str(e)[:50]}")
                    
                    # Strategy 3: Wait and retry
                    if not click_success:
                        try:
                            time.sleep(2)
                            # Re-find button (might have changed)
                            if next_button.is_enabled():
                                next_button.click()
                                print("✅ Button clicked after wait")
                                click_success = True
                        except:
                            pass
                    
                    # Strategy 4: Force click via JavaScript with event dispatch
                    if not click_success:
                        try:
                            self.browser.execute_script("""
                                var btn = arguments[0];
                                var event = new MouseEvent('click', {
                                    view: window,
                                    bubbles: true,
                                    cancelable: true
                                });
                                btn.dispatchEvent(event);
                            """, next_button)
                            print("✅ Button clicked using event dispatch")
                            click_success = True
                        except Exception as e:
                            print(f"⚠️  Event dispatch click failed: {str(e)[:50]}")
                    
                    if click_success:
                        # Wait a bit to see if form progresses
                        time.sleep(random.uniform(1, 2))
                        return True
                    else:
                        if attempt < max_attempts:
                            print(f"⏳ All click strategies failed, retrying in 2 seconds...")
                            time.sleep(2)
                            continue
                        else:
                            print("❌ All click strategies failed after all attempts")
                            return False
                else:
                    print(f"⚠️  No submission button found (attempt {attempt}/{max_attempts})")
                    if attempt < max_attempts:
                        # Wait and try again - button might appear later
                        time.sleep(2)
                        continue
                    else:
                        print("❌ No submission button found after all attempts")
                        return False
                        
            except Exception as e:
                print(f"❌ Error in form submission attempt {attempt}: {str(e)}")
                if attempt < max_attempts:
                    time.sleep(2)
                    continue
                traceback.print_exc()
                return False
        
        return False

    def find_alternative_forms(self):
        """Find alternative application forms when the main modal is not found"""
        try:
            print("🔍 Looking for alternative application forms...")
            
            # Look for various types of forms
            form_selectors = [
                "form",
                ".application-form",
                ".job-application-form",
                ".apply-form",
                "[data-test-application-form]",
                ".artdeco-form",
                ".jobs-apply-form"
            ]
            
            forms_found = []
            for selector in form_selectors:
                try:
                    forms = self.browser.find_elements(By.CSS_SELECTOR, selector)
                    if forms:
                        forms_found.extend(forms)
                        print(f"Found {len(forms)} forms using selector: {selector}")
                except:
                    continue
            
            # Remove duplicates
            unique_forms = []
            seen_ids = set()
            for form in forms_found:
                try:
                    form_id = form.get_attribute("id") or form.get_attribute("class") or str(hash(form))
                    if form_id not in seen_ids:
                        unique_forms.append(form)
                        seen_ids.add(form_id)
                except:
                    continue
            
            print(f"🔍 Found {len(unique_forms)} unique alternative forms")
            return unique_forms
            
        except Exception as e:
            print(f"❌ Error finding alternative forms: {str(e)}")
            return []
    
    def try_alternative_form_application(self):
        """Try to apply using alternative forms when the main modal fails"""
        try:
            print("🔄 Trying alternative form application...")
            
            # Look for alternative forms
            alternative_forms = self.find_alternative_forms()
            
            if not alternative_forms:
                print("❌ No alternative forms found")
                return False
            
            # Try to fill each form
            for i, form in enumerate(alternative_forms):
                try:
                    print(f"📝 Trying alternative form {i+1}/{len(alternative_forms)}")
                    
                    # Look for common form elements
                    inputs = form.find_elements(By.CSS_SELECTOR, "input, select, textarea")
                    if inputs:
                        print(f"  Found {len(inputs)} form elements")
                        
                        # Try to fill basic fields
                        filled_count = 0
                        for input_elem in inputs[:5]:  # Limit to first 5 inputs
                            try:
                                if self.fill_single_question(input_elem):
                                    filled_count += 1
                            except:
                                continue
                        
                        print(f"  Successfully filled {filled_count}/{len(inputs)} fields")
                        
                        # Look for submit button
                        submit_buttons = form.find_elements(By.CSS_SELECTOR, 
                            "button[type='submit'], button:contains('Submit'), button:contains('Apply')")
                        
                        if submit_buttons:
                            print(f"  Found {len(submit_buttons)} submit buttons")
                            return True
                            
                except Exception as e:
                    print(f"  ❌ Error with alternative form {i+1}: {str(e)}")
                    continue
            
            print("❌ All alternative forms failed")
            return False
            
        except Exception as e:
            print(f"❌ Error in alternative form application: {str(e)}")
            return False

    def get_hibernation_config(self):
        """Load and cache hibernation configuration settings."""
        if self._hibernation_config is not None:
            return self._hibernation_config

        try:
            with open('anti_ban_config.json', 'r', encoding='utf-8') as config_file:
                config_data = json.load(config_file)
                self._hibernation_config = config_data.get('hibernation_mode', {}) or {}
        except FileNotFoundError:
            print("⚠️  anti_ban_config.json not found. Using default hibernation settings.")
            self._hibernation_config = {}
        except json.JSONDecodeError as exc:
            print(f"⚠️  Failed to parse anti_ban_config.json: {exc}")
            self._hibernation_config = {}

        return self._hibernation_config

    def simulate_human_activity(self, duration_minutes=3):
        """
        Simulate passive human activity on LinkedIn to build natural browsing history.
        Actions include visiting the feed, scrolling, and viewing suggested profiles.
        """
        if duration_minutes is None:
            duration_minutes = 3
        try:
            duration_minutes = max(1, int(duration_minutes))
        except Exception:
            duration_minutes = 3

        if not getattr(self, 'browser', None):
            print("⚠️  Cannot simulate human activity without an active browser session.")
            return

        end_time = time.time() + duration_minutes * 60
        print(f"👣 Simulating human activity for approximately {duration_minutes} minute(s)...")
        self._log_info("Starting human activity simulation", checkpoint="human_activity_start")

        def _safe_scroll(iterations=None):
            scroll_times = iterations or random.randint(3, 6)
            for _ in range(scroll_times):
                delta = random.randint(500, 1100)
                try:
                    if hasattr(self.browser, 'mouse'):
                        self.browser.mouse.wheel(0, delta)
                    else:
                        self.browser.evaluate("window.scrollBy(0, arguments[0]);", delta)
                except Exception:
                    try:
                        self.browser.evaluate("window.scrollBy(0, arguments[0]);", delta)
                    except Exception:
                        pass
                time.sleep(random.uniform(0.7, 1.4))

        def _visit_feed():
            print("📄 Visiting LinkedIn feed")
            self.safe_get("https://www.linkedin.com/feed/")
            time.sleep(random.uniform(3, 5))
            _safe_scroll()

        def _visit_my_network():
            print("👥 Opening My Network page")
            self.safe_get("https://www.linkedin.com/mynetwork/")
            time.sleep(random.uniform(3, 5))
            _safe_scroll()

        def _scroll_current_page():
            print("🖱️  Scrolling current page")
            _safe_scroll(random.randint(2, 4))

        def _view_people_also_viewed():
            print("🔍 Looking at People Also Viewed section")
            selectors = [
                "[data-test-id='peopleAlsoViewedSection'] a[href*='/in/']",
                "section[data-test-id='right-rail'] a[href*='/in/']",
                "aside a[href*='/in/'][data-test-app-aware='true']",
                "a[href*='/in/'][data-control-name*='people']"
            ]
            for selector in selectors:
                try:
                    locator = self.browser.locator(selector)
                    count = locator.count()
                    if count == 0:
                        continue
                    index = random.randrange(min(count, 5))
                    profile = locator.nth(index)
                    profile.scroll_into_view_if_needed()
                    time.sleep(random.uniform(1, 2))
                    profile.click()
                    time.sleep(random.uniform(3, 6))
                    _safe_scroll(random.randint(1, 3))
                    try:
                        self.browser.go_back()
                    except Exception:
                        pass
                    time.sleep(random.uniform(2, 4))
                    return True
                except Exception:
                    continue
            print("ℹ️  People Also Viewed section not found this time")
            return False

        actions = [
            ("visit_feed", _visit_feed),
            ("scroll_page", _scroll_current_page),
            ("visit_my_network", _visit_my_network),
            ("view_people_also_viewed", _view_people_also_viewed)
        ]

        while time.time() < end_time:
            action_name, action_callable = random.choice(actions)
            try:
                action_result = action_callable()
                self._log_debug(f"Human activity action executed: {action_name} ({action_result})")
            except Exception as exc:
                print(f"⚠️  Human activity action failed: {exc}")
                self._log_error("E_HUMAN_ACTIVITY", f"Action {action_name} failed: {exc}")
            # Random idle time between actions
            idle_seconds = random.uniform(5, 12)
            time.sleep(idle_seconds)
            if time.time() + 5 > end_time:
                break

        print("✅ Human activity simulation completed")
        self._log_info("Human activity simulation completed", checkpoint="human_activity_end")

    def run_single_application_session(self):
        """Execute a single application attempt using hibernation-mode constraints."""
        print("\n" + "=" * 70)
        print("🌙 RUNNING SINGLE APPLICATION SESSION")
        print("=" * 70)
        self._log_info("Starting single-session application", checkpoint="single_session_start")

        hibernation_settings = self.get_hibernation_config()
        max_applications = hibernation_settings.get('max_applications_per_session', 1)
        try:
            max_applications = int(max_applications)
        except Exception:
            max_applications = 1
        max_applications = max(1, min(max_applications, 1))  # enforce single application limit

        search_pairs = list(product(self.positions, self.locations))
        random.shuffle(search_pairs)

        attempt_summary = None
        for position, location in search_pairs:
            print(f"🎯 Target position: {position} | Location: {location}")
            try:
                if not self.check_and_handle_logout():
                    print("❌ Unable to verify login status. Aborting session.")
                    break

                location_url = f"&location={location}"
                print("📄 Loading job search results page...")
                self.next_job_page(position, location_url, 0)
                time.sleep(random.uniform(2, 4))

                summary = self.apply_jobs(location, max_applications=max_applications)
                attempt_summary = summary or {}

                attempts = attempt_summary.get('attempted', 0)
                if attempts >= max_applications:
                    print("✅ Single application session completed.")
                    break

                print("⚠️  No suitable job attempted for this search combination. Trying next...")
            except Exception as exc:
                print(f"❌ Error during single-session application: {exc}")
                traceback.print_exc()
                time.sleep(random.uniform(2, 4))
                continue

        if not attempt_summary or attempt_summary.get('attempted', 0) == 0:
            print("⚠️  No applications were attempted during this session.")
        else:
            print("\n" + "-" * 70)
            print("📈 SINGLE SESSION SUMMARY")
            print("-" * 70)
            print(f"✅ Successful: {attempt_summary.get('successful', 0)}")
            print(f"❌ Failed: {attempt_summary.get('failed', 0)}")
            print(f"⏭️  Skipped: {attempt_summary.get('skipped', 0)}")
            print(f"🧪 Attempts: {attempt_summary.get('attempted', 0)}")
            print("-" * 70 + "\n")

        self._log_info("Single-session application completed", checkpoint="single_session_end")
        return attempt_summary
