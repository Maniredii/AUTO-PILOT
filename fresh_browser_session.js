/**
 * Fresh Browser Session Script for LinkedIn Automation
 * 
 * This script demonstrates how to create a completely isolated browser session
 * that has ZERO memory of previous runs. Perfect for automation that requires
 * a clean slate every time.
 * 
 * Author: Senior Automation Engineer
 * Purpose: Prevent session persistence and ensure login page is always shown
 */

const { chromium } = require('playwright');

async function createFreshBrowserSession() {
    console.log('🚀 Starting fresh browser session...\n');
    
    let browser = null;
    let context = null;
    let page = null;
    
    try {
        // Step 1: Launch browser with NO persistent storage
        // Key: We do NOT specify userDataDir, which means everything is in-memory
        browser = await chromium.launch({
            headless: false,  // Set to true for headless mode
            args: [
                '--disable-blink-features=AutomationControlled',  // Hide automation
                '--disable-dev-shm-usage',                        // Overcome limited resource problems
                '--no-sandbox',                                   // Required for some environments
                '--disable-setuid-sandbox',
                '--disable-web-security',                         // Sometimes needed for testing
                '--disable-features=IsolateOrigins,site-per-process'
            ]
        });
        console.log('✅ Browser launched (in-memory mode)\n');
        
        // Step 2: Create a NEW, ISOLATED browser context
        // This is the KEY to session isolation!
        // Each context is completely independent with its own:
        // - Cookies
        // - Local Storage
        // - Session Storage
        // - Cache
        // - IndexedDB
        // - Service Workers
        context = await browser.newContext({
            // Viewport configuration
            viewport: { width: 1920, height: 1080 },
            
            // User agent (optional: makes it look more human)
            userAgent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            
            // Locale and timezone
            locale: 'en-US',
            timezoneId: 'America/New_York',
            
            // Permissions (optional)
            permissions: [],
            
            // Geolocation (optional)
            // geolocation: { longitude: -74.0060, latitude: 40.7128 },
            
            // CRITICAL: Do NOT specify storageState
            // This ensures we start with a completely clean slate
            // storageState: undefined  // This is the default, but shown for clarity
        });
        console.log('✅ Fresh browser context created (isolated session)\n');
        
        // Step 3: Create a new page in this context
        page = await context.newPage();
        console.log('✅ New page created\n');
        
        // Step 4: Navigate to LinkedIn login page
        console.log('🌐 Navigating to LinkedIn login page...');
        await page.goto('https://www.linkedin.com/login', {
            waitUntil: 'networkidle',  // Wait for network to be idle
            timeout: 30000              // 30 second timeout
        });
        
        // Step 5: Verify we're on the login page
        const currentUrl = page.url();
        console.log(`📍 Current URL: ${currentUrl}\n`);
        
        // Check if we're actually on the login page
        if (currentUrl.includes('/login') || currentUrl.includes('/checkpoint')) {
            console.log('✅ SUCCESS: Login page loaded (clean session confirmed!)');
            console.log('   No previous session data was retained.\n');
        } else if (currentUrl.includes('/feed')) {
            console.log('⚠️  WARNING: Redirected to feed (session may have persisted)');
            console.log('   This should NOT happen with this script.\n');
        }
        
        // Step 6: Additional verification - check for login form elements
        try {
            const usernameField = await page.locator('#username').isVisible({ timeout: 5000 });
            const passwordField = await page.locator('#password').isVisible({ timeout: 5000 });
            
            if (usernameField && passwordField) {
                console.log('✅ Login form elements detected:');
                console.log('   - Username field: visible');
                console.log('   - Password field: visible\n');
            }
        } catch (error) {
            console.log('⚠️  Could not verify login form elements (page may still be loading)\n');
        }
        
        // Step 7: Wait for user to see the result (optional, for demonstration)
        console.log('⏳ Keeping browser open for 10 seconds for inspection...');
        await page.waitForTimeout(10000);
        
        console.log('\n✅ Script completed successfully!');
        
    } catch (error) {
        console.error('❌ Error occurred:', error.message);
        throw error;
        
    } finally {
        // Step 8: Clean up - close everything
        // This ensures no data is persisted
        console.log('\n🧹 Cleaning up...');
        
        if (page) {
            await page.close();
            console.log('   - Page closed');
        }
        
        if (context) {
            await context.close();
            console.log('   - Context closed (all session data discarded)');
        }
        
        if (browser) {
            await browser.close();
            console.log('   - Browser closed');
        }
        
        console.log('✅ Cleanup complete - all session data destroyed\n');
    }
}

// Execute the function
(async () => {
    try {
        await createFreshBrowserSession();
        console.log('🎉 Fresh browser session demonstration complete!');
    } catch (error) {
        console.error('💥 Fatal error:', error);
        process.exit(1);
    }
})();
