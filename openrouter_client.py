#!/usr/bin/env python3
"""
OpenRouter API Client
Utility for interacting with OpenRouter API for AI-powered features
"""

import requests
import json
import base64
from typing import Dict, List, Optional, Any
import os

class OpenRouterClient:
    """Client for OpenRouter API integration"""
    
    def __init__(self, api_key: str = None):
        """
        Initialize OpenRouter client
        
        Args:
            api_key: OpenRouter API key. If None, will try to load from config
        """
        self.api_key = api_key or self._load_api_key()
        self.base_url = "https://openrouter.ai/api/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",  # Optional: for analytics
        }
    
    def _load_api_key(self) -> str:
        """Load API key from config.yaml"""
        try:
            import yaml
            with open("config.yaml", 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return config.get('openrouter', {}).get('api_key', '')
        except Exception as e:
            print(f"⚠️  Could not load API key from config: {e}")
            return ""
    
    def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "openai/gpt-3.5-turbo",
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """
        Generate chat completion using OpenRouter
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: Model to use (default: gpt-3.5-turbo)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            **kwargs: Additional parameters
            
        Returns:
            Response dict with 'content' and other metadata, or None on error
        """
        if not self.api_key:
            print("❌ OpenRouter API key not configured")
            return None
        
        url = f"{self.base_url}/chat/completions"
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            **kwargs
        }
        
        try:
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'choices' in data and len(data['choices']) > 0:
                return {
                    'content': data['choices'][0]['message']['content'],
                    'model': data.get('model'),
                    'usage': data.get('usage', {}),
                    'full_response': data
                }
            else:
                print("⚠️  Unexpected response format from OpenRouter")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ OpenRouter API error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print(f"   Error details: {error_data}")
                except:
                    print(f"   Status code: {e.response.status_code}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return None
    
    def generate_cover_letter(
        self,
        job_title: str,
        company: str,
        job_description: str,
        resume_summary: str = ""
    ) -> Optional[str]:
        """
        Generate a personalized cover letter for a job application
        
        Args:
            job_title: Job title
            company: Company name
            job_description: Job description text
            resume_summary: Summary of candidate's experience (optional)
            
        Returns:
            Generated cover letter text or None on error
        """
        prompt = f"""Write a professional, concise cover letter for the following job application:

Job Title: {job_title}
Company: {company}

Job Description:
{job_description[:2000]}

{f"Candidate Background: {resume_summary[:500]}" if resume_summary else ""}

Requirements:
- Keep it professional and concise (3-4 paragraphs)
- Highlight relevant skills and experience
- Show enthusiasm for the role
- Do not include placeholders or generic statements
- Make it specific to this job and company
"""
        
        messages = [
            {"role": "system", "content": "You are a professional career advisor helping job seekers write effective cover letters."},
            {"role": "user", "content": prompt}
        ]
        
        result = self.chat_completion(messages, temperature=0.8, max_tokens=800)
        
        if result:
            return result['content']
        return None
    
    def answer_application_question(
        self,
        question: str,
        job_title: str,
        company: str,
        candidate_background: str = ""
    ) -> Optional[str]:
        """
        Generate an intelligent answer to an application question
        
        Args:
            question: The question from the application form
            job_title: Job title being applied for
            company: Company name
            candidate_background: Relevant background information
            
        Returns:
            Generated answer or None on error
        """
        prompt = f"""Answer the following job application question professionally and concisely:

Question: {question}

Job: {job_title} at {company}

{f"Relevant Background: {candidate_background[:500]}" if candidate_background else ""}

Requirements:
- Answer directly and professionally
- Be specific and relevant
- Keep it concise (2-3 sentences unless question requires more)
- Show enthusiasm and fit for the role
"""
        
        messages = [
            {"role": "system", "content": "You are a professional helping job seekers answer application questions effectively."},
            {"role": "user", "content": prompt}
        ]
        
        result = self.chat_completion(messages, temperature=0.7, max_tokens=300)
        
        if result:
            return result['content']
        return None
    
    def analyze_job_match(
        self,
        job_description: str,
        candidate_skills: List[str],
        candidate_experience: str = ""
    ) -> Optional[Dict[str, Any]]:
        """
        Analyze how well a candidate matches a job description
        
        Args:
            job_description: Full job description
            candidate_skills: List of candidate's skills
            candidate_experience: Candidate's experience summary
            
        Returns:
            Dict with match_score, strengths, gaps, and recommendations
        """
        skills_str = ", ".join(candidate_skills)
        
        prompt = f"""Analyze how well this candidate matches the job description:

Job Description:
{job_description[:2000]}

Candidate Skills: {skills_str}

{f"Candidate Experience: {candidate_experience[:500]}" if candidate_experience else ""}

Provide a JSON response with:
- match_score: 0-100 (how well they match)
- strengths: array of matching strengths
- gaps: array of missing requirements
- recommendation: "apply" or "skip" with brief reason
"""
        
        messages = [
            {"role": "system", "content": "You are a professional recruiter analyzing job-candidate fit. Respond only with valid JSON."},
            {"role": "user", "content": prompt}
        ]
        
        result = self.chat_completion(messages, temperature=0.3, max_tokens=500)
        
        if result:
            try:
                # Try to parse JSON from response
                content = result['content'].strip()
                # Remove markdown code blocks if present
                if content.startswith("```"):
                    content = content.split("```")[1]
                    if content.startswith("json"):
                        content = content[4:]
                content = content.strip()
                
                analysis = json.loads(content)
                return analysis
            except json.JSONDecodeError:
                # If not JSON, return as text
                return {
                    'match_score': None,
                    'analysis': result['content'],
                    'raw_response': result['content']
                }
        
        return None
    
    def improve_resume_for_job(
        self,
        current_resume_text: str,
        job_description: str,
        job_title: str
    ) -> Optional[str]:
        """
        Get suggestions for improving resume for a specific job
        
        Args:
            current_resume_text: Current resume content
            job_description: Job description
            job_title: Job title
            
        Returns:
            Suggestions for resume improvements
        """
        prompt = f"""Analyze this resume and provide specific suggestions to improve it for this job:

Job Title: {job_title}

Job Description:
{job_description[:2000]}

Current Resume:
{current_resume_text[:2000]}

Provide actionable suggestions:
- What keywords to add
- What skills to emphasize
- What experience to highlight
- Format improvements if needed
"""
        
        messages = [
            {"role": "system", "content": "You are a professional resume advisor helping candidates optimize their resumes."},
            {"role": "user", "content": prompt}
        ]
        
        result = self.chat_completion(messages, temperature=0.6, max_tokens=600)
        
        if result:
            return result['content']
        return None
    
    def list_models(self) -> Optional[List[Dict[str, Any]]]:
        """List available models from OpenRouter"""
        if not self.api_key:
            return None
        
        try:
            url = f"{self.base_url}/models"
            response = requests.get(url, headers=self.headers, timeout=10)
            response.raise_for_status()
            data = response.json()
            return data.get('data', [])
        except Exception as e:
            print(f"❌ Error fetching models: {e}")
            return None
    
    def get_ai_selector(
        self,
        page_html: str,
        screenshot_base64: str,
        element_description: str,
        model: str = "openai/gpt-4o-mini"
    ) -> Optional[str]:
        """
        Use AI to generate a robust CSS selector for an element based on HTML and screenshot.
        
        Args:
            page_html: HTML content of the page (from page.content())
            screenshot_base64: Base64-encoded screenshot (from page.screenshot())
            element_description: Description of the element to find (e.g., "Easy Apply button")
            model: Model to use (default: gpt-4o-mini for vision support)
            
        Returns:
            CSS selector string or None on error
        """
        if not self.api_key:
            print("❌ OpenRouter API key not configured")
            return None
        
        # Truncate HTML if too long (keep first 8000 chars for context)
        html_preview = page_html[:8000] if len(page_html) > 8000 else page_html
        
        prompt = f"""Given this HTML and screenshot, what is the most robust CSS selector for the element described as: '{element_description}'?

Requirements:
- The selector should be specific enough to uniquely identify the element
- Prefer data-testid, id, or class attributes if available
- Use stable selectors that won't break with minor UI changes
- Avoid overly specific selectors that depend on exact DOM structure
- Respond with ONLY the CSS selector string, nothing else
- If the element cannot be found, respond with "NOT_FOUND"

HTML Preview:
{html_preview}

Element Description: {element_description}

Respond with only the CSS selector:"""

        # Prepare messages with image support
        messages = [
            {
                "role": "system",
                "content": "You are a web automation expert. Analyze HTML and screenshots to generate robust CSS selectors. Respond with only the selector string."
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
                            "url": f"data:image/png;base64,{screenshot_base64}"
                        }
                    }
                ]
            }
        ]
        
        try:
            url = f"{self.base_url}/chat/completions"
            
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0.1,  # Low temperature for consistent selector generation
                "max_tokens": 200
            }
            
            response = requests.post(url, headers=self.headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            if 'choices' in data and len(data['choices']) > 0:
                selector = data['choices'][0]['message']['content'].strip()
                
                # Clean up the response (remove quotes, markdown, etc.)
                selector = selector.strip('"\'`')
                if selector.startswith('```'):
                    selector = selector.split('```')[1]
                    if selector.startswith('css'):
                        selector = selector[3:]
                selector = selector.strip()
                
                if selector.upper() == "NOT_FOUND":
                    print(f"⚠️  AI could not find element: {element_description}")
                    return None
                
                print(f"✅ AI generated selector for '{element_description}': {selector}")
                return selector
            else:
                print("⚠️  Unexpected response format from OpenRouter")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"❌ OpenRouter API error: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    print(f"   Error details: {error_data}")
                except:
                    print(f"   Status code: {e.response.status_code}")
            return None
        except Exception as e:
            print(f"❌ Unexpected error in get_ai_selector: {e}")
            return None

