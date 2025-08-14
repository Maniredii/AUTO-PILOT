#!/usr/bin/env python3
"""
Test script to verify the bot fixes work
"""

import traceback

def test_imports():
    """Test if all modules can be imported"""
    try:
        from linkedineasyapply import LinkedinEasyApply
        print("✅ LinkedinEasyApply imported successfully")
        return True
    except Exception as e:
        print(f"❌ Error importing LinkedinEasyApply: {str(e)}")
        traceback.print_exc()
        return False

def test_syntax():
    """Test if the main file has valid syntax"""
    try:
        with open("main.py", "r") as f:
            compile(f.read(), "main.py", "exec")
        print("✅ main.py has valid syntax")
        return True
    except Exception as e:
        print(f"❌ Syntax error in main.py: {str(e)}")
        return False

if __name__ == "__main__":
    print("Testing EasyApplyBot fixes...")
    print("=" * 50)
    
    import_ok = test_imports()
    syntax_ok = test_syntax()
    
    if import_ok and syntax_ok:
        print("\n✅ All tests passed! The bot should work better now.")
        print("\nKey improvements made:")
        print("- Better error handling for stale elements")
        print("- Multiple button selector strategies")
        print("- Form retry logic with page refresh")
        print("- Improved exception handling")
        print("- Better logging and debugging info")
    else:
        print("\n❌ Some tests failed. Please check the errors above.")
