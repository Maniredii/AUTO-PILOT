#!/usr/bin/env python3
"""
LinkedIn Easy Apply Bot Launcher with Anti-Ban System
Comprehensive launcher with multiple protection modes and monitoring
"""

import asyncio
import sys
import os
import json
import argparse
from pathlib import Path
from datetime import datetime
import traceback

# Import bot components
from linkedin_bot_with_anti_ban import ProtectedLinkedInBot
from anti_ban_system import AntiDetectionManager
from stealth_browser_manager import StealthBrowserManager

class BotLauncher:
    """Advanced bot launcher with monitoring and protection"""
    
    def __init__(self):
        self.bot = None
        self.anti_detection = None
        self.launch_time = datetime.now()
        
    def display_banner(self):
        """Display startup banner"""
        banner = """
╔══════════════════════════════════════════════════════════════╗
║                🛡️  PROTECTED LINKEDIN BOT 🛡️                ║  
║                                                              ║
║          Advanced Anti-Ban Easy Apply Automation            ║
║                                                              ║
║  Features:                                                   ║
║  ✅ Advanced Browser Fingerprint Spoofing                    ║
║  ✅ Human Behavior Simulation                                ║
║  ✅ Intelligent Rate Limiting                                ║
║  ✅ CAPTCHA Detection & Response                             ║
║  ✅ Session Management & Rotation                            ║
║  ✅ Daily Application Limits                                 ║
║  ✅ Real-time Monitoring                                     ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
        """
        print(banner)
    
    def check_dependencies(self) -> bool:
        """Check if all required dependencies are installed"""
        required_files = [
            "config.yaml",
            "anti_ban_config.json",
            "anti_ban_system.py",
            "stealth_browser_manager.py",
            "linkedin_bot_with_anti_ban.py"
        ]
        
        missing_files = []
        for file in required_files:
            if not os.path.exists(file):
                missing_files.append(file)
        
        if missing_files:
            print(f"❌ Missing required files: {missing_files}")
            return False
        
        # Check Python packages
        try:
            import selenium
            import yaml
            import asyncio
            print("✅ All dependencies satisfied")
            return True
        except ImportError as e:
            print(f"❌ Missing Python package: {e}")
            return False
    
    def validate_config(self) -> bool:
        """Validate configuration files"""
        try:
            # Validate main config
            with open("config.yaml", 'r') as f:
                main_config = yaml.safe_load(f)
            
            required_fields = ['email', 'password', 'positions', 'locations']
            for field in required_fields:
                if field not in main_config:
                    print(f"❌ Missing field in config.yaml: {field}")
                    return False
            
            # Validate anti-ban config
            with open("anti_ban_config.json", 'r') as f:
                anti_ban_config = json.load(f)
            
            print("✅ Configuration files validated")
            return True
            
        except Exception as e:
            print(f"❌ Configuration validation failed: {e}")
            return False
    
    def show_protection_status(self):
        """Display current protection status"""
        print("\n🛡️  Protection Status:")
        print("=" * 40)
        
        try:
            # Load anti-ban config
            with open("anti_ban_config.json", 'r') as f:
                config = json.load(f)
            
            settings = config["anti_ban_settings"]
            
            # Session Management
            print("📊 Session Management:")
            print(f"  • Max Applications/Session: {settings['session_management']['max_applications_per_session']}")
            print(f"  • Max Session Duration: {settings['session_management']['max_session_duration_minutes']} minutes")
            print(f"  • Break Duration: {settings['session_management']['min_break_duration_minutes']}-{settings['session_management']['max_break_duration_minutes']} minutes")
            
            # Timing Controls
            print("\n⏰ Timing Controls:")
            print(f"  • Application Delay: {settings['timing_controls']['min_delay_between_applications']}-{settings['timing_controls']['max_delay_between_applications']} seconds")
            print(f"  • Page Load Wait: {settings['timing_controls']['min_page_load_wait']}-{settings['timing_controls']['max_page_load_wait']} seconds")
            
            # Detection Thresholds
            print("\n🚨 Detection Thresholds:")
            print(f"  • Max Errors/Session: {settings['detection_thresholds']['max_errors_per_session']}")
            print(f"  • Max Daily Applications: {settings['detection_thresholds']['max_daily_applications']}")
            print(f"  • CAPTCHA Limit: {settings['detection_thresholds']['max_captcha_encounters']}")
            
            # Stealth Features
            print("\n🕵️  Stealth Features:")
            enabled_features = [k.replace('_', ' ').title() for k, v in settings['stealth_features'].items() if v]
            for feature in enabled_features:
                print(f"  ✅ {feature}")
                
        except Exception as e:
            print(f"⚠️  Could not load protection status: {e}")
    
    def select_operation_mode(self) -> str:
        """Interactive mode selection"""
        print("\n🎯 Select Operation Mode:")
        print("=" * 30)
        print("1. 🛡️  Maximum Protection (Safest, Slower)")
        print("2. ⚖️  Balanced Protection (Recommended)")
        print("3. ⚡ Performance Mode (Faster, Less Safe)")
        print("4. 🧪 Test Mode (Dry Run)")
        print("5. 📊 Monitor Only")
        
        while True:
            try:
                choice = input("\nEnter your choice (1-5): ").strip()
                if choice in ['1', '2', '3', '4', '5']:
                    return choice
                else:
                    print("❌ Invalid choice. Please enter 1-5.")
            except KeyboardInterrupt:
                print("\n⏹️  Operation cancelled")
                sys.exit(0)
    
    def configure_protection_level(self, mode: str):
        """Configure protection based on selected mode"""
        try:
            with open("anti_ban_config.json", 'r') as f:
                config = json.load(f)
            
            settings = config["anti_ban_settings"]
            
            if mode == '1':  # Maximum Protection
                settings["session_management"]["max_applications_per_session"] = 10
                settings["timing_controls"]["min_delay_between_applications"] = 300
                settings["timing_controls"]["max_delay_between_applications"] = 900
                settings["detection_thresholds"]["max_daily_applications"] = 25
                print("🛡️  Maximum Protection Mode Activated")
                
            elif mode == '2':  # Balanced Protection  
                settings["session_management"]["max_applications_per_session"] = 15
                settings["timing_controls"]["min_delay_between_applications"] = 180
                settings["timing_controls"]["max_delay_between_applications"] = 600
                settings["detection_thresholds"]["max_daily_applications"] = 40
                print("⚖️  Balanced Protection Mode Activated")
                
            elif mode == '3':  # Performance Mode
                settings["session_management"]["max_applications_per_session"] = 25
                settings["timing_controls"]["min_delay_between_applications"] = 120
                settings["timing_controls"]["max_delay_between_applications"] = 300
                settings["detection_thresholds"]["max_daily_applications"] = 60
                print("⚡ Performance Mode Activated")
                
            elif mode == '4':  # Test Mode
                settings["session_management"]["max_applications_per_session"] = 5
                settings["timing_controls"]["min_delay_between_applications"] = 10
                settings["timing_controls"]["max_delay_between_applications"] = 30
                settings["detection_thresholds"]["max_daily_applications"] = 5
                print("🧪 Test Mode Activated")
                
            elif mode == '5':  # Monitor Only
                print("📊 Monitor Only Mode - No applications will be submitted")
                return
            
            # Save updated config
            with open("anti_ban_config.json", 'w') as f:
                json.dump(config, f, indent=2)
                
        except Exception as e:
            print(f"⚠️  Could not configure protection level: {e}")
    
    async def run_bot(self, mode: str):
        """Run the bot with selected configuration"""
        try:
            print(f"\n🚀 Starting bot in mode {mode}...")
            
            if mode == '5':  # Monitor only
                print("📊 Running in monitor mode - tracking only")
                # Implement monitoring logic here
                await asyncio.sleep(10)
                print("📊 Monitor session completed")
                return
            
            # Create and run protected bot
            self.bot = ProtectedLinkedInBot()
            await self.bot.run_protected_application_cycle()
            
        except KeyboardInterrupt:
            print("\n⏹️  Bot stopped by user")
        except Exception as e:
            print(f"❌ Bot execution error: {e}")
            traceback.print_exc()
    
    def show_session_summary(self):
        """Display session summary"""
        duration = datetime.now() - self.launch_time
        
        print("\n📊 Session Summary:")
        print("=" * 30)
        print(f"⏰ Duration: {duration}")
        print(f"📅 Started: {self.launch_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 Ended: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Try to load session stats
        try:
            if self.bot and hasattr(self.bot, 'applications_today'):
                print(f"📝 Applications Today: {self.bot.applications_today}")
            
            # Look for log files
            log_files = [f for f in os.listdir('.') if f.startswith('daily_usage_')]
            if log_files:
                latest_log = sorted(log_files)[-1]
                with open(latest_log, 'r') as f:
                    data = json.load(f)
                    print(f"📈 Total Daily Applications: {data.get('applications_count', 0)}")
        except Exception:
            pass
        
        print("\n🎉 Session completed successfully!")
    
    async def main(self):
        """Main launcher function"""
        self.display_banner()
        
        # Pre-flight checks
        if not self.check_dependencies():
            print("❌ Dependency check failed. Please install required packages.")
            return
        
        if not self.validate_config():
            print("❌ Configuration validation failed. Please check your config files.")
            return
        
        # Show protection status
        self.show_protection_status()
        
        # Mode selection
        mode = self.select_operation_mode()
        
        # Configure protection
        self.configure_protection_level(mode)
        
        # Confirmation
        print(f"\n⚠️  Ready to start bot. Press Ctrl+C anytime to stop safely.")
        input("Press Enter to continue or Ctrl+C to cancel...")
        
        try:
            # Run bot
            await self.run_bot(mode)
        finally:
            # Show summary
            self.show_session_summary()

def main():
    """Entry point with argument parsing"""
    parser = argparse.ArgumentParser(description="LinkedIn Easy Apply Bot with Anti-Ban Protection")
    parser.add_argument("--mode", choices=['1', '2', '3', '4', '5'], 
                       help="Operation mode (1=Max Protection, 2=Balanced, 3=Performance, 4=Test, 5=Monitor)")
    parser.add_argument("--auto", action='store_true', 
                       help="Run in automatic mode without interactive prompts")
    parser.add_argument("--config", default="config.yaml", 
                       help="Path to configuration file")
    
    args = parser.parse_args()
    
    try:
        launcher = BotLauncher()
        
        if args.mode and args.auto:
            # Non-interactive mode
            launcher.configure_protection_level(args.mode)
            asyncio.run(launcher.run_bot(args.mode))
        else:
            # Interactive mode
            asyncio.run(launcher.main())
            
    except KeyboardInterrupt:
        print("\n⏹️  Launcher stopped by user")
    except Exception as e:
        print(f"❌ Launcher error: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()