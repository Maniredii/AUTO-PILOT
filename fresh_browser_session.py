#!/usr/bin/env python3
"""
Fresh Browser Session Script for LinkedIn Automation (Python/Playwright)

This script demonstrates how to create a completely isolated browser session
that has ZERO memory of previous runs. Perfect for automation that requires
a clean slate every time.

Author: Senior Automation Engineer
Purpose: Prevent session persistence and ensure login page is always shown
"""

from playwright.sync_api import sync_playwright
import time


def create_fresh_browser_session():
    """
    Creates a completely fresh browser session with no data persistence.
    
    This function demonstrates the professional approach to browser automation
    where each run starts with a clean slate - no cookies, no cache, no history.
    """
    print('🚀 Starting fresh browser session...\n')
    
    playwright = None
    browser = None
    context = None
    page = None
    
    try:
        # Step 1: Initialize Playwright
        playwright = sync_playwright().start()
        print('✅ Playwright initialized\n')
        
        # Step 2: Launch browser with NO persistent storage
        # KEY POINT: We do NOT specify user_data_dir
        # This means everything stays in memory and is discarded when closed
        browser = playwright.chromium.launch(
            headless=False,  # Set to True for headless mode
            args=[
                '--disable-blink-features=AutomationControlled',  # Hide automation
                '--disable-dev-shm-usage',                        # Overcome limited resource problems
                '--no-sandbox',                                   # Required for some environments
                '--disable-setuid-sandbox',
                '--disable-web-security',                         # Sometimes needed for testing
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        )
        print('✅ Browser launched (in-memory mode)\n')
        
        # Step 3: Create a NEW, ISOLATED browser context
        # This is the KEY to session isolation!
        # Each context is completely independent with its own:
        # - Cookies
        # - Local Storage
        # - Session Storage
        # - Cache
        # - IndexedDB
        # - Service Workers
        context = browser.new_context(
            # Viewport configuration
            viewport={'width': 1920, 'height': 1080},
            
            # User agent (makes it look more human)
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            
            # Locale and timezone
            locale='en-US',
            timezone_id='America/New_York',
            
            # Permissions (empty list = no special permissions)
            permissions=[],
            
            # CRITICAL: Do NOT specify storage_state
            # This ensures we start with a completely clean slate
            # storage_state=None  # This is the default
        )
        print('✅ Fresh browser context created (isolated session)\n')
        
        # Step 4: Create a new page in this context
        page = context.new_page()
        print('✅ New page created\n')
        
        # Step 5: Navigate to LinkedIn login page
        print('🌐 Navigating to LinkedIn login page...')
        page.goto('https://www.linkedin.com/login', wait_until='networkidle', timeout=30000)
        
        # Step 6: Verify we're on the login page
        current_url = page.url
        print(f'📍 Current URL: {current_url}\n')
        
        # Check if we're actually on the login page
        if '/login' in current_url or '/checkpoint' in current_url:
            print('✅ SUCCESS: Login page loaded (clean session confirmed!)')
            print('   No previous session data was retained.\n')
        elif '/feed' in current_url:
            print('⚠️  WARNING: Redirected to feed (session may have persisted)')
            print('   This should NOT happen with this script.\n')
        
        # Step 7: Additional verification - check for login form elements
        try:
            username_visible = page.locator('#username').is_visible(timeout=5000)
            password_visible = page.locator('#password').is_visible(timeout=5000)
            
            if username_visible and password_visible:
                print('✅ Login form elements detected:')
                print('   - Username field: visible')
                print('   - Password field: visible\n')
        except Exception as e:
            print(f'⚠️  Could not verify login form elements: {str(e)}\n')
        
        # Step 8: Wait for user to see the result (optional, for demonstration)
        print('⏳ Keeping browser open for 10 seconds for inspection...')
        time.sleep(10)
        
        print('\n✅ Script completed successfully!')
        
    except Exception as error:
        print(f'❌ Error occurred: {str(error)}')
        raise
        
    finally:
        # Step 9: Clean up - close everything
        # This ensures no data is persisted
        print('\n🧹 Cleaning up...')
        
        if page:
            page.close()
            print('   - Page closed')
        
        if context:
            context.close()
            print('   - Context closed (all session data discarded)')
        
        if browser:
            browser.close()
            print('   - Browser closed')
        
        if playwright:
            playwright.stop()
            print('   - Playwright stopped')
        
        print('✅ Cleanup complete - all session data destroyed\n')


if __name__ == '__main__':
    try:
        create_fresh_browser_session()
        print('🎉 Fresh browser session demonstration complete!')
    except Exception as error:
        print(f'💥 Fatal error: {error}')
        exit(1)
