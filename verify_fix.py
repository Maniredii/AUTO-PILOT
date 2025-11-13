#!/usr/bin/env python3
"""
Verification Script: Check if Session Persistence Fix is Applied
Run this to verify your bot will create fresh sessions
"""

import os
import sys

def check_file_for_issue(filepath, bad_patterns, good_patterns):
    """Check if file has been fixed"""
    if not os.path.exists(filepath):
        return False, f"File not found: {filepath}"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check for bad patterns
    for pattern in bad_patterns:
        if pattern in content:
            return False, f"Found problematic code: {pattern[:50]}..."
    
    # Check for good patterns
    for pattern in good_patterns:
        if pattern not in content:
            return False, f"Missing expected fix: {pattern[:50]}..."
    
    return True, "OK"

def main():
    print("=" * 70)
    print("🔍 VERIFYING SESSION PERSISTENCE FIX")
    print("=" * 70)
    print()
    
    all_good = True
    
    # Check 1: stealth_browser_manager.py
    print("1. Checking stealth_browser_manager.py...")
    bad_patterns = [
        "launch_persistent_context",
        "'user_data_dir': user_data_dir or"
    ]
    good_patterns = [
        "browser.new_context",
        "Fresh stealth browser created"
    ]
    
    is_fixed, message = check_file_for_issue(
        "stealth_browser_manager.py",
        bad_patterns,
        good_patterns
    )
    
    if is_fixed:
        print("   ✅ FIXED: Using fresh contexts (no persistence)")
    else:
        print(f"   ❌ ISSUE: {message}")
        all_good = False
    print()
    
    # Check 2: protected_linkedin_bot.py
    print("2. Checking protected_linkedin_bot.py...")
    bad_patterns = [
        'user_data_dir=user_data_dir',
        'user_data_dir=os.path.join'
    ]
    good_patterns = [
        "create_stealth_driver",
        "session_id="
    ]
    
    is_fixed, message = check_file_for_issue(
        "protected_linkedin_bot.py",
        bad_patterns,
        good_patterns
    )
    
    if is_fixed:
        print("   ✅ FIXED: Not passing user_data_dir parameter")
    else:
        print(f"   ❌ ISSUE: {message}")
        all_good = False
    print()
    
    # Check 3: chrome_bot folder
    print("3. Checking for chrome_bot folder...")
    if os.path.exists("chrome_bot"):
        print("   ⚠️  WARNING: chrome_bot folder still exists")
        print("   Recommendation: Delete it to ensure clean start")
        print("   Command: rmdir /s /q chrome_bot")
    else:
        print("   ✅ GOOD: No chrome_bot folder (will be created fresh)")
    print()
    
    # Final verdict
    print("=" * 70)
    if all_good:
        print("✅ ALL CHECKS PASSED!")
        print()
        print("Your bot is configured for fresh sessions.")
        print("Each run will start with a clean slate - no saved cookies or data.")
        print()
        print("Next steps:")
        print("1. Delete chrome_bot folder if it exists: rmdir /s /q chrome_bot")
        print("2. Run your bot: python main.py")
        print("3. You should see the LinkedIn login page (not a logged-in feed)")
    else:
        print("❌ SOME ISSUES FOUND")
        print()
        print("Please review the issues above and apply the fixes.")
        print("See SOLUTION.md and APPROACH_A_SIMPLE_FIX.md for instructions.")
    print("=" * 70)
    
    return 0 if all_good else 1

if __name__ == "__main__":
    sys.exit(main())
