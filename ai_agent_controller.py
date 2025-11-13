#!/usr/bin/env python3
"""
AI Agent Controller
Implements a goal-oriented AI agent that uses OpenRouter API to make decisions
and execute actions on web pages using Playwright.
"""

import json
import base64
import time
import random
import traceback
from typing import Dict, List, Optional, Any, Tuple
from playwright.sync_api import Page, BrowserContext
from openrouter_client import OpenRouterClient

# Import visual feedback
try:
    from visual_feedback import highlight_element, get_visual_feedback
    VISUAL_FEEDBACK_AVAILABLE = True
except ImportError:
    VISUAL_FEEDBACK_AVAILABLE = False


class AIAgentController:
    """
    AI-powered agent controller that makes decisions based on page state
    and executes actions to achieve goals.
    """
    
    def __init__(self, page: Page, openrouter_client: OpenRouterClient, visual_feedback_enabled: bool = True):
        """
        Initialize the AI agent controller.
        
        Args:
            page: Playwright Page object
            openrouter_client: OpenRouterClient instance for API calls
            visual_feedback_enabled: Whether to show visual feedback for actions
        """
        self.page = page
        self.openrouter = openrouter_client
        self.action_history: List[Dict] = []
        self.max_iterations = 100  # Safety limit
        self.current_iteration = 0
        self.goal = None
        self.goal_achieved = False
        self.visual_feedback_enabled = visual_feedback_enabled
        
    def ai_get_page_state(self) -> Dict[str, str]:
        """
        Get the current page state (HTML and screenshot).
        
        Returns:
            Dict with 'html' and 'screenshot_base64' keys
        """
        try:
            # Get HTML content (truncate if too long)
            html = self.page.content()
            # Keep first 15000 chars for context (AI models have token limits)
            html_preview = html[:15000] if len(html) > 15000 else html
            
            # Take screenshot and convert to base64
            screenshot_bytes = self.page.screenshot(type='png', full_page=False)
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
            
            return {
                'html': html_preview,
                'screenshot_base64': screenshot_base64,
                'url': self.page.url
            }
        except Exception as e:
            print(f"⚠️  Error getting page state: {e}")
            return {
                'html': '',
                'screenshot_base64': '',
                'url': self.page.url
            }
    
    def ai_click(self, selector: str) -> Dict[str, Any]:
        """
        Click an element using a CSS selector.
        
        Args:
            selector: CSS selector for the element to click
            
        Returns:
            Dict with 'success' and 'message' keys
        """
        # Show visual feedback before clicking
        if VISUAL_FEEDBACK_AVAILABLE and self.visual_feedback_enabled:
            try:
                highlight_element(
                    self.page,
                    selector,
                    color='green',
                    duration=1.0,
                    action_description="AI Agent: Clicking element"
                )
            except Exception as e:
                # Don't fail if visual feedback fails
                pass
        
        try:
            locator = self.page.locator(selector).first
            locator.wait_for(state='visible', timeout=5000)
            locator.click(timeout=5000)
            
            # Add human-like delay
            time.sleep(random.uniform(0.5, 1.5))
            
            result = {
                'success': True,
                'message': f'Successfully clicked element: {selector}',
                'action': 'click',
                'selector': selector
            }
            self.action_history.append(result)
            return result
            
        except Exception as e:
            result = {
                'success': False,
                'message': f'Failed to click element {selector}: {str(e)}',
                'action': 'click',
                'selector': selector,
                'error': str(e)
            }
            self.action_history.append(result)
            return result
    
    def ai_type(self, selector: str, text: str) -> Dict[str, Any]:
        """
        Type text into an input field.
        
        Args:
            selector: CSS selector for the input field
            text: Text to type
            
        Returns:
            Dict with 'success' and 'message' keys
        """
        # Show visual feedback before typing
        if VISUAL_FEEDBACK_AVAILABLE and self.visual_feedback_enabled:
            try:
                highlight_element(
                    self.page,
                    selector,
                    color='blue',
                    duration=0.8,
                    action_description=f"AI Agent: Typing ({len(text)} chars)"
                )
            except Exception as e:
                # Don't fail if visual feedback fails
                pass
        
        try:
            locator = self.page.locator(selector).first
            locator.wait_for(state='visible', timeout=5000)
            
            # Clear field first
            locator.fill('')
            
            # Type with human-like delay
            locator.type(text, delay=random.randint(50, 150))
            
            # Add delay after typing
            time.sleep(random.uniform(0.3, 0.8))
            
            result = {
                'success': True,
                'message': f'Successfully typed text into {selector}',
                'action': 'type',
                'selector': selector,
                'text_length': len(text)
            }
            self.action_history.append(result)
            return result
            
        except Exception as e:
            result = {
                'success': False,
                'message': f'Failed to type into {selector}: {str(e)}',
                'action': 'type',
                'selector': selector,
                'error': str(e)
            }
            self.action_history.append(result)
            return result
    
    def ai_scroll(self, direction: str = 'down', amount: int = 500) -> Dict[str, Any]:
        """
        Scroll the page in a specified direction.
        
        Args:
            direction: 'up', 'down', 'left', 'right'
            amount: Number of pixels to scroll
            
        Returns:
            Dict with 'success' and 'message' keys
        """
        try:
            current_scroll = self.page.evaluate("() => window.scrollY")
            
            if direction.lower() == 'down':
                new_scroll = current_scroll + amount
            elif direction.lower() == 'up':
                new_scroll = max(0, current_scroll - amount)
            elif direction.lower() == 'right':
                self.page.evaluate(f"() => window.scrollBy({amount}, 0)")
                new_scroll = current_scroll
            elif direction.lower() == 'left':
                self.page.evaluate(f"() => window.scrollBy(-{amount}, 0)")
                new_scroll = current_scroll
            else:
                new_scroll = current_scroll + amount
            
            if direction.lower() in ['up', 'down']:
                self.page.evaluate(f"() => window.scrollTo(0, {new_scroll})")
            
            # Add human-like delay
            time.sleep(random.uniform(0.3, 0.7))
            
            result = {
                'success': True,
                'message': f'Successfully scrolled {direction} by {amount}px',
                'action': 'scroll',
                'direction': direction,
                'amount': amount
            }
            self.action_history.append(result)
            return result
            
        except Exception as e:
            result = {
                'success': False,
                'message': f'Failed to scroll: {str(e)}',
                'action': 'scroll',
                'error': str(e)
            }
            self.action_history.append(result)
            return result
    
    def ai_wait(self, seconds: float = 2.0) -> Dict[str, Any]:
        """
        Wait for a specified amount of time.
        
        Args:
            seconds: Number of seconds to wait
            
        Returns:
            Dict with 'success' and 'message' keys
        """
        try:
            time.sleep(seconds)
            result = {
                'success': True,
                'message': f'Waited for {seconds} seconds',
                'action': 'wait',
                'duration': seconds
            }
            self.action_history.append(result)
            return result
        except Exception as e:
            return {
                'success': False,
                'message': f'Wait interrupted: {str(e)}',
                'action': 'wait',
                'error': str(e)
            }
    
    def ai_navigate(self, url: str) -> Dict[str, Any]:
        """
        Navigate to a URL.
        
        Args:
            url: URL to navigate to
            
        Returns:
            Dict with 'success' and 'message' keys
        """
        try:
            self.page.goto(url, wait_until='networkidle', timeout=30000)
            time.sleep(random.uniform(2, 4))
            
            result = {
                'success': True,
                'message': f'Successfully navigated to {url}',
                'action': 'navigate',
                'url': url
            }
            self.action_history.append(result)
            return result
            
        except Exception as e:
            result = {
                'success': False,
                'message': f'Failed to navigate to {url}: {str(e)}',
                'action': 'navigate',
                'url': url,
                'error': str(e)
            }
            self.action_history.append(result)
            return result
    
    def _get_decision_from_ai(self, page_state: Dict, goal: str, recent_actions: List[Dict]) -> Optional[Dict]:
        """
        Get the next action decision from the AI.
        
        Args:
            page_state: Current page state (HTML, screenshot, URL)
            goal: High-level goal description
            recent_actions: List of recent actions taken
            
        Returns:
            Dict with action details or None on error
        """
        if not self.openrouter:
            print("❌ OpenRouter client not available")
            return None
        
        # Build context from recent actions
        action_summary = ""
        if recent_actions:
            action_summary = "\nRecent actions taken:\n"
            for action in recent_actions[-5:]:  # Last 5 actions
                action_summary += f"- {action.get('action', 'unknown')}: {action.get('message', '')}\n"
        
        # Build prompt
        prompt = f"""You are an expert web automation agent. Your goal is: {goal}

Current page URL: {page_state.get('url', 'unknown')}

{action_summary}

Here is the current page state. Analyze the HTML and screenshot to determine the next best action.

Available tools:
1. click(selector) - Click an element using CSS selector
2. type(selector, text) - Type text into an input field
3. scroll(direction, amount) - Scroll page (direction: 'up', 'down', 'left', 'right', amount: pixels)
4. wait(seconds) - Wait for specified seconds
5. navigate(url) - Navigate to a URL
6. done() - Indicate goal is achieved

IMPORTANT: 
- Respond ONLY with valid JSON in this exact format:
{{"action": "tool_name", "selector": "css_selector_or_empty", "text": "text_to_type_or_empty", "direction": "scroll_direction_or_empty", "amount": number_or_empty, "seconds": number_or_empty, "url": "url_or_empty", "reasoning": "why I chose this action"}}
- If goal is achieved, use action: "done"
- Be specific with selectors - prefer data-testid, id, or stable class names
- Only use one tool per response
- Include reasoning for your decision

HTML Preview:
{page_state.get('html', '')[:8000]}

Respond with JSON only:"""

        # Prepare messages with image support
        messages = [
            {
                "role": "system",
                "content": "You are an expert web automation agent. Analyze web pages and decide the best action to achieve goals. Always respond with valid JSON only."
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{page_state.get('screenshot_base64', '')}"
                        }
                    }
                ]
            }
        ]
        
        try:
            result = self.openrouter.chat_completion(
                messages=messages,
                model="openai/gpt-4o-mini",  # Can use gpt-4o for better vision
                temperature=0.3,  # Lower temperature for more consistent decisions
                max_tokens=500
            )
            
            if not result or 'content' not in result:
                print("⚠️  No response from AI")
                return None
            
            content = result['content'].strip()
            
            # Clean up response (remove markdown code blocks if present)
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            
            # Remove leading/trailing quotes if present
            content = content.strip('"\'`')
            
            # Parse JSON
            try:
                decision = json.loads(content)
                return decision
            except json.JSONDecodeError as e:
                print(f"⚠️  Failed to parse AI response as JSON: {e}")
                print(f"   Response was: {content[:200]}")
                return None
                
        except Exception as e:
            print(f"❌ Error getting AI decision: {e}")
            return None
    
    def execute_action(self, decision: Dict) -> Dict[str, Any]:
        """
        Execute an action based on AI decision.
        
        Args:
            decision: Dict with action details from AI
            
        Returns:
            Result dict from the executed action
        """
        action = decision.get('action', '').lower()
        
        if action == 'click':
            selector = decision.get('selector', '')
            if not selector:
                return {'success': False, 'message': 'No selector provided for click action'}
            return self.ai_click(selector)
            
        elif action == 'type':
            selector = decision.get('selector', '')
            text = decision.get('text', '')
            if not selector or not text:
                return {'success': False, 'message': 'Selector or text missing for type action'}
            return self.ai_type(selector, text)
            
        elif action == 'scroll':
            direction = decision.get('direction', 'down')
            amount = decision.get('amount', 500)
            return self.ai_scroll(direction, amount)
            
        elif action == 'wait':
            seconds = decision.get('seconds', 2.0)
            return self.ai_wait(seconds)
            
        elif action == 'navigate':
            url = decision.get('url', '')
            if not url:
                return {'success': False, 'message': 'No URL provided for navigate action'}
            return self.ai_navigate(url)
            
        elif action == 'done':
            self.goal_achieved = True
            return {
                'success': True,
                'message': 'Goal achieved according to AI',
                'action': 'done'
            }
            
        else:
            return {
                'success': False,
                'message': f'Unknown action: {action}',
                'action': action
            }
    
    def run_agent_loop(self, goal: str, max_iterations: int = 100) -> Dict[str, Any]:
        """
        Run the main agent loop until goal is achieved or max iterations reached.
        
        Args:
            goal: High-level goal description (e.g., "Apply to 5 remote Python jobs")
            max_iterations: Maximum number of iterations before stopping
            
        Returns:
            Dict with final status and statistics
        """
        self.goal = goal
        self.goal_achieved = False
        self.current_iteration = 0
        self.max_iterations = max_iterations
        self.action_history = []
        
        print(f"\n🤖 AI Agent Controller Started")
        print(f"🎯 Goal: {goal}")
        print(f"📊 Max iterations: {max_iterations}")
        print("=" * 70)
        
        while not self.goal_achieved and self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            print(f"\n🔄 Iteration {self.current_iteration}/{self.max_iterations}")
            
            try:
                # Get current page state
                print("📸 Capturing page state...")
                page_state = self.ai_get_page_state()
                
                # Get recent actions for context
                recent_actions = self.action_history[-5:] if len(self.action_history) > 5 else self.action_history
                
                # Get decision from AI
                print("🤖 Consulting AI for next action...")
                decision = self._get_decision_from_ai(page_state, goal, recent_actions)
                
                if not decision:
                    print("⚠️  No decision from AI, waiting and retrying...")
                    time.sleep(2)
                    continue
                
                # Log decision
                action_name = decision.get('action', 'unknown')
                reasoning = decision.get('reasoning', 'No reasoning provided')
                print(f"💭 AI Decision: {action_name}")
                print(f"   Reasoning: {reasoning}")
                
                # Execute action
                print(f"⚡ Executing: {action_name}...")
                result = self.execute_action(decision)
                
                if result.get('success'):
                    print(f"✅ {result.get('message', 'Action completed')}")
                else:
                    print(f"❌ {result.get('message', 'Action failed')}")
                
                # Check if goal is achieved
                if self.goal_achieved:
                    print("\n🎉 Goal achieved!")
                    break
                
                # Small delay between iterations
                time.sleep(random.uniform(1, 2))
                
            except KeyboardInterrupt:
                print("\n⏹️  Agent loop interrupted by user")
                break
            except Exception as e:
                print(f"❌ Error in agent loop: {e}")
                traceback.print_exc()
                time.sleep(2)
                continue
        
        # Final summary
        print("\n" + "=" * 70)
        print("📊 Agent Session Summary")
        print("=" * 70)
        print(f"Goal: {goal}")
        print(f"Status: {'✅ Achieved' if self.goal_achieved else '⏸️  Stopped'}")
        print(f"Iterations: {self.current_iteration}")
        print(f"Total actions: {len(self.action_history)}")
        print(f"Successful actions: {sum(1 for a in self.action_history if a.get('success'))}")
        print("=" * 70)
        
        return {
            'goal_achieved': self.goal_achieved,
            'iterations': self.current_iteration,
            'total_actions': len(self.action_history),
            'successful_actions': sum(1 for a in self.action_history if a.get('success')),
            'action_history': self.action_history
        }

