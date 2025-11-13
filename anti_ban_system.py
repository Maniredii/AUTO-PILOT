#!/usr/bin/env python3
"""
Advanced Anti-Ban System for LinkedIn Easy Apply Bot
Implements multiple layers of detection avoidance and account protection
"""

import random
import time
import json
import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import asyncio
import logging
from pathlib import Path

# Browser automation imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException

@dataclass
class SessionMetrics:
    """Track session activity to avoid detection patterns"""
    start_time: datetime
    applications_count: int
    page_views: int
    clicks: int
    typing_events: int
    scroll_events: int
    mouse_movements: int
    idle_time: float
    errors_count: int
    captcha_encounters: int
    
class BehaviorPattern:
    """Human behavior simulation patterns"""
    
    @staticmethod
    def human_delay(min_seconds: float = 1.0, max_seconds: float = 3.0) -> float:
        """Generate human-like delays with gaussian distribution"""
        # Use gaussian distribution for more natural timing
        mean = (min_seconds + max_seconds) / 2
        std = (max_seconds - min_seconds) / 6  # 99.7% within range
        delay = random.gauss(mean, std)
        return max(min_seconds, min(max_seconds, delay))
    
    @staticmethod
    def typing_speed() -> float:
        """Simulate human typing speed (characters per second)"""
        # Average human typing: 5-8 characters per second
        base_speed = random.uniform(5, 8)
        # Add occasional slower typing (thinking)
        if random.random() < 0.2:  # 20% chance
            base_speed *= random.uniform(0.3, 0.7)
        return 1.0 / base_speed  # Return delay between characters
    
    @staticmethod
    def mouse_movement_pattern() -> List[Tuple[int, int]]:
        """Generate natural mouse movement path"""
        # Create bezier-like curved path between points
        points = []
        current_x, current_y = random.randint(100, 800), random.randint(100, 600)
        
        for _ in range(random.randint(5, 15)):
            # Add some randomness to movement
            next_x = current_x + random.randint(-50, 50)
            next_y = current_y + random.randint(-30, 30)
            points.append((next_x, next_y))
            current_x, current_y = next_x, next_y
            
        return points
    
    @staticmethod
    def scroll_pattern() -> List[int]:
        """Generate natural scrolling behavior"""
        # Humans don't scroll uniformly
        scrolls = []
        total_scroll = random.randint(300, 1200)
        remaining = total_scroll
        
        while remaining > 0:
            # Vary scroll amounts
            scroll_amount = min(remaining, random.randint(50, 200))
            scrolls.append(scroll_amount)
            remaining -= scroll_amount
            
        return scrolls

class FingerprintManager:
    """Advanced browser fingerprint management"""
    
    def __init__(self):
        self.fingerprints = self._generate_fingerprint_pool()
        self.current_fingerprint = None
    
    def _generate_fingerprint_pool(self) -> List[Dict]:
        """Generate pool of realistic browser fingerprints"""
        fingerprints = []
        
        # Common screen resolutions
        resolutions = [
            (1920, 1080), (1366, 768), (1536, 864), (1440, 900),
            (1280, 720), (1600, 900), (2560, 1440), (1920, 1200)
        ]
        
        # Common user agents (recent versions)
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15"
        ]
        
        # Generate fingerprint combinations
        for i in range(20):  # Create 20 different fingerprints
            width, height = random.choice(resolutions)
            fingerprint = {
                'user_agent': random.choice(user_agents),
                'screen_resolution': f"{width}x{height}",
                'viewport_size': (width - random.randint(0, 100), height - random.randint(100, 200)),
                'timezone': random.choice(['America/New_York', 'America/Los_Angeles', 'America/Chicago', 'Europe/London']),
                'language': random.choice(['en-US', 'en-GB', 'en-CA']),
                'platform': random.choice(['Win32', 'MacIntel', 'Linux x86_64']),
                'hardware_concurrency': random.choice([4, 6, 8, 12, 16]),
                'device_memory': random.choice([4, 8, 16, 32]),
                'webgl_vendor': random.choice(['Google Inc.', 'ANGLE']),
                'webgl_renderer': random.choice([
                    'ANGLE (Intel, Intel(R) UHD Graphics Direct3D11 vs_5_0 ps_5_0, D3D11)',
                    'ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Ti Direct3D11 vs_5_0 ps_5_0, D3D11)'
                ])
            }
            fingerprints.append(fingerprint)
            
        return fingerprints
    
    def get_random_fingerprint(self) -> Dict:
        """Get a random fingerprint from the pool"""
        self.current_fingerprint = random.choice(self.fingerprints)
        return self.current_fingerprint
    
    def apply_fingerprint(self, driver_options: Options, fingerprint: Dict):
        """Apply fingerprint to browser options"""
        # Set user agent
        driver_options.add_argument(f"--user-agent={fingerprint['user_agent']}")
        
        # Set window size
        width, height = fingerprint['viewport_size']
        driver_options.add_argument(f"--window-size={width},{height}")
        
        # Set timezone
        driver_options.add_argument(f"--timezone={fingerprint['timezone']}")
        
        # Set language
        driver_options.add_experimental_option('prefs', {
            'intl.accept_languages': fingerprint['language']
        })

