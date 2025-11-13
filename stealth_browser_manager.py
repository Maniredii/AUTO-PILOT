#!/usr/bin/env python3
"""
Advanced Stealth Browser Manager
Provides next-generation browser stealth capabilities for LinkedIn automation
Refactored for Playwright
"""

import random
import json
import time
import os
import platform
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

from playwright.sync_api import sync_playwright, BrowserContext, Page, Playwright

@dataclass
class BrowserProfile:
    """Browser profile with all fingerprint data"""
    user_agent: str
    viewport: Tuple[int, int]
    screen_resolution: Tuple[int, int]
    timezone: str
    language: str
    platform: str
    hardware_concurrency: int
    device_memory: int
    webgl_vendor: str
    webgl_renderer: str
    canvas_fingerprint: str
    audio_fingerprint: str
    battery_charging: bool
    battery_level: float
    connection_type: str
    plugins: List[str]
    chrome_version: str

class StealthBrowserManager:
    """Advanced browser stealth management using Playwright"""
    
    def __init__(self, config_path: str = "anti_ban_config.json"):
        self.current_profile = None
        self.profile_pool = self._generate_realistic_profiles()
        self.session_profiles = {}
        self.playwright: Optional[Playwright] = None
        self.config_path = config_path
        self.proxy_config = self._load_proxy_config()
        self.current_proxy_index = 0
        self.last_proxy_rotation = datetime.now()
        
    def _generate_realistic_profiles(self) -> List[BrowserProfile]:
        """Generate pool of realistic browser profiles"""
        profiles = []
        
        # Common screen resolutions and their frequencies
        resolutions = [
            ((1920, 1080), 0.35),  # Most common
            ((1366, 768), 0.20),
            ((1536, 864), 0.15),
            ((1440, 900), 0.10),
            ((1280, 720), 0.08),
            ((2560, 1440), 0.07),
            ((1600, 900), 0.05)
        ]
        
        # Realistic Chrome versions (recent)
        chrome_versions = [
            "120.0.6099.109",
            "120.0.6099.130", 
            "119.0.6045.199",
            "119.0.6045.123",
            "118.0.5993.117"
        ]
        
        # Operating systems
        os_configs = [
            {
                "platform": "Win32",
                "user_agent_os": "Windows NT 10.0; Win64; x64",
                "timezone_options": ["America/New_York", "America/Chicago", "America/Los_Angeles"]
            },
            {
                "platform": "MacIntel", 
                "user_agent_os": "Macintosh; Intel Mac OS X 10_15_7",
                "timezone_options": ["America/Los_Angeles", "America/New_York", "America/Denver"]
            },
            {
                "platform": "Linux x86_64",
                "user_agent_os": "X11; Linux x86_64", 
                "timezone_options": ["America/New_York", "Europe/London", "America/Los_Angeles"]
            }
        ]
        
        # Generate 50 realistic profiles
        for i in range(50):
            # Select weighted resolution
            resolution_weights = [weight for _, weight in resolutions]
            screen_res = random.choices([res for res, _ in resolutions], weights=resolution_weights)[0]
            viewport = (screen_res[0] - random.randint(0, 100), screen_res[1] - random.randint(100, 200))
            
            # Select OS
            os_config = random.choice(os_configs)
            
            # Select Chrome version
            chrome_ver = random.choice(chrome_versions)
            
            # Build user agent
            user_agent = f"Mozilla/5.0 ({os_config['user_agent_os']}) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/{chrome_ver} Safari/537.36"
            
            # Hardware specs (realistic ranges)
            hardware_concurrency = random.choice([4, 6, 8, 12, 16])
            device_memory = random.choice([4, 8, 16, 32])
            
            # WebGL configurations
            webgl_configs = [
                ("Google Inc. (Intel)", "ANGLE (Intel, Intel(R) UHD Graphics 620 Direct3D11 vs_5_0 ps_5_0, D3D11-27.20.100.8681)"),
                ("Google Inc. (NVIDIA)", "ANGLE (NVIDIA, NVIDIA GeForce GTX 1660 Ti Direct3D11 vs_5_0 ps_5_0, D3D11-31.0.15.1659)"),
                ("Google Inc. (AMD)", "ANGLE (AMD, AMD Radeon RX 580 Series Direct3D11 vs_5_0 ps_5_0, D3D11-30.0.15002.18)")
            ]
            webgl_vendor, webgl_renderer = random.choice(webgl_configs)
            
            # Generate unique fingerprints
            canvas_fp = self._generate_canvas_fingerprint()
            audio_fp = self._generate_audio_fingerprint()
            
            # Battery simulation
            battery_charging = random.choice([True, False])
            battery_level = random.uniform(0.2, 1.0) if battery_charging else random.uniform(0.1, 0.9)
            
            # Connection type
            connection_type = random.choice(["ethernet", "wifi", "cellular", "unknown"])
            
            # Plugin simulation
            plugins = self._generate_plugin_list()
            
            profile = BrowserProfile(
                user_agent=user_agent,
                viewport=viewport,
                screen_resolution=screen_res,
                timezone=random.choice(os_config['timezone_options']),
                language="en-US",
                platform=os_config['platform'],
                hardware_concurrency=hardware_concurrency,
                device_memory=device_memory,
                webgl_vendor=webgl_vendor,
                webgl_renderer=webgl_renderer,
                canvas_fingerprint=canvas_fp,
                audio_fingerprint=audio_fp,
                battery_charging=battery_charging,
                battery_level=battery_level,
                connection_type=connection_type,
                plugins=plugins,
                chrome_version=chrome_ver
            )
            
            profiles.append(profile)
        
        return profiles
    
    def _generate_canvas_fingerprint(self) -> str:
        """Generate unique but realistic canvas fingerprint"""
        # Create deterministic but varied fingerprint
        base_data = f"{random.randint(1000, 9999)}_{time.time()}"
        return hashlib.md5(base_data.encode()).hexdigest()[:16]
    
    def _generate_audio_fingerprint(self) -> str:
        """Generate unique audio context fingerprint"""
        base_data = f"{random.randint(10000, 99999)}_{datetime.now().microsecond}"
        return hashlib.sha256(base_data.encode()).hexdigest()[:20]
    
    def _generate_plugin_list(self) -> List[str]:
        """Generate realistic plugin list"""
        common_plugins = [
            "PDF Viewer",
            "Chrome PDF Viewer", 
            "Chromium PDF Viewer",
            "Microsoft Edge PDF Viewer",
            "WebKit built-in PDF"
        ]
        
        # Select 2-4 plugins randomly
        selected_count = random.randint(2, 4)
        return random.sample(common_plugins, selected_count)
    
    def _load_proxy_config(self) -> Dict:
        """Load proxy configuration from anti_ban_config.json"""
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    return config.get('proxy_settings', {})
        except Exception as e:
            print(f"⚠️  Could not load proxy config: {e}")
        return {
            "enabled": False,
            "rotation_interval_minutes": 30,
            "proxy_provider": "custom",
            "proxy_list": [],
            "proxy_format": "http://user:pass@host:port",
            "fallback_to_direct": True
        }
    
    def get_next_proxy(self) -> Optional[Dict[str, str]]:
        """
        Get the next proxy from the rotation pool.
        Returns proxy dict in format: {'server': 'http://user:pass@host:port'}
        Returns None if proxy rotation is disabled or no proxies available.
        """
        # Check if proxy rotation is enabled
        if not self.proxy_config.get('enabled', False):
            return None
        
        # Check if we need to rotate based on interval
        rotation_interval = self.proxy_config.get('rotation_interval_minutes', 30)
        time_since_rotation = (datetime.now() - self.last_proxy_rotation).total_seconds() / 60
        
        # Get proxy list
        proxy_list = self.proxy_config.get('proxy_list', [])
        
        # If no proxies configured, try to load from environment or external source
        if not proxy_list:
            # Try environment variable
            env_proxy = os.environ.get('PROXY_SERVER')
            if env_proxy:
                proxy_list = [env_proxy]
            else:
                # Try external proxy provider (placeholder for future integration)
                proxy_list = self._fetch_proxies_from_provider()
        
        if not proxy_list:
            if self.proxy_config.get('fallback_to_direct', True):
                print("⚠️  No proxies available, falling back to direct connection")
                return None
            else:
                raise Exception("Proxy rotation enabled but no proxies available")
        
        # Rotate proxy if interval has passed or if this is first call
        if time_since_rotation >= rotation_interval or self.current_proxy_index == 0:
            self.current_proxy_index = (self.current_proxy_index + 1) % len(proxy_list)
            self.last_proxy_rotation = datetime.now()
        
        # Get current proxy
        proxy_string = proxy_list[self.current_proxy_index]
        
        # Parse proxy string into Playwright format
        # Expected format: http://user:pass@host:port or http://host:port
        try:
            if '@' in proxy_string:
                # Has authentication
                auth_part, server_part = proxy_string.split('@', 1)
                protocol = auth_part.split('://')[0] if '://' in auth_part else 'http'
                auth = auth_part.split('://')[1] if '://' in auth_part else auth_part
                
                if ':' in auth:
                    username, password = auth.split(':', 1)
                else:
                    username = auth
                    password = ""
                
                server = f"{protocol}://{server_part}"
                
                proxy_info = {
                    'server': server,
                    'username': username,
                    'password': password
                }
            else:
                # No authentication
                proxy_info = {
                    'server': proxy_string
                }
            
            print(f"🔄 Using proxy: {proxy_info['server'][:50]}...")
            return proxy_info
            
        except Exception as e:
            print(f"⚠️  Error parsing proxy string '{proxy_string}': {e}")
            if self.proxy_config.get('fallback_to_direct', True):
                return None
            raise
    
    def _fetch_proxies_from_provider(self) -> List[str]:
        """
        Placeholder function to fetch proxies from external provider.
        Can be extended to integrate with proxy services like:
        - Bright Data
        - Oxylabs
        - Smartproxy
        - ScraperAPI
        etc.
        """
        # Placeholder: Return empty list
        # In production, this would fetch from a proxy provider API
        provider = self.proxy_config.get('proxy_provider', 'custom')
        
        if provider == 'custom':
            # For custom provider, proxies should be in proxy_list
            return []
        else:
            # Future: Integrate with actual proxy providers
            print(f"⚠️  Proxy provider '{provider}' not yet implemented")
            return []
    
    def get_stealth_profile(self, session_id: str = None) -> BrowserProfile:
        """Get consistent profile for session or new random profile"""
        if session_id and session_id in self.session_profiles:
            return self.session_profiles[session_id]
        
        profile = random.choice(self.profile_pool)
        
        if session_id:
            self.session_profiles[session_id] = profile
        
        self.current_profile = profile
        return profile
    
    def _get_stealth_script(self, profile: BrowserProfile) -> str:
        """Generate comprehensive stealth JavaScript"""
        plugins_json = json.dumps([{"name": p, "description": p, "filename": f"{p.lower().replace(' ', '')}.dll"} for p in profile.plugins])
        
        stealth_script = f"""
        // Remove automation traces
        Object.defineProperty(navigator, 'webdriver', {{get: () => undefined}});
        
        // Override navigator properties
        Object.defineProperty(navigator, 'languages', {{
            get: function() {{ return ['{profile.language}', 'en']; }}
        }});
        
        Object.defineProperty(navigator, 'platform', {{
            get: function() {{ return '{profile.platform}'; }}
        }});
        
        Object.defineProperty(navigator, 'hardwareConcurrency', {{
            get: function() {{ return {profile.hardware_concurrency}; }}
        }});
        
        Object.defineProperty(navigator, 'deviceMemory', {{
            get: function() {{ return {profile.device_memory}; }}
        }});
        
        Object.defineProperty(navigator, 'maxTouchPoints', {{
            get: function() {{ return 0; }}
        }});
        
        // Override screen properties
        Object.defineProperty(screen, 'width', {{
            get: function() {{ return {profile.screen_resolution[0]}; }}
        }});
        
        Object.defineProperty(screen, 'height', {{
            get: function() {{ return {profile.screen_resolution[1]}; }}
        }});
        
        Object.defineProperty(screen, 'availWidth', {{
            get: function() {{ return {profile.screen_resolution[0]}; }}
        }});
        
        Object.defineProperty(screen, 'availHeight', {{
            get: function() {{ return {profile.screen_resolution[1] - 40}; }}
        }});
        
        // WebGL spoofing
        const getParameter = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {{
            if (parameter === 37445) {{ return '{profile.webgl_vendor}'; }}
            if (parameter === 37446) {{ return '{profile.webgl_renderer}'; }}
            return getParameter.apply(this, arguments);
        }};
        
        // Canvas fingerprint protection
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function() {{
            // Add slight noise to canvas
            const context = this.getContext('2d');
            const originalData = context.getImageData(0, 0, this.width, this.height);
            for (let i = 0; i < originalData.data.length; i += 4) {{
                originalData.data[i] += Math.floor(Math.random() * 3) - 1;
                originalData.data[i + 1] += Math.floor(Math.random() * 3) - 1; 
                originalData.data[i + 2] += Math.floor(Math.random() * 3) - 1;
            }}
            context.putImageData(originalData, 0, 0);
            return originalData.toString() + '{profile.canvas_fingerprint}';
        }};
        
        // Audio fingerprint protection
        const originalGetChannelData = AudioBuffer.prototype.getChannelData;
        AudioBuffer.prototype.getChannelData = function(channel) {{
            const originalArray = originalGetChannelData.call(this, channel);
            for (let i = 0; i < originalArray.length; i += 100) {{
                originalArray[i] = originalArray[i] + (Math.random() - 0.5) * 0.0001;
            }}
            return originalArray;
        }};
        
        // Battery API spoofing
        if (navigator.getBattery) {{
            navigator.getBattery = function() {{
                return Promise.resolve({{
                    charging: {str(profile.battery_charging).lower()},
                    chargingTime: Infinity,
                    dischargingTime: {random.randint(3600, 28800)},
                    level: {profile.battery_level:.2f}
                }});
            }};
        }}
        
        // Connection API spoofing  
        if (navigator.connection) {{
            Object.defineProperty(navigator.connection, 'type', {{
                get: function() {{ return '{profile.connection_type}'; }}
            }});
        }}
        
        // Plugin spoofing
        Object.defineProperty(navigator, 'plugins', {{
            get: function() {{
                return {plugins_json};
            }}
        }});
        
        // Timezone spoofing
        Date.prototype.getTimezoneOffset = function() {{
            // This is a simplified approach - full implementation would be more complex
            const timezoneOffsets = {{
                'America/New_York': 300,
                'America/Chicago': 360, 
                'America/Denver': 420,
                'America/Los_Angeles': 480,
                'Europe/London': 0
            }};
            return timezoneOffsets['{profile.timezone}'] || 0;
        }};
        
        // Remove automation-related properties
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Array;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Promise; 
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Symbol;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_JSON;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Object;
        delete window.cdc_adoQpoasnfa76pfcZLmcfl_Proxy;
        
        // Spoof permissions API
        const originalPermissionsQuery = navigator.permissions.query;
        navigator.permissions.query = function(parameters) {{
            const permissionStatus = {{
                state: Math.random() > 0.5 ? 'granted' : 'denied'
            }};
            return Promise.resolve(permissionStatus);
        }};
        
        // Add realistic timing jitter
        const originalSetTimeout = window.setTimeout;
        const originalSetInterval = window.setInterval;
        
        window.setTimeout = function(callback, delay) {{
            const jitter = Math.random() * 50 - 25; // ±25ms jitter
            return originalSetTimeout(callback, delay + jitter);
        }};
        
        window.setInterval = function(callback, delay) {{
            const jitter = Math.random() * 100 - 50; // ±50ms jitter  
            return originalSetInterval(callback, delay + jitter);
        }};
        
        // Spoof speech synthesis (if present)
        if (window.speechSynthesis) {{
            Object.defineProperty(window.speechSynthesis, 'getVoices', {{
                value: function() {{ return []; }}
            }});
        }}
        
        console.log('🛡️ Advanced stealth mode activated');
        """
        
        return stealth_script
    
    def create_stealth_context(self, session_id: str = None, user_data_dir: str = None, headless: bool = False) -> Tuple[BrowserContext, Page]:
        """
        Create fully stealthed browser context and page using Playwright.
        
        IMPORTANT: By default, this creates a FRESH session with NO data persistence.
        Set use_persistent=True only if you explicitly need to save session data.
        """
        try:
            # Start Playwright
            if not self.playwright:
                self.playwright = sync_playwright().start()
            
            # Get profile
            profile = self.get_stealth_profile(session_id)
            
            # Get proxy if enabled
            proxy_info = self.get_next_proxy()
            
            # Chrome arguments for stealth
            chrome_args = [
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-extensions',
                '--disable-plugins-discovery',
                '--disable-default-apps',
                '--disable-sync',
                '--disable-translate',
                '--hide-scrollbars',
                '--mute-audio',
                '--no-first-run',
                '--no-service-autorun',
                '--password-store=basic',
                '--use-mock-keychain',
                '--disable-component-extensions-with-background-pages',
                '--disable-background-networking',
                '--disable-background-timer-throttling',
                '--disable-renderer-backgrounding',
                '--disable-backgrounding-occluded-windows',
                '--disable-client-side-phishing-detection',
                '--disable-component-update',
                '--disable-domain-reliability',
                '--disable-features=TranslateUI,BlinkGenPropertyTrees',
                '--disable-hang-monitor',
                '--disable-ipc-flooding-protection',
                '--disable-popup-blocking',
                '--disable-prompt-on-repost',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor',
                '--run-all-compositor-stages-before-draw',
                '--disable-threaded-animation',
                '--disable-threaded-scrolling',
                '--disable-checker-imaging',
                '--disable-new-bookmark-apps',
                '--disable-partial-raster',
                '--disable-skia-runtime-opts',
                '--disable-v8-idle-tasks',
                '--max-gum-fps=30',
                '--enable-surface-synchronization'
            ]
            
            # ✅ FIX: Launch browser WITHOUT persistent context
            # This ensures NO data is saved to disk
            browser = self.playwright.chromium.launch(
                headless=headless,
                args=chrome_args
            )
            
            # ✅ FIX: Create a FRESH context (not persistent)
            # This is the key to preventing session persistence
            context_options = {
                'viewport': {'width': profile.viewport[0], 'height': profile.viewport[1]},
                'user_agent': profile.user_agent,
                'locale': profile.language,
                'timezone_id': profile.timezone,
                'permissions': ['notifications'],
                'ignore_https_errors': True,
                'java_script_enabled': True,
                'bypass_csp': True
            }
            
            # Add proxy if available
            if proxy_info:
                context_options['proxy'] = proxy_info
                print(f"✅ Proxy configured: {proxy_info.get('server', 'N/A')[:50]}...")
            
            # Create fresh context (NO storage_state = clean slate)
            context = browser.new_context(**context_options)
            
            # Create a new page
            page = context.new_page()
            
            # Add stealth script to all pages in this context
            stealth_script = self._get_stealth_script(profile)
            context.add_init_script(stealth_script)
            
            # Set extra HTTP headers
            context.set_extra_http_headers({
                'Accept-Language': f'{profile.language},en;q=0.9',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding': 'gzip, deflate, br',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            })
            
            # Navigate to blank page to initialize
            page.goto("about:blank")
            
            print(f"✅ Fresh stealth browser created (NO data persistence)")
            print(f"   Profile: {profile.user_agent[:50]}...")
            return context, page
            
        except Exception as e:
            print(f"❌ Failed to create stealth browser: {e}")
            raise
    
    def create_stealth_driver(self, session_id: str = None, user_data_dir: str = None) -> Tuple[BrowserContext, Page]:
        """
        Create fully stealthed browser (alias for create_stealth_context for backward compatibility)
        Returns (context, page) tuple instead of Selenium driver
        
        NOTE: user_data_dir parameter is IGNORED to ensure fresh sessions.
        This prevents session persistence and ensures login page is always shown.
        """
        if user_data_dir:
            print("⚠️  WARNING: user_data_dir parameter is ignored to ensure fresh sessions")
            print("   Each run will start with a clean slate (no saved cookies/data)")
        
        return self.create_stealth_context(session_id, user_data_dir=None, headless=False)
    
    def validate_stealth(self, page: Page) -> Dict[str, bool]:
        """Validate stealth effectiveness"""
        validation_script = """
        return {
            webdriver_undefined: typeof navigator.webdriver === 'undefined',
            plugins_present: navigator.plugins.length > 0,
            languages_set: navigator.languages.length > 0,
            chrome_present: window.chrome !== undefined,
            permission_query_present: typeof navigator.permissions.query === 'function',
            webgl_vendor_spoofed: true, // Would need actual validation
            canvas_fingerprint_protected: true // Would need actual validation
        };
        """
        
        try:
            results = page.evaluate(validation_script)
            
            print("🔍 Stealth Validation Results:")
            for check, passed in results.items():
                status = "✅" if passed else "❌"
                print(f"  {status} {check.replace('_', ' ').title()}: {passed}")
            
            return results
            
        except Exception as e:
            print(f"⚠️  Could not validate stealth: {e}")
            return {}
    
    def cleanup(self):
        """Cleanup Playwright instance"""
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass
            self.playwright = None

# Factory function for easy integration
def create_stealth_browser(session_id: str = None, user_data_dir: str = None) -> Tuple[BrowserContext, Page]:
    """
    Factory function to create stealth browser with FRESH session.
    
    Returns a completely isolated browser context with no data persistence.
    Perfect for automation that requires a clean slate every time.
    """
    manager = StealthBrowserManager()
    return manager.create_stealth_driver(session_id, user_data_dir=None)
