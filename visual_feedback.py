#!/usr/bin/env python3
"""
Visual Feedback Module
Provides colored overlays on screenshots to show which element the bot is about to interact with.
Similar to browser-use visual feedback system.
"""

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont
import time
import io
from typing import Optional, Dict, Tuple
from playwright.sync_api import Page, Locator


class VisualFeedback:
    """
    Visual feedback system for showing bot actions on screen.
    """
    
    # Color definitions (RGBA format: Red, Green, Blue, Alpha)
    COLORS = {
        'green': (0, 255, 0, 120),      # Success/click actions
        'red': (255, 0, 0, 120),        # Errors/warnings
        'yellow': (255, 255, 0, 120),   # Attention/waiting
        'blue': (0, 0, 255, 120),       # Information/navigation
        'orange': (255, 165, 0, 120),   # Important actions
        'purple': (128, 0, 128, 120),   # Special actions
        'cyan': (0, 255, 255, 120),      # Alternative actions
    }
    
    # Outline colors (fully opaque)
    OUTLINE_COLORS = {
        'green': (0, 255, 0, 255),
        'red': (255, 0, 0, 255),
        'yellow': (255, 255, 0, 255),
        'blue': (0, 0, 255, 255),
        'orange': (255, 165, 0, 255),
        'purple': (128, 0, 128, 255),
        'cyan': (0, 255, 255, 255),
    }
    
    def __init__(self, enabled: bool = True, window_name: str = "Bot Action Preview"):
        """
        Initialize visual feedback system.
        
        Args:
            enabled: Whether visual feedback is enabled
            window_name: Name of the OpenCV window
        """
        self.enabled = enabled
        self.window_name = window_name
        self.window_created = False
    
    def highlight_element(
        self,
        page: Page,
        selector: str,
        color: str = 'green',
        duration: float = 1.5,
        action_description: str = None,
        show_label: bool = True
    ) -> bool:
        """
        Highlights a given element on the screen by taking a screenshot,
        drawing a colored box, and displaying it temporarily.
        
        Args:
            page: Playwright Page object
            selector: CSS selector for the element to highlight
            color: Color name ('green', 'red', 'yellow', 'blue', 'orange', 'purple', 'cyan')
            duration: How long to display the highlight (seconds)
            action_description: Optional text description of the action
            show_label: Whether to show a text label on the highlight
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Get element's bounding box
            locator = page.locator(selector).first
            
            # Wait for element to be visible
            try:
                locator.wait_for(state='visible', timeout=3000)
            except:
                # Element might not be visible, try to get bounding box anyway
                pass
            
            bbox = locator.bounding_box()
            
            if not bbox:
                print(f"⚠️  Could not find bounding box for selector: {selector}")
                return False
            
            # Take full-page screenshot
            screenshot_bytes = page.screenshot(full_page=True, type='png')
            
            # Open screenshot with Pillow
            img = Image.open(io.BytesIO(screenshot_bytes))
            
            # Convert to RGBA if needed
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            # Create a drawing context
            draw = ImageDraw.Draw(img, 'RGBA')
            
            # Get color (default to green if invalid)
            fill_color = self.COLORS.get(color.lower(), self.COLORS['green'])
            outline_color = self.OUTLINE_COLORS.get(color.lower(), self.OUTLINE_COLORS['green'])
            
            # Calculate coordinates
            x = int(bbox['x'])
            y = int(bbox['y'])
            width = int(bbox['width'])
            height = int(bbox['height'])
            
            # Draw semi-transparent rectangle
            draw.rectangle(
                [x, y, x + width, y + height],
                fill=fill_color,
                outline=outline_color,
                width=3
            )
            
            # Add text label if requested
            if show_label and action_description:
                try:
                    # Try to use a default font, fallback to basic if not available
                    try:
                        font = ImageFont.truetype("arial.ttf", 16)
                    except:
                        try:
                            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 16)
                        except:
                            font = ImageFont.load_default()
                    
                    # Calculate text position (centered on element)
                    text_bbox = draw.textbbox((0, 0), action_description, font=font)
                    text_width = text_bbox[2] - text_bbox[0]
                    text_height = text_bbox[3] - text_bbox[1]
                    
                    text_x = x + (width - text_width) // 2
                    text_y = y - text_height - 5  # Above the element
                    
                    # Draw text background
                    padding = 4
                    draw.rectangle(
                        [text_x - padding, text_y - padding, 
                         text_x + text_width + padding, text_y + text_height + padding],
                        fill=(0, 0, 0, 200),  # Semi-transparent black background
                        outline=outline_color,
                        width=2
                    )
                    
                    # Draw text
                    draw.text(
                        (text_x, text_y),
                        action_description,
                        fill=(255, 255, 255, 255),  # White text
                        font=font
                    )
                except Exception as e:
                    print(f"⚠️  Could not add text label: {e}")
            
            # Convert PIL Image to OpenCV format (BGR)
            cv_image = cv2.cvtColor(np.array(img.convert('RGB')), cv2.COLOR_RGB2BGR)
            
            # Display the image
            display_name = f"{self.window_name} - {action_description or selector[:30]}"
            cv2.imshow(display_name, cv_image)
            
            # Wait for key press or duration timeout
            # cv2.waitKey returns the key code, or -1 if no key pressed
            wait_time_ms = int(duration * 1000)
            key = cv2.waitKey(wait_time_ms) & 0xFF
            
            # Close window
            cv2.destroyAllWindows()
            self.window_created = False
            
            return True
            
        except Exception as e:
            print(f"⚠️  Error during visual feedback: {e}")
            try:
                cv2.destroyAllWindows()
            except:
                pass
            return False
    
    def highlight_multiple_elements(
        self,
        page: Page,
        selectors: list,
        colors: list = None,
        duration: float = 2.0,
        action_descriptions: list = None
    ) -> bool:
        """
        Highlight multiple elements at once with different colors.
        
        Args:
            page: Playwright Page object
            selectors: List of CSS selectors
            colors: List of color names (defaults to cycling through colors)
            duration: How long to display (seconds)
            action_descriptions: Optional list of descriptions
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            # Take screenshot
            screenshot_bytes = page.screenshot(full_page=True, type='png')
            img = Image.open(io.BytesIO(screenshot_bytes))
            
            if img.mode != 'RGBA':
                img = img.convert('RGBA')
            
            draw = ImageDraw.Draw(img, 'RGBA')
            
            # Default colors if not provided
            if not colors:
                color_list = list(self.COLORS.keys())
                colors = [color_list[i % len(color_list)] for i in range(len(selectors))]
            
            # Highlight each element
            for i, selector in enumerate(selectors):
                try:
                    locator = page.locator(selector).first
                    bbox = locator.bounding_box()
                    
                    if not bbox:
                        continue
                    
                    color = colors[i] if i < len(colors) else 'green'
                    fill_color = self.COLORS.get(color.lower(), self.COLORS['green'])
                    outline_color = self.OUTLINE_COLORS.get(color.lower(), self.OUTLINE_COLORS['green'])
                    
                    x = int(bbox['x'])
                    y = int(bbox['y'])
                    width = int(bbox['width'])
                    height = int(bbox['height'])
                    
                    draw.rectangle(
                        [x, y, x + width, y + height],
                        fill=fill_color,
                        outline=outline_color,
                        width=3
                    )
                    
                    # Add label if provided
                    if action_descriptions and i < len(action_descriptions):
                        try:
                            try:
                                font = ImageFont.truetype("arial.ttf", 14)
                            except:
                                font = ImageFont.load_default()
                            
                            desc = action_descriptions[i]
                            text_bbox = draw.textbbox((0, 0), desc, font=font)
                            text_width = text_bbox[2] - text_bbox[0]
                            text_height = text_bbox[3] - text_bbox[1]
                            
                            text_x = x + (width - text_width) // 2
                            text_y = y - text_height - 5
                            
                            draw.rectangle(
                                [text_x - 3, text_y - 3, text_x + text_width + 3, text_y + text_height + 3],
                                fill=(0, 0, 0, 200),
                                outline=outline_color,
                                width=1
                            )
                            
                            draw.text(
                                (text_x, text_y),
                                desc,
                                fill=(255, 255, 255, 255),
                                font=font
                            )
                        except:
                            pass
                            
                except Exception as e:
                    print(f"⚠️  Could not highlight element {selector}: {e}")
                    continue
            
            # Display
            cv_image = cv2.cvtColor(np.array(img.convert('RGB')), cv2.COLOR_RGB2BGR)
            cv2.imshow(f"{self.window_name} - Multiple Elements", cv_image)
            cv2.waitKey(int(duration * 1000))
            cv2.destroyAllWindows()
            
            return True
            
        except Exception as e:
            print(f"⚠️  Error during multi-element visual feedback: {e}")
            try:
                cv2.destroyAllWindows()
            except:
                pass
            return False
    
    def show_page_state(
        self,
        page: Page,
        duration: float = 2.0,
        title: str = "Current Page State"
    ) -> bool:
        """
        Show a simple screenshot of the current page state.
        
        Args:
            page: Playwright Page object
            duration: How long to display (seconds)
            title: Window title
            
        Returns:
            True if successful, False otherwise
        """
        if not self.enabled:
            return False
        
        try:
            screenshot_bytes = page.screenshot(full_page=True, type='png')
            img = Image.open(io.BytesIO(screenshot_bytes))
            cv_image = cv2.cvtColor(np.array(img.convert('RGB')), cv2.COLOR_RGB2BGR)
            
            cv2.imshow(title, cv_image)
            cv2.waitKey(int(duration * 1000))
            cv2.destroyAllWindows()
            
            return True
            
        except Exception as e:
            print(f"⚠️  Error showing page state: {e}")
            try:
                cv2.destroyAllWindows()
            except:
                pass
            return False


# Global instance for easy access
_visual_feedback = VisualFeedback()


def highlight_element(
    page: Page,
    selector: str,
    color: str = 'green',
    duration: float = 1.5,
    action_description: str = None,
    enabled: bool = True
) -> bool:
    """
    Convenience function to highlight an element.
    
    Args:
        page: Playwright Page object
        selector: CSS selector for the element
        color: Color name
        duration: Display duration in seconds
        action_description: Optional action description
        enabled: Whether visual feedback is enabled
        
    Returns:
        True if successful, False otherwise
    """
    _visual_feedback.enabled = enabled
    return _visual_feedback.highlight_element(
        page, selector, color, duration, action_description
    )


def set_visual_feedback_enabled(enabled: bool):
    """Enable or disable visual feedback globally."""
    _visual_feedback.enabled = enabled


def get_visual_feedback() -> VisualFeedback:
    """Get the global visual feedback instance."""
    return _visual_feedback