class AntiDetectionManager:
    """Comprehensive anti-detection system"""
    
    def __init__(self, config_path: str = "anti_ban_config.json"):
        self.config = self._load_config(config_path)
        self.session_metrics = self._init_session_metrics()
        self.fingerprint_manager = FingerprintManager()
        self.behavior_pattern = BehaviorPattern()
        self.detection_triggers = self._init_detection_triggers()
        self.logger = self._setup_logging()
        
    def _load_config(self, config_path: str) -> Dict:
        """Load anti-ban configuration"""
        default_config = {
            'max_applications_per_session': 20,
            'max_session_duration_minutes': 120,
            'min_delay_between_applications': 300,  # 5 minutes
            'max_delay_between_applications': 900,   # 15 minutes
            'break_duration_minutes': 30,
            'max_daily_applications': 50,
            'rotation_frequency_minutes': 60,
            'captcha_cooldown_minutes': 60,
            'error_threshold': 5,
            'stealth_mode': True,
            'proxy_rotation': False,
            'user_data_rotation': True
        }
        
        try:
            with open(config_path, 'r') as f:
                custom_config = json.load(f)
                default_config.update(custom_config)
        except FileNotFoundError:
            # Save default config
            with open(config_path, 'w') as f:
                json.dump(default_config, f, indent=2)
                
        return default_config
    
    def _init_session_metrics(self) -> SessionMetrics:
        """Initialize session tracking"""
        return SessionMetrics(
            start_time=datetime.now(),
            applications_count=0,
            page_views=0,
            clicks=0,
            typing_events=0,
            scroll_events=0,
            mouse_movements=0,
            idle_time=0.0,
            errors_count=0,
            captcha_encounters=0
        )
    
    def _init_detection_triggers(self) -> Dict:
        """Initialize detection pattern triggers"""
        return {
            'rapid_clicking': {'threshold': 10, 'timeframe': 60},  # 10 clicks per minute
            'rapid_applications': {'threshold': 5, 'timeframe': 300},  # 5 apps per 5 minutes
            'repetitive_patterns': {'threshold': 3, 'timeframe': 1800},  # 3 same actions in 30 min
            'unusual_navigation': {'threshold': 20, 'timeframe': 600},  # 20 page changes in 10 min
            'captcha_frequency': {'threshold': 3, 'timeframe': 3600}  # 3 captchas per hour
        }
    
    def _setup_logging(self) -> logging.Logger:
        """Setup comprehensive logging"""
        logger = logging.getLogger('AntiDetection')
        logger.setLevel(logging.INFO)
        
        # Create file handler
        log_file = f"anti_ban_logs_{datetime.now().strftime('%Y%m%d')}.log"
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        
        return logger
    
    def _convert_datetime_to_str(self, obj):
        """Recursively convert datetime objects to ISO format strings"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, dict):
            return {key: self._convert_datetime_to_str(value) for key, value in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._convert_datetime_to_str(item) for item in obj]
        else:
            return obj
    
    def create_stealth_driver(self) -> webdriver.Chrome:
        """Create stealth browser instance with advanced anti-detection"""
        options = Options()
        
        # Get and apply random fingerprint
        fingerprint = self.fingerprint_manager.get_random_fingerprint()
        self.fingerprint_manager.apply_fingerprint(options, fingerprint)
        
        # Advanced stealth options
        stealth_arguments = [
            '--no-sandbox',
            '--disable-dev-shm-usage',
            '--disable-blink-features=AutomationControlled',
            '--disable-extensions',
            '--disable-plugins',
            '--disable-images',  # Faster loading
            '--disable-javascript-harmony-shipping',
            '--disable-background-timer-throttling',
            '--disable-backgrounding-occluded-windows',
            '--disable-renderer-backgrounding',
            '--disable-features=TranslateUI',
            '--disable-ipc-flooding-protection',
            '--disable-background-networking',
            '--disable-default-apps',
            '--disable-sync',
            '--disable-speech-api',
            '--disable-web-security',
            '--disable-permissions-api',
            '--disable-notification-api',
            '--disable-desktop-notifications',
            '--disable-extensions-file-access-check',
            '--disable-extensions-http-throttling',
            '--aggressive-cache-discard',
            '--memory-pressure-off',
            '--max_old_space_size=4096'
        ]
        
        for arg in stealth_arguments:
            options.add_argument(arg)
        
        # Exclude automation indicators
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # Create driver
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        # Additional stealth measures
        self._apply_advanced_stealth(driver, fingerprint)
        
        self.logger.info(f"Created stealth driver with fingerprint: {fingerprint['user_agent'][:50]}...")
        return driver
    
    def _apply_advanced_stealth(self, driver: webdriver.Chrome, fingerprint: Dict):
        """Apply advanced stealth measures to existing driver"""
        # Remove webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        # Modify navigator properties
        script = f"""
        Object.defineProperty(navigator, 'languages', {{
            get: function() {{ return ['{fingerprint['language']}']; }}
        }});
        
        Object.defineProperty(navigator, 'plugins', {{
            get: function() {{ return [1, 2, 3, 4, 5]; }}
        }});
        
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: function() {{ return {fingerprint['hardware_concurrency']}; }}
        }});
        
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: function() {{ return {fingerprint['device_memory']}; }}
        }});
        
        // Modify WebGL fingerprint
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) {{ return '{fingerprint['webgl_vendor']}'; }}
            if (parameter === 37446) {{ return '{fingerprint['webgl_renderer']}'; }}
            return getParameter.apply(this, arguments);
        }};
        
        // Modify screen properties
        Object.defineProperty(screen, 'width', {{
            get: function() {{ return {fingerprint['viewport_size'][0]}; }}
        }});
        Object.defineProperty(screen, 'height', {{
            get: function() {{ return {fingerprint['viewport_size'][1]}; }}
        }});
        """
        
        driver.execute_script(script)
    
    async def simulate_human_behavior(self, driver: webdriver.Chrome, action_type: str = "general"):
        """Simulate human-like behavior patterns"""
        if action_type == "reading":
            # Simulate reading behavior
            await self._simulate_reading(driver)
        elif action_type == "form_filling":
            # Simulate form filling behavior
            await self._simulate_form_interaction(driver)
        elif action_type == "navigation":
            # Simulate navigation behavior
            await self._simulate_navigation(driver)
        else:
            # General human behavior
            await self._simulate_general_activity(driver)
    
    async def _simulate_reading(self, driver: webdriver.Chrome):
        """Simulate human reading patterns"""
        # Random scrolling while reading
        scroll_pattern = self.behavior_pattern.scroll_pattern()
        
        for scroll_amount in scroll_pattern:
            driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
            self.session_metrics.scroll_events += 1
            
            # Pause as if reading
            await asyncio.sleep(self.behavior_pattern.human_delay(1, 3))
            
            # Occasional mouse movement
            if random.random() < 0.3:
                await self._move_mouse_randomly(driver)
    
    async def _simulate_form_interaction(self, driver: webdriver.Chrome):
        """Simulate human form filling behavior"""
        # Pause before interacting (thinking time)
        await asyncio.sleep(self.behavior_pattern.human_delay(1, 4))
        
        # Simulate occasional tab navigation
        if random.random() < 0.2:
            ActionChains(driver).send_keys_to_element(driver.find_element(By.TAG_NAME, "body"), "\t").perform()
            await asyncio.sleep(self.behavior_pattern.human_delay(0.5, 1.5))
    
    async def _simulate_navigation(self, driver: webdriver.Chrome):
        """Simulate human navigation patterns"""
        # Brief pause before navigation
        await asyncio.sleep(self.behavior_pattern.human_delay(0.5, 2))
        
        # Simulate back button occasionally (user changed mind)
        if random.random() < 0.1:
            driver.back()
            await asyncio.sleep(self.behavior_pattern.human_delay(2, 4))
            driver.forward()
        
        self.session_metrics.page_views += 1
    
    async def _simulate_general_activity(self, driver: webdriver.Chrome):
        """Simulate general human activity"""
        activities = [
            self._move_mouse_randomly,
            self._random_scroll,
            self._pause_activity
        ]
        
        activity = random.choice(activities)
        await activity(driver)
    
    async def _move_mouse_randomly(self, driver: webdriver.Chrome):
        """Move mouse in natural patterns"""
        action = ActionChains(driver)
        movement_path = self.behavior_pattern.mouse_movement_pattern()
        
        for x, y in movement_path[:3]:  # Limit movements
            action.move_by_offset(random.randint(-5, 5), random.randint(-5, 5))
            await asyncio.sleep(0.1)
        
        action.perform()
        self.session_metrics.mouse_movements += 1
    
    async def _random_scroll(self, driver: webdriver.Chrome):
        """Perform random scrolling"""
        scroll_direction = random.choice(['up', 'down'])
        scroll_amount = random.randint(100, 300)
        
        if scroll_direction == 'up':
            scroll_amount = -scroll_amount
        
        driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
        self.session_metrics.scroll_events += 1
        await asyncio.sleep(self.behavior_pattern.human_delay(0.5, 2))
    
    async def _pause_activity(self, driver: webdriver.Chrome):
        """Simulate user pausing to think/read"""
        pause_duration = self.behavior_pattern.human_delay(2, 8)
        await asyncio.sleep(pause_duration)
        self.session_metrics.idle_time += pause_duration
    
    def should_take_break(self) -> bool:
        """Determine if bot should take a break"""
        current_time = datetime.now()
        session_duration = (current_time - self.session_metrics.start_time).total_seconds() / 60
        
        # Check various break conditions
        conditions = [
            # Session duration limit
            session_duration >= self.config['max_session_duration_minutes'],
            
            # Applications limit
            self.session_metrics.applications_count >= self.config['max_applications_per_session'],
            
            # Error threshold
            self.session_metrics.errors_count >= self.config['error_threshold'],
            
            # Captcha encounters
            self.session_metrics.captcha_encounters >= 2
        ]
        
        if any(conditions):
            self.logger.info(f"Break recommended - Duration: {session_duration:.1f}min, "
                           f"Applications: {self.session_metrics.applications_count}, "
                           f"Errors: {self.session_metrics.errors_count}")
            return True
        
        return False
    
    async def take_smart_break(self):
        """Take an intelligent break with varied duration"""
        break_duration = random.uniform(
            self.config['break_duration_minutes'] * 0.8,
            self.config['break_duration_minutes'] * 1.5
        )
        
        self.logger.info(f"Taking break for {break_duration:.1f} minutes")
        print(f"🛌 Taking strategic break for {break_duration:.1f} minutes...")
        
        await asyncio.sleep(break_duration * 60)
        
        # Reset session metrics after break
        self.session_metrics = self._init_session_metrics()
    
    def detect_captcha(self, driver: webdriver.Chrome) -> bool:
        """Detect if CAPTCHA is present with LinkedIn-specific checks"""
        captcha_indicators = [
            "recaptcha",
            "captcha",
            "security check",
            "verify you're human",
            "prove you're not a robot",
            "challenge",
            "verify your identity",
            "unusual activity"
        ]
        
        # LinkedIn-specific selectors
        captcha_selectors = [
            "#recaptcha",
            ".captcha-container",
            "[data-testid='challenge']",
            ".security-challenge",
            "iframe[src*='recaptcha']",
            ".challenge-container",
            "[aria-label*='captcha']",
            "[aria-label*='challenge']"
        ]
        
        try:
            # Check page source
            page_source = driver.page_source.lower()
            for indicator in captcha_indicators:
                if indicator in page_source:
                    self.session_metrics.captcha_encounters += 1
                    self.logger.warning(f"CAPTCHA detected: {indicator}")
                    return True
            
            # Check for CAPTCHA elements
            from selenium.webdriver.common.by import By
            for selector in captcha_selectors:
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    if element.is_displayed():
                        self.session_metrics.captcha_encounters += 1
                        self.logger.warning(f"CAPTCHA element detected: {selector}")
                        return True
                except:
                    continue
            
            # Check URL for challenge indicators
            current_url = driver.current_url.lower()
            if any(word in current_url for word in ['challenge', 'captcha', 'verify', 'security']):
                self.session_metrics.captcha_encounters += 1
                self.logger.warning("CAPTCHA detected in URL")
                return True
                
        except Exception as e:
            self.logger.error(f"Error detecting CAPTCHA: {str(e)}")
        
        return False
    
    def detect_rate_limiting(self, driver: webdriver.Chrome) -> bool:
        """Detect if account is being rate limited with LinkedIn-specific checks"""
        rate_limit_indicators = [
            "try again later",
            "too many requests",
            "rate limit",
            "temporarily unavailable",
            "please wait",
            "suspicious activity",
            "unusual activity detected",
            "account temporarily restricted",
            "too many applications",
            "please slow down",
            "action blocked",
            "temporarily blocked"
        ]
        
        # LinkedIn-specific error messages
        linkedin_specific = [
            "we've noticed unusual activity",
            "verify your identity",
            "account verification required",
            "security check required",
            "unusual sign-in activity"
        ]
        
        try:
            page_source = driver.page_source.lower()
            
            # Check general indicators
            for indicator in rate_limit_indicators:
                if indicator in page_source:
                    self.logger.warning(f"Rate limiting detected: {indicator}")
                    return True
            
            # Check LinkedIn-specific indicators
            for indicator in linkedin_specific:
                if indicator in page_source:
                    self.logger.warning(f"LinkedIn-specific rate limiting: {indicator}")
                    return True
            
            # Check for error banners/alerts
            from selenium.webdriver.common.by import By
            error_selectors = [
                ".artdeco-inline-notification--error",
                "[data-test-id='error-banner']",
                ".error-message",
                ".alert-error",
                "[role='alert']"
            ]
            
            for selector in error_selectors:
                try:
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            text = element.text.lower()
                            if any(indicator in text for indicator in rate_limit_indicators + linkedin_specific):
                                self.logger.warning(f"Rate limiting detected in error banner")
                                return True
                except:
                    continue
                    
        except Exception as e:
            self.logger.error(f"Error detecting rate limiting: {str(e)}")
        
        return False
    
    def handle_detection_event(self, event_type: str, driver: webdriver.Chrome = None):
        """Handle various detection events"""
        handlers = {
            'captcha': self._handle_captcha,
            'rate_limit': self._handle_rate_limit,
            'suspicious_activity': self._handle_suspicious_activity,
            'account_restriction': self._handle_account_restriction
        }
        
        if event_type in handlers:
            handlers[event_type](driver)
        else:
            self.logger.warning(f"Unknown detection event: {event_type}")
    
    async def _handle_captcha(self, driver: webdriver.Chrome):
        """Handle CAPTCHA encounters"""
        self.logger.warning("CAPTCHA encountered - entering cooldown mode")
        
        # Close current session
        if driver:
            driver.quit()
        
        # Extended cooldown
        cooldown_duration = self.config['captcha_cooldown_minutes']
        await asyncio.sleep(cooldown_duration * 60)
        
        # Reset fingerprint for next session
        self.fingerprint_manager.get_random_fingerprint()
    
    async def _handle_rate_limit(self, driver: webdriver.Chrome):
        """Handle rate limiting"""
        self.logger.warning("Rate limiting detected - taking extended break")
        
        # Take longer break
        break_duration = random.uniform(60, 180)  # 1-3 hours
        await asyncio.sleep(break_duration * 60)
    
    async def _handle_suspicious_activity(self, driver: webdriver.Chrome):
        """Handle suspicious activity detection"""
        self.logger.warning("Suspicious activity detected - switching to maximum stealth mode")
        
        # Enable maximum stealth
        self.config['stealth_mode'] = True
        
        # Take break and reset session
        await self.take_smart_break()
    
    async def _handle_account_restriction(self, driver: webdriver.Chrome):
        """Handle account restrictions"""
        self.logger.critical("Account restriction detected - stopping bot")
        raise Exception("Account restricted - manual intervention required")
    
    def get_application_delay(self) -> float:
        """Get intelligent delay between applications with LinkedIn-specific adjustments"""
        base_delay = random.uniform(
            self.config['min_delay_between_applications'],
            self.config['max_delay_between_applications']
        )
        
        # Adjust based on recent activity
        if self.session_metrics.applications_count > 10:
            base_delay *= 1.5  # Slower when many applications
        
        if self.session_metrics.errors_count > 2:
            base_delay *= 2.0  # Much slower if errors occurred
        
        # LinkedIn-specific: Add extra delay if we've seen any warnings
        if self.session_metrics.captcha_encounters > 0:
            base_delay *= 1.8  # Extra cautious after CAPTCHA
        
        # Add random variation to avoid patterns
        variation = random.uniform(0.9, 1.1)
        base_delay *= variation
        
        # Ensure minimum delay (LinkedIn typically needs at least 2-3 minutes)
        min_safe_delay = 120  # 2 minutes minimum
        if base_delay < min_safe_delay:
            base_delay = min_safe_delay + random.uniform(0, 60)
        
        return base_delay
    
    def log_activity(self, activity_type: str, details: Dict = None):
        """Log activity for monitoring"""
        log_data = {
            'timestamp': datetime.now().isoformat(),
            'activity_type': activity_type,
            'session_metrics': asdict(self.session_metrics),
            'details': details or {}
        }
        
        # Convert datetime objects in details before JSON serialization
        safe_details = self._convert_datetime_to_str(details or {}) if details else {}
        
        try:
            self.logger.info(f"Activity: {activity_type} | {json.dumps(safe_details)}")
        except (TypeError, ValueError) as e:
            # Fallback if JSON serialization still fails
            self.logger.info(f"Activity: {activity_type} | {str(safe_details)}")
        
        # Update session metrics
        if activity_type == 'application':
            self.session_metrics.applications_count += 1
        elif activity_type == 'click':
            self.session_metrics.clicks += 1
        elif activity_type == 'typing':
            self.session_metrics.typing_events += 1
        elif activity_type == 'error':
            self.session_metrics.errors_count += 1
    
    async def safe_type(self, element, text: str, driver: webdriver.Chrome):
        """Type text with human-like behavior and anti-detection"""
        # Clear field first
        element.clear()
        await asyncio.sleep(self.behavior_pattern.human_delay(0.2, 0.5))
        
        # Type with variable speed
        for i, char in enumerate(text):
            element.send_keys(char)
            
            # Variable typing speed
            typing_delay = self.behavior_pattern.typing_speed()
            
            # Occasional longer pauses (thinking/correcting)
            if random.random() < 0.1:  # 10% chance
                typing_delay *= random.uniform(2, 5)
            
            await asyncio.sleep(typing_delay)
            
            # Log typing activity
            if i % 10 == 0:  # Log every 10 characters
                self.log_activity('typing', {'chars_typed': i + 1})
    
    async def safe_click(self, element, driver: webdriver.Chrome):
        """Click with human-like behavior and verification"""
        # Move to element first (more human-like)
        ActionChains(driver).move_to_element(element).perform()
        await asyncio.sleep(self.behavior_pattern.human_delay(0.3, 0.8))
        
        # Click
        element.click()
        self.log_activity('click')
        
        # Brief pause after click
        await asyncio.sleep(self.behavior_pattern.human_delay(0.5, 1.5))
    
    def save_session_data(self):
        """Save session data for analysis"""
        session_file = f"session_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        session_data = {
            'session_metrics': asdict(self.session_metrics),
            'config': self.config,
            'fingerprint': self.fingerprint_manager.current_fingerprint,
            'timestamp': datetime.now().isoformat()
        }
        
        # Convert datetime objects to strings for JSON serialization
        session_data = self._convert_datetime_to_str(session_data)
        
        try:
            with open(session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            self.logger.info(f"Session data saved to {session_file}")
        except Exception as e:
            self.logger.error(f"Failed to save session data: {str(e)}")
            print(f"⚠️  Could not save session data: {str(e)}")

# Usage example for integration
class AntiDetectionMixin:
    """Mixin class to add anti-detection capabilities to existing bot"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.anti_detection = AntiDetectionManager()
    
    def create_protected_driver(self):
        """Create driver with anti-detection"""
        return self.anti_detection.create_stealth_driver()
    
    async def protected_application_flow(self, job_data: Dict):
        """Application flow with anti-detection measures"""
        # Check if break is needed
        if self.anti_detection.should_take_break():
            await self.anti_detection.take_smart_break()
        
        # Get intelligent delay
        delay = self.anti_detection.get_application_delay()
        await asyncio.sleep(delay)
        
        # Log application start
        self.anti_detection.log_activity('application', {
            'job_title': job_data.get('title'),
            'company': job_data.get('company')
        })
        
        return True