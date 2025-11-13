#!/usr/bin/env python3
"""
FIXED VERSION - Part 1: Core Changes
This shows the key method that needs to be replaced in stealth_browser_manager.py
"""

from playwright.sync_api import sync_playwright, BrowserContext, Page
from typing import Tuple
import os

def create_fresh_stealth_context(self, session_id: str = None, headless: bool = False) -> Tuple[BrowserContext, Page]:
    """
    Create fully stealthed browser context with NO PERSISTENCE
    
    KEY CHANGE: Uses browser.new_context() instead of launch_persistent_context()
    This ensures ZERO data is saved between runs.
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
            '--no-first-run',
            '--disable-sync',
            '--disable-translate',
            '--disable-background-networking',
            '--disable-default-apps',
        ]
        
        # Launch browser WITHOUT user_data_dir (in-memory only)
        browser = self.playwright.chromium.launch(
            headless=headless,
            args=chrome_args
        )
        
        print("✅ Browser launched (in-memory mode - no persistence)")
