#!/usr/bin/env python3
"""
FIXED VERSION - Part 2: Context Creation
Continuation of the fixed method
"""

        # Create NEW context (isolated session)
        context_options = {
            'viewport': {'width': profile.viewport[0], 'height': profile.viewport[1]},
            'user_agent': profile.user_agent,
            'locale': profile.language,
            'timezone_id': profile.timezone,
            'permissions': [],
            'ignore_https_errors': True,
            'java_script_enabled': True,
        }
        
        # Add proxy if available
        if proxy_info:
            context_options['proxy'] = proxy_info
            print(f"✅ Proxy configured: {proxy_info.get('server', 'N/A')[:50]}...")
        
        # Create fresh context
        context = browser.new_context(**context_options)
        
        print("✅ Fresh context created (isolated session)")
        
        # Create page
        page = context.new_page()
        
        # Add stealth script
        stealth_script = self._get_stealth_script(profile)
        context.add_init_script(stealth_script)
        
        # Set headers
        context.set_extra_http_headers({
            'Accept-Language': f'{profile.language},en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        })
        
        print(f"✅ Stealth browser ready: {profile.user_agent[:50]}...")
        return context, page
        
    except Exception as e:
        print(f"❌ Failed to create stealth browser: {e}")
        raise
