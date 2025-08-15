import time, random, csv, pyautogui, pdb, traceback, sys, os
import cv2
import numpy as np
import pytesseract
from PIL import Image
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from datetime import date, datetime
from itertools import product
import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    ElementClickInterceptedException,
    StaleElementReferenceException
)

class LinkedinEasyApply:
    def __init__(self, parameters, driver):
        self.browser = driver
        self.email = parameters['email']
        self.password = parameters['password']
        self.disable_lock = parameters['disableAntiLock']
        self.company_blacklist = parameters.get('companyBlacklist', []) or []
        self.title_blacklist = parameters.get('titleBlacklist', []) or []
        self.poster_blacklist = parameters.get('posterBlacklist', []) or []
        self.positions = parameters.get('positions', [])
        self.locations = parameters.get('locations', [])
        self.residency = parameters.get('residentStatus', [])
        self.base_search_url = self.get_base_search_url(parameters)
        self.seen_jobs = []
        self.file_name = "output"
        self.unprepared_questions_file_name = "unprepared_questions"
        self.output_file_directory = parameters['outputFileDirectory']
        self.resume_dir = parameters['uploads']['resume']
        if 'coverLetter' in parameters['uploads']:
            self.cover_letter_dir = parameters['uploads']['coverLetter']
        else:
            self.cover_letter_dir = ''
        self.checkboxes = parameters.get('checkboxes', [])
        self.university_gpa = parameters['universityGpa']
        self.salary_minimum = parameters['salaryMinimum']
        self.notice_period = int(parameters['noticePeriod'])
        self.languages = parameters.get('languages', [])
        self.experience = parameters.get('experience', [])
        self.personal_info = parameters.get('personalInfo', [])
        self.eeo = parameters.get('eeo', [])
        self.experience_default = int(self.experience['default'])
        
        # User skills and preferences for job matching
        self.user_skills = parameters.get('userSkills', [
            'python', 'javascript', 'java', 'react', 'node.js', 'aws', 'sql',
            'machine learning', 'data analysis', 'web development'
        ])
        self.user_tech_stack = parameters.get('userTechStack', [
            'python', 'javascript', 'react', 'node.js', 'aws', 'sql', 'mongodb',
            'docker', 'git', 'agile', 'scrum'
        ])
        self.experience_level = parameters.get('userExperienceLevel', 'mid')  # junior, mid, senior
        self.prefer_remote = parameters.get('preferRemote', True)
        self.min_salary = parameters.get('minSalary', 50000)
        self.max_salary = parameters.get('maxSalary', 150000)
        
        # Current job tracking for skill editor
        self.current_job_title = None
        self.current_company = None

    def read_job_description_ocr(self, job_element=None):
        """
        Read job description using computer vision and OCR
        Returns the extracted text from the job description area
        """
        try:
            print("Reading job description using OCR...")
            
            # If no specific element provided, try to find the job description container
            if job_element is None:
                try:
                    # Try multiple selectors for job description
                    description_selectors = [
                        "jobs-search__job-details--container",
                        "jobs-description",
                        "job-description",
                        "description__text",
                        "jobs-box__html-content",
                        "jobs-description-content__text",
                        "show-more-less-html__markup"
                    ]
                    
                    for selector in description_selectors:
                        try:
                            job_element = self.browser.find_element(By.CLASS_NAME, selector)
                            if job_element:
                                break
                        except:
                            continue
                    
                    if not job_element:
                        print("Could not find job description container")
                        return ""
                        
                except Exception as e:
                    print(f"Error finding job description container: {str(e)}")
                    return ""
            
            # Try OCR first, fall back to text if it fails
            try:
                # Take a screenshot of the job description area
                # Scroll the element into view
                self.browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", job_element)
                time.sleep(1)
                
                # Get element location and size
                location = job_element.location
                size = job_element.size
                
                # Take full page screenshot
                screenshot_path = "temp_job_screenshot.png"
                self.browser.save_screenshot(screenshot_path)
                
                # Load the screenshot
                full_screenshot = cv2.imread(screenshot_path)
                
                # Calculate coordinates for cropping (accounting for browser UI elements)
                x = int(location['x'])
                y = int(location['y'])
                w = int(size['width'])
                h = int(size['height'])
                
                # Crop the job description area
                job_description_img = full_screenshot[y:y+h, x:x+w]
                
                # Clean up temporary file
                if os.path.exists(screenshot_path):
                    os.remove(screenshot_path)
                
                if job_description_img.size == 0:
                    print("Failed to capture job description image")
                    return ""
                
                # Preprocess image for better OCR
                # Convert to grayscale
                gray = cv2.cvtColor(job_description_img, cv2.COLOR_BGR2GRAY)
                
                # Apply thresholding to get binary image
                _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
                
                # Apply morphological operations to clean up the image
                kernel = np.ones((1, 1), np.uint8)
                cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
                
                # Use pytesseract to extract text
                try:
                    # Try with cleaned image first
                    text = pytesseract.image_to_string(cleaned, config='--psm 6')
                    
                    # If no text found, try with original grayscale image
                    if not text.strip():
                        text = pytesseract.image_to_string(gray, config='--psm 6')
                    
                    # If still no text, try with different PSM modes
                    if not text.strip():
                        text = pytesseract.image_to_string(gray, config='--psm 3')
                    
                    # Clean up the extracted text
                    if text:
                        text = self.clean_job_description_text(text)
                        print(f"Successfully extracted {len(text)} characters from job description using OCR")
                        return text
                    else:
                        print("No text extracted from job description image")
                        return ""
                        
                except Exception as ocr_error:
                    print(f"OCR error: {str(ocr_error)}")
                    # Fall back to text-based reading
                    return self.read_job_description_text_only(job_element)
                    
            except Exception as screenshot_error:
                print(f"Screenshot error: {str(screenshot_error)}")
                # Fall back to text-based reading
                return self.read_job_description_text_only(job_element)
                
        except Exception as e:
            print(f"Error in OCR job description reading: {str(e)}")
            # Fall back to text-based reading
            return self.read_job_description_text_only(job_element)
    
    def read_job_description_text_only(self, job_element=None):
        """
        Read job description using HTML text instead of OCR
        This is a fallback method when OCR is not available
        """
        try:
            print("Reading job description using HTML text...")
            
            if job_element is None:
                # Try to find the job description container
                description_selectors = [
                    "jobs-search__job-details--container",
                    "jobs-description",
                    "job-description",
                    "description__text",
                    "jobs-box__html-content",
                    "jobs-description-content__text",
                    "show-more-less-html__markup"
                ]
                
                for selector in description_selectors:
                    try:
                        job_element = self.browser.find_element(By.CLASS_NAME, selector)
                        if job_element:
                            break
                    except:
                        continue
                
                if not job_element:
                    print("Could not find job description container")
                    return ""
            
            # Get text directly from HTML
            job_text = job_element.text
            
            if job_text:
                # Clean up the text
                job_text = self.clean_job_description_text(job_text)
                print(f"Successfully extracted {len(job_text)} characters from job description using HTML text")
                return job_text
            else:
                print("No text found in job description HTML")
                return ""
                
        except Exception as e:
            print(f"Error reading job description HTML: {str(e)}")
            return ""
    
    def clean_job_description_text(self, text):
        """
        Clean and normalize job description text for better analysis
        """
        if not text:
            return ""
        
        # Remove extra whitespace and normalize
        text = ' '.join(text.split())
        
        # Remove common LinkedIn artifacts
        text = text.replace('LinkedIn', '')
        text = text.replace('Easy Apply', '')
        text = text.replace('Apply now', '')
        
        # Remove excessive punctuation
        text = text.replace('...', '.')
        text = text.replace('..', '.')
        
        # Normalize line breaks
        text = text.replace('\n', ' ')
        text = text.replace('\r', ' ')
        
        # Remove multiple spaces
        text = ' '.join(text.split())
        
        return text.strip()
    
    def extract_skills_from_text(self, text):
        """
        Extract skills and technical requirements from job description text
        Returns a list of identified skills
        """
        if not text:
            return []
        
        # Convert to lowercase for matching
        text_lower = text.lower()
        
        # Define skill categories and keywords
        programming_languages = [
            'python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'swift',
            'kotlin', 'scala', 'r', 'matlab', 'perl', 'bash', 'powershell', 'typescript'
        ]
        
        frameworks_libraries = [
            'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask', 'spring',
            'laravel', 'asp.net', 'jquery', 'bootstrap', 'tailwind', 'material-ui',
            'redux', 'mobx', 'graphql', 'rest api', 'api development'
        ]
        
        databases = [
            'sql', 'mysql', 'postgresql', 'oracle', 'sql server', 'sqlite', 'mongodb',
            'redis', 'cassandra', 'dynamodb', 'elasticsearch', 'neo4j', 'firebase'
        ]
        
        cloud_platforms = [
            'aws', 'azure', 'google cloud', 'gcp', 'heroku', 'digitalocean', 'linode',
            'kubernetes', 'docker', 'terraform', 'cloudformation', 'serverless'
        ]
        
        devops_tools = [
            'git', 'github', 'gitlab', 'jenkins', 'circleci', 'travis ci', 'gitlab ci',
            'ansible', 'chef', 'puppet', 'vagrant', 'virtualbox', 'vmware'
        ]
        
        methodologies = [
            'agile', 'scrum', 'kanban', 'waterfall', 'devops', 'ci/cd', 'tdd', 'bdd',
            'lean', 'six sigma', 'prince2', 'pmp'
        ]
        
        soft_skills = [
            'leadership', 'communication', 'teamwork', 'problem solving', 'analytical thinking',
            'creativity', 'adaptability', 'time management', 'project management'
        ]
        
        # Combine all skills
        all_skills = (
            programming_languages + frameworks_libraries + databases + 
            cloud_platforms + devops_tools + methodologies + soft_skills
        )
        
        # Find skills in text
        found_skills = []
        for skill in all_skills:
            if skill in text_lower:
                found_skills.append(skill)
        
        # Look for additional patterns
        # Years of experience
        experience_patterns = [
            r'(\d+)\+?\s*years?\s*of\s*experience',
            r'experience:\s*(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?\s*in\s*[a-zA-Z\s]+'
        ]
        
        for pattern in experience_patterns:
            matches = re.findall(pattern, text_lower)
            if matches:
                found_skills.append(f"{matches[0]}+ years experience")
        
        # Education requirements
        education_keywords = ['bachelor', 'master', 'phd', 'degree', 'diploma', 'certification']
        for keyword in education_keywords:
            if keyword in text_lower:
                found_skills.append(f"education: {keyword}")
        
        # Remove duplicates and return
        return list(set(found_skills))
    
    def calculate_skill_match_score(self, job_skills, user_skills):
        """
        Calculate how well user skills match job requirements
        Returns a score from 0-100 and detailed analysis
        """
        if not job_skills or not user_skills:
            return {
                'score': 0,
                'matched_skills': [],
                'missing_skills': job_skills,
                'extra_skills': user_skills,
                'match_percentage': 0
            }
        
        # Convert all skills to lowercase for comparison
        job_skills_lower = [skill.lower() for skill in job_skills]
        user_skills_lower = [skill.lower() for skill in user_skills]
        
        # Convert to sets for comparison
        job_skills_set = set(job_skills_lower)
        user_skills_set = set(user_skills_lower)
        
        # Calculate matches
        matched_skills = job_skills_set.intersection(user_skills_set)
        missing_skills = job_skills_set - user_skills_set
        extra_skills = user_skills_set - job_skills_set
        
        # Map back to original case for display
        matched_skills_original = [skill for skill in job_skills if skill.lower() in matched_skills]
        missing_skills_original = [skill for skill in job_skills if skill.lower() in missing_skills]
        extra_skills_original = [skill for skill in user_skills if skill.lower() in extra_skills]
        
        # Calculate score
        if len(job_skills_set) == 0:
            match_percentage = 0
        else:
            match_percentage = (len(matched_skills) / len(job_skills_set)) * 100
        
        # Weight the score based on importance
        score = match_percentage
        
        # Bonus for having extra relevant skills
        if len(extra_skills) > 0:
            score += min(10, len(extra_skills) * 2)  # Max 10 bonus points
        
        # Cap score at 100
        score = min(100, score)
        
        return {
            'score': round(score, 1),
            'matched_skills': matched_skills_original,
            'missing_skills': missing_skills_original,
            'extra_skills': extra_skills_original,
            'match_percentage': round(match_percentage, 1)
        }

    def analyze_job_description(self, job_text):
        """
        Analyze the job description text for key information
        Returns a dictionary with analysis results
        """
        if not job_text:
            return {}
        
        analysis = {}
        
        # Convert to lowercase for analysis
        text_lower = job_text.lower()
        
        # Extract skills from job description
        job_skills = self.extract_skills_from_text(job_text)
        analysis['job_skills'] = job_skills
        
        # Calculate skill match with user skills
        if hasattr(self, 'user_skills') and self.user_skills:
            skill_match = self.calculate_skill_match_score(job_skills, self.user_skills)
            analysis['skill_match'] = skill_match
            analysis['skill_match_score'] = skill_match['score']
            analysis['matched_skills'] = skill_match['matched_skills']
            analysis['missing_skills'] = skill_match['missing_skills']
            analysis['extra_skills'] = skill_match['extra_skills']
        
        # Experience level detection
        experience_keywords = {
            'junior': ['junior', 'entry level', 'entry-level', '0-2 years', '1-2 years', 'new grad', 'recent graduate'],
            'mid': ['mid level', 'mid-level', 'intermediate', '3-5 years', '4-6 years', 'mid-senior'],
            'senior': ['senior', 'lead', 'principal', 'staff', '5+ years', '7+ years', '10+ years', 'expert']
        }
        
        for level, keywords in experience_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                analysis['experience_level'] = level
                break
        
        if 'experience_level' not in analysis:
            analysis['experience_level'] = 'unknown'
        
        # Remote work detection
        remote_keywords = ['remote', 'work from home', 'wfh', 'telecommute', 'virtual', 'distributed team']
        analysis['remote_work'] = any(keyword in text_lower for keyword in remote_keywords)
        
        # Salary detection
        salary_keywords = ['salary', 'compensation', 'pay', 'rate', '$', 'dollars', 'annual', 'yearly']
        analysis['salary_mentioned'] = any(keyword in text_lower for keyword in salary_keywords)
        
        # Tech stack analysis
        tech_keywords = [
            'python', 'javascript', 'java', 'react', 'node.js', 'aws', 'sql', 'mongodb',
            'docker', 'kubernetes', 'git', 'agile', 'scrum', 'machine learning', 'ai',
            'data science', 'cloud', 'devops', 'ci/cd'
        ]
        
        found_tech = []
        for tech in tech_keywords:
            if tech in text_lower:
                found_tech.append(tech)
        
        analysis['tech_stack'] = found_tech
        
        # Red flag detection
        red_flags = []
        
        # Unpaid/volunteer work
        unpaid_keywords = ['unpaid', 'volunteer', 'internship', 'no pay', 'experience only']
        if any(keyword in text_lower for keyword in unpaid_keywords):
            red_flags.append('unpaid/volunteer position')
        
        # Commission only
        if 'commission only' in text_lower or 'commission-based' in text_lower:
            red_flags.append('commission-only compensation')
        
        # No benefits
        if 'no benefits' in text_lower or 'benefits not included' in text_lower:
            red_flags.append('no benefits mentioned')
        
        # Excessive overtime
        overtime_keywords = ['24/7', 'on-call', 'overtime required', 'weekend work', 'holiday work']
        if any(keyword in text_lower for keyword in overtime_keywords):
            red_flags.append('excessive overtime requirements')
        
        # High pressure
        pressure_keywords = ['fast-paced', 'high-pressure', 'deadline-driven', 'crunch time']
        if any(keyword in text_lower for keyword in pressure_keywords):
            red_flags.append('high-pressure environment')
        
        analysis['red_flags'] = red_flags
        
        # Job type detection
        job_types = {
            'full_time': ['full-time', 'full time', 'permanent', 'regular'],
            'part_time': ['part-time', 'part time', 'temporary', 'contract'],
            'contract': ['contract', 'freelance', 'consulting', 'project-based']
        }
        
        for job_type, keywords in job_types.items():
            if any(keyword in text_lower for keyword in keywords):
                analysis['job_type'] = job_type
                break
        
        if 'job_type' not in analysis:
            analysis['job_type'] = 'unknown'
        
        # Location requirements
        location_keywords = ['on-site', 'onsite', 'in-office', 'hybrid', 'flexible']
        if any(keyword in text_lower for keyword in location_keywords):
            analysis['location_type'] = 'on-site'
        elif analysis.get('remote_work', False):
            analysis['location_type'] = 'remote'
        else:
            analysis['location_type'] = 'unknown'
        
        return analysis

    def should_apply_to_job(self, analysis, job_text):
        """
        Determine whether to apply to a job based on analysis
        Returns True if should apply, False if should skip
        """
        if not analysis:
            print("⚠️  No job analysis available. Proceeding with application.")
            return True
        
        # Check for critical red flags
        red_flags = analysis.get('red_flags', [])
        if red_flags:
            print(f"🚨 Red flags detected: {', '.join(red_flags)}")
            
            # Critical red flags that should always cause a skip
            critical_flags = ['unpaid/volunteer position', 'commission-only compensation']
            if any(flag in red_flags for flag in critical_flags):
                print("❌ Critical red flag detected. Skipping this job.")
                return False
        
        # Check experience level compatibility
        user_experience = getattr(self, 'experience_level', 'mid')
        job_experience = analysis.get('experience_level', 'unknown')
        
        if user_experience and job_experience != 'unknown':
            experience_compatibility = self.check_experience_compatibility(user_experience, job_experience)
            if not experience_compatibility:
                print(f"❌ Experience level mismatch: You're {user_experience}, job requires {job_experience}")
                return False
            else:
                print(f"✅ Experience level compatible: {user_experience} → {job_experience}")
        
        # Check skill match score
        skill_match_score = analysis.get('skill_match_score', 0)
        if skill_match_score > 0:
            print(f"🎯 Skill Match Score: {skill_match_score}/100")
            
            # Show skill analysis
            matched_skills = analysis.get('matched_skills', [])
            missing_skills = analysis.get('missing_skills', [])
            extra_skills = analysis.get('extra_skills', [])
            
            if matched_skills:
                print(f"  ✅ Matched Skills: {', '.join(matched_skills[:5])}{'...' if len(matched_skills) > 5 else ''}")
            
            if missing_skills:
                print(f"  ❌ Missing Skills: {', '.join(missing_skills[:5])}{'...' if len(missing_skills) > 5 else ''}")
            
            if extra_skills:
                print(f"  🎁 Extra Skills: {', '.join(extra_skills[:5])}{'...' if len(extra_skills) > 5 else ''}")
            
            # Decision based on skill match
            if skill_match_score >= 80:
                print("🎉 Excellent skill match! Highly recommended to apply.")
                return True
            elif skill_match_score >= 60:
                print("✅ Good skill match. Recommended to apply.")
                return True
            elif skill_match_score >= 40:
                print("⚠️  Moderate skill match. Consider applying if interested.")
                return True
            else:
                print("❌ Low skill match. Consider skipping unless very interested.")
                
                # Show skill editor GUI for low skill matches
                if missing_skills and len(missing_skills) > 2:  # Only show if there are significant missing skills
                    print("\n🎯 Skill mismatch detected! Opening skill editor...")
                    print("💡 You can add missing skills to improve your match for future jobs.")
                    
                    try:
                        # Import the skill editor
                        from skill_editor_gui import show_skill_editor
                        
                        # Get current job info for the GUI
                        job_title = getattr(self, 'current_job_title', 'Unknown Position')
                        company = getattr(self, 'current_company', 'Unknown Company')
                        
                        # Show the skill editor
                        added_skills, removed_skills = show_skill_editor(
                            missing_skills, 
                            self.user_skills, 
                            job_title, 
                            company
                        )
                        
                        if added_skills or removed_skills:
                            print(f"✅ Skills updated - Added: {added_skills}, Removed: {removed_skills}")
                            
                            # Update the bot's skill lists
                            if added_skills:
                                for skill in added_skills:
                                    if skill not in self.user_skills:
                                        self.user_skills.append(skill)
                                    if skill not in self.user_tech_stack:
                                        self.user_tech_stack.append(skill)
                                        
                            if removed_skills:
                                for skill in removed_skills:
                                    if skill in self.user_skills:
                                        self.user_skills.remove(skill)
                                    if skill in self.user_tech_stack:
                                        self.user_tech_stack.remove(skill)
                            
                            print("🔄 Skill lists updated for this session!")
                            
                            # Recalculate skill match with updated skills
                            if 'job_skills' in analysis:
                                updated_skill_match = self.calculate_skill_match_score(
                                    analysis['job_skills'], 
                                    self.user_skills
                                )
                                print(f"🔄 Updated Skill Match Score: {updated_skill_match['score']}/100")
                                
                                # If score improved significantly, reconsider applying
                                if updated_skill_match['score'] >= 40:
                                    print("✅ Skill match improved! Proceeding with application.")
                                    return True
                        
                    except ImportError:
                        print("⚠️  Skill editor GUI not available. Continuing with current decision.")
                    except Exception as e:
                        print(f"⚠️  Error showing skill editor: {str(e)}")
                        print("Continuing with current decision.")
                
                return False
        
        # Check remote work preference
        prefer_remote = getattr(self, 'prefer_remote', False)
        job_remote = analysis.get('remote_work', False)
        
        if prefer_remote and not job_remote:
            print("⚠️  You prefer remote work, but this job is not remote.")
            # Don't skip, just warn
        elif not prefer_remote and job_remote:
            print("✅ Remote work available, which might be a plus.")
        
        # Check tech stack overlap
        user_tech_stack = getattr(self, 'user_tech_stack', [])
        job_tech_stack = analysis.get('tech_stack', [])
        
        if user_tech_stack and job_tech_stack:
            tech_overlap = len(set(user_tech_stack) & set(job_tech_stack))
            tech_total = len(set(job_tech_stack))
            
            if tech_total > 0:
                tech_match_percentage = (tech_overlap / tech_total) * 100
                print(f"🔧 Tech Stack Match: {tech_overlap}/{tech_total} technologies ({tech_match_percentage:.1f}%)")
                
                if tech_match_percentage >= 50:
                    print("✅ Good tech stack alignment.")
                elif tech_match_percentage >= 25:
                    print("⚠️  Moderate tech stack alignment.")
                else:
                    print("❌ Low tech stack alignment.")
        
        # Overall decision
        print("✅ Job analysis completed. Proceeding with application.")
        return True
    
    def check_experience_compatibility(self, user_level, job_level):
        """
        Check if user experience level is compatible with job requirements
        """
        if user_level == job_level:
            return True
        
        # Allow some flexibility
        if user_level == 'mid' and job_level == 'senior':
            return True  # Mid-level can apply to senior positions
        elif user_level == 'senior' and job_level == 'mid':
            return True  # Senior can apply to mid-level positions
        elif user_level == 'mid' and job_level == 'junior':
            return True  # Mid-level can apply to junior positions (overqualified but acceptable)
        
        return False

    def login(self):
        try:
            # Check if the "chrome_bot" directory exists
            print("Attempting to restore previous session...")
            if os.path.exists("chrome_bot"):
                self.browser.get("https://www.linkedin.com/feed/")
                time.sleep(random.uniform(5, 10))

                # Check if the current URL is the feed page
                if self.browser.current_url != "https://www.linkedin.com/feed/":
                    print("Feed page not loaded, proceeding to login.")
                    self.load_login_page_and_login()
            else:
                print("No session found, proceeding to login.")
                self.load_login_page_and_login()

        except TimeoutException:
            print("Timeout occurred, checking for security challenges...")
            self.security_check()
            # raise Exception("Could not login!")

    def security_check(self):
        current_url = self.browser.current_url
        page_source = self.browser.page_source

        if '/checkpoint/challenge/' in current_url or 'security check' in page_source or 'quick verification' in page_source or 'Check your LinkedIn app' in page_source:
            input("Please complete the security check and press enter on this console when it is done.")
            time.sleep(random.uniform(5.5, 10.5))

    def load_login_page_and_login(self):
        self.browser.get("https://www.linkedin.com/login")

        # Wait for the username field to be present
        WebDriverWait(self.browser, 10).until(
            EC.presence_of_element_located((By.ID, "username"))
        )

        self.browser.find_element(By.ID, "username").send_keys(self.email)
        self.browser.find_element(By.ID, "password").send_keys(self.password)
        self.browser.find_element(By.CSS_SELECTOR, ".btn__primary--large").click()

        # Wait for the feed page to load after login
        WebDriverWait(self.browser, 10).until(
            EC.url_contains("https://www.linkedin.com/feed/")
        )

        time.sleep(random.uniform(5, 10))

    def start_applying(self):
        searches = list(product(self.positions, self.locations))
        random.shuffle(searches)

        page_sleep = 0
        minimum_time = 60 * 15  # minimum time bot should run before taking a break
        minimum_page_time = time.time() + minimum_time

        for (position, location) in searches:
            location_url = "&location=" + location
            job_page_number = -1

            print("Starting the search for " + position + " in " + location + ".")

            try:
                while True:
                    page_sleep += 1
                    job_page_number += 1
                    print("Going to job page " + str(job_page_number))
                    self.next_job_page(position, location_url, job_page_number)
                    time.sleep(random.uniform(1.5, 3.5))
                    print("Starting the application process for this page...")
                    self.apply_jobs(location)
                    print("Job applications on this page have been successfully completed.")

                    time_left = minimum_page_time - time.time()
                    if time_left > 0:
                        print("Sleeping for " + str(time_left) + " seconds.")
                        time.sleep(time_left)
                        minimum_page_time = time.time() + minimum_time
                    if page_sleep % 5 == 0:
                        sleep_time = random.randint(180, 300)  # Changed from 500, 900 {seconds}
                        print("Sleeping for " + str(sleep_time / 60) + " minutes.")
                        time.sleep(sleep_time)
                        page_sleep += 1
            except Exception as e:
                print(f"Error in search for {position} in {location}: {str(e)}")
                traceback.print_exc()
                # Wait a bit before continuing to next search
                time.sleep(random.uniform(10, 20))
                continue

            time_left = minimum_page_time - time.time()
            if time_left > 0:
                print("Sleeping for " + str(time_left) + " seconds.")
                time.sleep(time_left)
                minimum_page_time = time.time() + minimum_time
            if page_sleep % 5 == 0:
                sleep_time = random.randint(500, 900)
                print("Sleeping for " + str(sleep_time / 60) + " minutes.")
                time.sleep(sleep_time)
                page_sleep += 1

    def apply_jobs(self, location):
        no_jobs_text = ""
        try:
            no_jobs_element = self.browser.find_element(By.CLASS_NAME,
                                                        'jobs-search-two-pane__no-results-banner--expand')
            no_jobs_text = no_jobs_element.text
        except:
            pass
        if 'No matching jobs found' in no_jobs_text:
            raise Exception("No more jobs on this page.")

        if 'unfortunately, things are' in self.browser.page_source.lower():
            raise Exception("No more jobs on this page.")

        job_results_header = ""
        maybe_jobs_crap = ""
        job_results_header = self.browser.find_element(By.CLASS_NAME, "jobs-search-results-list__text")
        maybe_jobs_crap = job_results_header.text

        if 'Jobs you may be interested in' in maybe_jobs_crap:
            raise Exception("Nothing to do here, moving forward...")

        try:
            # Define the XPaths for potentially different regions
            xpath_region1 = "/html/body/div[6]/div[3]/div[4]/div/div/main/div/div[2]/div[1]/div"
            xpath_region2 = "/html/body/div[5]/div[3]/div[4]/div/div/main/div/div[2]/div[1]/div"
            job_list = []

            # Attempt to locate the element using XPaths
            try:
                job_results = self.browser.find_element(By.XPATH, xpath_region1)
                ul_xpath = "/html/body/div[6]/div[3]/div[4]/div/div/main/div/div[2]/div[1]/div/ul"
                ul_element = self.browser.find_element(By.XPATH, ul_xpath)
                ul_element_class = ul_element.get_attribute("class").split()[0]
                print(f"Found using xpath_region1 and detected ul_element as {ul_element_class} based on {ul_xpath}")

            except NoSuchElementException:
                job_results = self.browser.find_element(By.XPATH, xpath_region2)
                ul_xpath = "/html/body/div[5]/div[3]/div[4]/div/div/main/div/div[2]/div[1]/div/ul"
                ul_element = self.browser.find_element(By.XPATH, ul_xpath)
                ul_element_class = ul_element.get_attribute("class").split()[0]
                print(f"Found using xpath_region2 and detected ul_element as {ul_element_class} based on {ul_xpath}")

            # Extract the random class name dynamically
            random_class = job_results.get_attribute("class").split()[0]
            print(f"Random class detected: {random_class}")

            # Use the detected class name to find the element
            job_results_by_class = self.browser.find_element(By.CSS_SELECTOR, f".{random_class}")
            print(f"job_results: {job_results_by_class}")
            print("Successfully located the element using the random class name.")

            # Scroll logic (currently disabled for testing)
            self.scroll_slow(job_results_by_class)  # Scroll down
            self.scroll_slow(job_results_by_class, step=300, reverse=True)  # Scroll up

            # Find job list elements
            job_list = self.browser.find_elements(By.CLASS_NAME, ul_element_class)[0].find_elements(By.CLASS_NAME, 'scaffold-layout__list-item')
            print(f"List of jobs: {job_list}")

            if len(job_list) == 0:
                raise Exception("No more jobs on this page.")

        except NoSuchElementException:
            print("No job results found using the specified XPaths or class.")
            # Try to refresh the page and retry
            try:
                self.browser.refresh()
                time.sleep(5)
                return self.apply_jobs(location)  # Recursive retry
            except:
                pass

        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            # Try to refresh the page and retry
            try:
                self.browser.refresh()
                time.sleep(5)
                return self.apply_jobs(location)  # Recursive retry
            except:
                pass

        job_index = 0
        while job_index < len(job_list):
            try:
                job_tile = job_list[job_index]
                job_title, company, poster, job_location, apply_method, link = "", "", "", "", "", ""

                try:
                    ## patch to incorporate new 'verification' crap by LinkedIn
                    # job_title = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title').text # original code
                    job_title_element = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title--link')
                    job_title = job_title_element.find_element(By.TAG_NAME, 'strong').text

                    link = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title--link').get_attribute('href').split('?')[0]
                except Exception as title_error:
                    print(f"Could not extract job title/link: {str(title_error)}")
                    # Skip this job and continue with the next one
                    job_index += 1
                    continue
                
                try:
                    # company = job_tile.find_element(By.CLASS_NAME, 'job-card-container__primary-description').text # original code
                    company = job_tile.find_element(By.CLASS_NAME, 'artdeco-entity-lockup__subtitle').text
                except:
                    pass
                try:
                    # get the name of the person who posted for the position, if any is listed
                    hiring_line = job_tile.find_element(By.XPATH, '//span[contains(.,\' is hiring for this\')]')
                    hiring_line_text = hiring_line.text
                    name_terminating_index = hiring_line_text.find(' is hiring for this')
                    if name_terminating_index != -1:
                        poster = hiring_line_text[:name_terminating_index]
                except:
                    pass
                try:
                    job_location = job_tile.find_element(By.CLASS_NAME, 'job-card-container__metadata-item').text
                except:
                    pass
                try:
                    apply_method = job_tile.find_element(By.CLASS_NAME, 'job-card-container__apply-method').text
                except:
                    pass

                contains_blacklisted_keywords = False
                job_title_parsed = job_title.lower().split(' ')

                for word in self.title_blacklist:
                    if word.lower() in job_title_parsed:
                        contains_blacklisted_keywords = True
                        break

                if company.lower() not in [word.lower() for word in self.company_blacklist] and \
                        poster.lower() not in [word.lower() for word in self.poster_blacklist] and \
                        contains_blacklisted_keywords is False and link not in self.seen_jobs:
                    try:
                        max_retries = 3
                        retries = 0
                        while retries < max_retries:
                            try:
                                job_el = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title--link')
                                
                                # Scroll the element into view first
                                self.browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", job_el)
                                time.sleep(1)
                                
                                # Try to click with JavaScript if regular click fails
                                try:
                                    job_el.click()
                                except Exception as click_error:
                                    if "element click intercepted" in str(click_error).lower():
                                        # Use JavaScript click as fallback
                                        self.browser.execute_script("arguments[0].click();", job_el)
                                    else:
                                        raise click_error
                                
                                break

                            except StaleElementReferenceException:
                                retries += 1
                                time.sleep(1)
                                continue
                            except Exception as e:
                                if "element click intercepted" in str(e).lower():
                                    retries += 1
                                    time.sleep(2)
                                    continue
                                else:
                                    raise e

                        time.sleep(random.uniform(3, 5))

                        try:
                            done_applying = self.apply_to_job(job_tile)
                            if done_applying:
                                print(f"Application sent to {company} for the position of {job_title}.")
                            else:
                                print(f"An application for a job at {company} has been submitted earlier.")
                        except Exception as apply_error:
                            print(f"Error applying to job: {str(apply_error)}")
                            temp = self.file_name
                            self.file_name = "failed"
                            print("Failed to apply to job. Please submit a bug report with this link: " + link)
                            try:
                                self.write_to_file(company, job_title, link, job_location, location)
                            except Exception as write_error:
                                print(f"Could not write to failed file: {str(write_error)}")
                            self.file_name = temp
                            print(f'updated {temp}.')

                        try:
                            self.write_to_file(company, job_title, link, job_location, location)
                        except Exception:
                            print(
                                f"Unable to save the job information in the file. The job title {job_title} or company {company} cannot contain special characters,")
                            traceback.print_exc()
                            
                    except Exception as job_error:
                        print(f"Error processing job at {company}: {str(job_error)}")
                        traceback.print_exc()
                        print(f"Could not apply to the job in {company}")
                        
                        # If we get too many stale element errors, refresh the page
                        if "stale element" in str(job_error).lower():
                            print("Detected stale elements, refreshing page...")
                            try:
                                self.browser.refresh()
                                time.sleep(5)
                                # Re-fetch the job list
                                return self.apply_jobs(location)
                            except:
                                pass
                        
                        job_index += 1
                        continue
                        
                else:
                    print(f"Job for {company} by {poster} contains a blacklisted word {word}.")

                self.seen_jobs += link
                job_index += 1
                
            except Exception as loop_error:
                print(f"Error in job processing loop: {str(loop_error)}")
                traceback.print_exc()
                job_index += 1
                continue

    def apply_to_job(self, job_tile):
        """
        Apply to a specific job
        """
        try:
            # Extract job information
            job_title, company, poster, job_location, apply_method, link = "", "", "", "", "", ""
            
            try:
                job_title_element = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title--link')
                job_title = job_title_element.find_element(By.TAG_NAME, 'strong').text
                link = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title--link').get_attribute('href').split('?')[0]
            except Exception as title_error:
                print(f"Could not extract job title/link: {str(title_error)}")
                return False
            
            try:
                company = job_tile.find_element(By.CLASS_NAME, 'artdeco-entity-lockup__subtitle').text
            except:
                pass
                
            try:
                hiring_line = job_tile.find_element(By.XPATH, '//span[contains(.,\' is hiring for this\')]')
                hiring_line_text = hiring_line.text
                name_terminating_index = hiring_line_text.find(' is hiring for this')
                if name_terminating_index != -1:
                    poster = hiring_line_text[:name_terminating_index]
            except:
                pass
                
            try:
                job_location = job_tile.find_element(By.CLASS_NAME, 'job-card-container__metadata-item').text
            except:
                pass
                
            try:
                apply_method = job_tile.find_element(By.CLASS_NAME, 'job-card-container__apply-method').text
            except:
                pass
            
            # Store current job info for skill editor
            self.current_job_title = job_title
            self.current_company = company
            
            print(f"Starting the job application...")
            print(f"Job: {job_title}")
            print(f"Company: {company}")
            print(f"Location: {job_location}")
            
            # Check if already applied
            if link in self.seen_jobs:
                print(f"Already applied to {job_title} at {company}. Skipping...")
                return False
            
            # Try to click on the job to open it
            max_retries = 3
            retries = 0
            while retries < max_retries:
                try:
                    job_el = job_tile.find_element(By.CLASS_NAME, 'job-card-list__title--link')
                    
                    # Scroll the element into view first
                    self.browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", job_el)
                    time.sleep(1)
                    
                    # Try to click with JavaScript if regular click fails
                    try:
                        job_el.click()
                    except Exception as click_error:
                        if "element click intercepted" in str(click_error).lower():
                            # Use JavaScript click as fallback
                            self.browser.execute_script("arguments[0].click();", job_el)
                        else:
                            raise click_error
                    
                    break
                    
                except StaleElementReferenceException:
                    retries += 1
                    time.sleep(1)
                    continue
                except Exception as e:
                    if "element click intercepted" in str(e).lower():
                        retries += 1
                        time.sleep(2)
                        continue
                    else:
                        raise e
            
            # Wait for job details to load
            time.sleep(3)
            
            # Find and click the Easy Apply button
            try:
                easy_apply_button = None
                easy_apply_selectors = [
                    "button[data-control-name='jobdetails_topcard_inapply']",
                    "button[data-control-name='jobdetails_topcard_apply']",
                    "button[aria-label*='Easy Apply']",
                    "button[aria-label*='Apply']",
                    "button:contains('Easy Apply')",
                    "button:contains('Apply')"
                ]
                
                for selector in easy_apply_selectors:
                    try:
                        if 'contains' in selector:
                            # Handle :contains selector manually
                            buttons = self.browser.find_elements(By.TAG_NAME, 'button')
                            for button in buttons:
                                if 'Easy Apply' in button.text or 'Apply' in button.text:
                                    easy_apply_button = button
                                    break
                        else:
                            easy_apply_button = self.browser.find_element(By.CSS_SELECTOR, selector)
                        if easy_apply_button:
                            break
                    except:
                        continue
                
                if not easy_apply_button:
                    print("❌ Easy Apply button not found. This job may not support Easy Apply.")
                    return False
                
                # Click the Easy Apply button with retry logic
                max_click_attempts = 3
                for attempt in range(max_click_attempts):
                    try:
                        # Scroll button into view
                        self.browser.execute_script("arguments[0].scrollIntoView({block: 'center'});", easy_apply_button)
                        time.sleep(1)
                        
                        # Try regular click first
                        easy_apply_button.click()
                        break
                        
                    except ElementClickInterceptedException:
                        print(f"Click failed, retrying... ({attempt + 1}/{max_click_attempts})")
                        if attempt < max_click_attempts - 1:
                            time.sleep(2)
                            # Try JavaScript click as fallback
                            try:
                                self.browser.execute_script("arguments[0].click();", easy_apply_button)
                                break
                            except:
                                continue
                        else:
                            print("❌ Failed to click Easy Apply button after all attempts")
                            return False
                            
                    except StaleElementReferenceException:
                        print(f"Element became stale, retrying... ({attempt + 1}/{max_click_attempts})")
                        if attempt < max_click_attempts - 1:
                            time.sleep(2)
                            # Try to find the button again
                            try:
                                easy_apply_button = self.browser.find_element(By.CSS_SELECTOR, easy_apply_selectors[0])
                            except:
                                continue
                        else:
                            print("❌ Failed to find Easy Apply button after all attempts")
                            return False
                            
                    except Exception as e:
                        print(f"Unexpected error clicking Easy Apply: {str(e)}")
                        if attempt < max_click_attempts - 1:
                            time.sleep(2)
                            continue
                        else:
                            return False
                
                # Wait for application form to load
                time.sleep(3)
                
            except Exception as e:
                print(f"❌ Error finding or clicking Easy Apply button: {str(e)}")
                return False
            
            # Now handle the application form
            try:
                # Find the job description area for analysis
                try:
                    job_description_area = self.browser.find_element(By.CLASS_NAME, "jobs-search__job-details--container")
                    print(f"{job_description_area}")

                    # Read and analyze job description using OCR
                    print("Reading job description with OCR...")
                    job_description_text = self.read_job_description_ocr(job_description_area)
                    
                    if job_description_text:
                        # Analyze the job description
                        analysis = self.analyze_job_description(job_description_text)
                        
                        print("\n" + "="*60)
                        print("🔍 JOB DESCRIPTION ANALYSIS")
                        print("="*60)
                        
                        # Basic job info
                        print(f"📋 Job Type: {analysis.get('job_type', 'unknown').replace('_', ' ').title()}")
                        print(f"📍 Location Type: {analysis.get('location_type', 'unknown').replace('_', ' ').title()}")
                        print(f"💼 Experience Level: {analysis.get('experience_level', 'unknown').title()}")
                        print(f"🏠 Remote Work: {'Yes' if analysis.get('remote_work', False) else 'No'}")
                        print(f"💰 Salary Mentioned: {'Yes' if analysis.get('salary_mentioned', False) else 'No'}")
                        
                        # Skills analysis
                        job_skills = analysis.get('job_skills', [])
                        if job_skills:
                            print(f"\n🎯 Required Skills ({len(job_skills)}):")
                            # Group skills by category for better display
                            programming_skills = ['python', 'javascript', 'java', 'c++', 'c#', 'php', 'ruby', 'go', 'rust', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'bash', 'powershell', 'typescript']
                            framework_skills = ['react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask', 'spring', 'laravel', 'asp.net', 'jquery', 'bootstrap', 'tailwind', 'material-ui', 'redux', 'mobx', 'graphql', 'rest api', 'api development']
                            database_skills = ['sql', 'mysql', 'postgresql', 'oracle', 'sql server', 'sqlite', 'mongodb', 'redis', 'cassandra', 'dynamodb', 'elasticsearch', 'neo4j', 'firebase']
                            cloud_devops_skills = ['aws', 'azure', 'google cloud', 'gcp', 'heroku', 'digitalocean', 'linode', 'kubernetes', 'docker', 'terraform', 'cloudformation', 'serverless', 'git', 'github', 'gitlab', 'jenkins', 'circleci', 'travis ci', 'gitlab ci', 'ansible', 'chef', 'puppet', 'vagrant', 'virtualbox', 'vmware']
                            methodology_skills = ['agile', 'scrum', 'kanban', 'waterfall', 'devops', 'ci/cd', 'tdd', 'bdd', 'lean', 'six sigma', 'prince2', 'pmp']
                            soft_skill_list = ['leadership', 'communication', 'teamwork', 'problem solving', 'analytical thinking', 'creativity', 'adaptability', 'time management', 'project management']
                            
                            skill_categories = {
                                'Programming': [s for s in job_skills if s.lower() in programming_skills],
                                'Frameworks': [s for s in job_skills if s.lower() in framework_skills],
                                'Databases': [s for s in job_skills if s.lower() in database_skills],
                                'Cloud/DevOps': [s for s in job_skills if s.lower() in cloud_devops_skills],
                                'Methodologies': [s for s in job_skills if s.lower() in methodology_skills],
                                'Soft Skills': [s for s in job_skills if s.lower() in soft_skill_list],
                                'Other': [s for s in job_skills if s.lower() not in programming_skills + framework_skills + database_skills + cloud_devops_skills + methodology_skills + soft_skill_list]
                            }
                            
                            for category, skills in skill_categories.items():
                                if skills:
                                    print(f"  {category}: {', '.join(skills[:8])}{'...' if len(skills) > 8 else ''}")
                        
                        # Tech stack
                        tech_stack = analysis.get('tech_stack', [])
                        if tech_stack:
                            print(f"\n🔧 Tech Stack: {', '.join(tech_stack[:10])}{'...' if len(tech_stack) > 10 else ''}")
                        
                        # Red flags
                        red_flags = analysis.get('red_flags', [])
                        if red_flags:
                            print(f"\n🚨 Red Flags:")
                            for flag in red_flags:
                                print(f"  ⚠️  {flag}")
                        
                        # Skill matching results
                        if 'skill_match' in analysis:
                            skill_match = analysis['skill_match']
                            print(f"\n🎯 SKILL MATCHING ANALYSIS")
                            print(f"   Overall Score: {skill_match['score']}/100")
                            print(f"   Match Percentage: {skill_match['match_percentage']}%")
                            
                            if skill_match['matched_skills']:
                                print(f"   ✅ Matched Skills: {', '.join(skill_match['matched_skills'][:6])}{'...' if len(skill_match['matched_skills']) > 6 else ''}")
                            
                            if skill_match['missing_skills']:
                                print(f"   ❌ Missing Skills: {', '.join(skill_match['missing_skills'][:6])}{'...' if len(skill_match['missing_skills']) > 6 else ''}")
                            
                            if skill_match['extra_skills']:
                                print(f"   🎁 Extra Skills: {', '.join(skill_match['extra_skills'][:6])}{'...' if len(skill_match['extra_skills']) > 6 else ''}")
                        
                        print("="*60)
                        
                        # Make decision based on analysis
                        should_apply = self.should_apply_to_job(analysis, job_description_text)
                        
                        if not should_apply:
                            print("❌ Job analysis suggests not to apply. Skipping this job.")
                            return False
                        else:
                            print("✅ Job analysis suggests this is a good fit. Proceeding with application.")
                    else:
                        print("⚠️  Could not read job description. Proceeding with caution.")
                        print("💡 To enable full job analysis, install Tesseract OCR:")
                        print("   Download from: https://github.com/UB-Mannheim/tesseract/wiki")
                        print("   Check 'Add to PATH' during installation and restart your IDE")
                    
                    self.scroll_slow(job_description_area, end=1600)
                    self.scroll_slow(job_description_area, end=1600, step=400, reverse=True)
                except Exception as e:
                    print(f"Error reading job description: {str(e)}")
                    # Continue with application even if OCR fails
                    pass
            except Exception as e:
                print(f"Error handling job application: {str(e)}")
                traceback.print_exc()
                return False
            
            # Now handle the application form
            button_text = ""
            submit_application_text = 'submit application'
            max_form_attempts = 5
            form_attempt = 0
            
            while submit_application_text not in button_text.lower() and form_attempt < max_form_attempts:
                try:
                    form_attempt += 1
                    print(f"Form attempt {form_attempt}/{max_form_attempts}")
                    
                    self.fill_up()
                    
                    # Try multiple selectors for the next button
                    next_button = None
                    button_selectors = [
                        "artdeco-button--primary",
                        "artdeco-button--2",
                        "artdeco-button",
                        "button[type='submit']",
                        "button[data-control-name='continue_unify']"
                    ]
                    
                    for selector in button_selectors:
                        try:
                            if selector.startswith("button["):
                                next_button = self.browser.find_element(By.CSS_SELECTOR, selector)
                            else:
                                next_button = self.browser.find_element(By.CLASS_NAME, selector)
                            if next_button and next_button.is_enabled():
                                break
                        except:
                            continue
                    
                    if not next_button:
                        print("Could not find next button, trying to refresh and retry...")
                        self.browser.refresh()
                        time.sleep(3)
                        continue
                    
                    button_text = next_button.text.lower()
                    print(f"Found button: {button_text}")
                    
                    if submit_application_text in button_text:
                        try:
                            self.unfollow()
                        except:
                            print("Failed to unfollow company.")
                    time.sleep(random.uniform(1.5, 2.5))
                    next_button.click()
                    time.sleep(random.uniform(3.0, 5.0))
                    
                    # Check for error messages
                    error_messages = [
                        'enter a valid',
                        'enter a decimal',
                        'Enter a whole number',
                        'Enter a whole number between 0 and 99',
                        'file is required',
                        'whole number',
                        'make a selection',
                        'select checkbox to proceed',
                        'saisissez un numéro',
                        '请输入whole编号',
                        '请输入decimal编号',
                        '长度超过 0.0',
                        'Numéro de téléphone',
                        'Introduce un número de whole entre',
                        'Inserisci un numero whole compreso',
                        'Preguntas adicionales',
                        'Insira um um número',
                        'Cuántos años',
                        'use the format',
                        'A file is required',
                        '请选择',
                        '请 选 择',
                        'Inserisci',
                        'wholenummer',
                        'Wpisz liczb',
                        'zakresu od',
                        'tussen'
                    ]
                    
                    if any(error in self.browser.page_source.lower() for error in error_messages):
                        raise Exception("Failed answering required questions or uploading required files.")
                        
                except Exception as e:
                    print(f"Error during application process: {str(e)}")
                    traceback.print_exc()
                    
                    # Try to close any open modals
                    try:
                        dismiss_buttons = self.browser.find_elements(By.CLASS_NAME, 'artdeco-modal__dismiss')
                        if dismiss_buttons:
                            dismiss_buttons[0].click()
                            time.sleep(random.uniform(2, 3))
                        
                        confirm_buttons = self.browser.find_elements(By.CLASS_NAME, 'artdeco-modal__confirm-dialog-btn')
                        if confirm_buttons:
                            confirm_buttons[0].click()
                            time.sleep(random.uniform(2, 3))
                    except Exception as close_error:
                        print(f"Could not close modal: {str(close_error)}")
                    
                    # If we've exhausted all attempts, raise the exception
                    if form_attempt >= max_form_attempts:
                        print(f"Exhausted {max_form_attempts} form attempts, giving up")
                        raise Exception("Failed to apply to job after multiple attempts!")
                    else:
                        print(f"Retrying form... (attempt {form_attempt + 1}/{max_form_attempts})")
                        continue
            
            # Close application confirmation
            closed_notification = False
            time.sleep(random.uniform(3, 5))
            try:
                self.browser.find_element(By.CLASS_NAME, 'artdeco-modal__dismiss').click()
                closed_notification = True
            except:
                pass
            try:
                self.browser.find_element(By.CLASS_NAME, 'artdeco-toast-item__dismiss').click()
                closed_notification = True
            except:
                pass
            try:
                self.browser.find_element(By.CSS_SELECTOR, 'button[data-control-name="save_application_btn"]').click()
                closed_notification = True
            except:
                pass
            
            time.sleep(random.uniform(3, 5))
            
            if closed_notification is False:
                print("⚠️  Could not close the applied confirmation window!")
            else:
                print("✅ Application confirmation closed successfully")
            
            return True
        except Exception as e:
            print(f"Unexpected error applying to job: {str(e)}")
            traceback.print_exc()
            return False

    def home_address(self, form):
        print("Trying to fill up home address fields")
        try:
            groups = form.find_elements(By.CLASS_NAME, 'jobs-easy-apply-form-section__grouping')
            if len(groups) > 0:
                for group in groups:
                    lb = group.find_element(By.TAG_NAME, 'label').text.lower()
                    input_field = group.find_element(By.TAG_NAME, 'input')
                    if 'street' in lb:
                        self.enter_text(input_field, self.personal_info['Street address'])
                    elif 'city' in lb:
                        self.enter_text(input_field, self.personal_info['City'])
                        time.sleep(3)
                        input_field.send_keys(Keys.DOWN)
                        input_field.send_keys(Keys.RETURN)
                    elif 'zip' in lb or 'zip / postal code' in lb or 'postal' in lb:
                        self.enter_text(input_field, self.personal_info['Zip'])
                    elif 'state' in lb or 'province' in lb:
                        self.enter_text(input_field, self.personal_info['State'])
                    else:
                        pass
        except:
            pass

    def get_answer(self, question):
        if self.checkboxes[question]:
            return 'yes'
        else:
            return 'no'

    def additional_questions(self, form):
        print("Trying to fill up additional questions")

        questions = form.find_elements(By.CLASS_NAME, 'fb-dash-form-element')
        for question in questions:
            try:
                # Radio check
                radio_fieldset = question.find_element(By.TAG_NAME, 'fieldset')
                question_span = radio_fieldset.find_element(By.CLASS_NAME, 'fb-dash-form-element__label').find_elements(By.TAG_NAME, 'span')[0]
                radio_text = question_span.text.lower()
                print(f"Radio question text: {radio_text}")  # TODO: Put logging behind debug flag

                radio_labels = radio_fieldset.find_elements(By.TAG_NAME, 'label')
                radio_options = [text.text.lower() for text in radio_labels]
                print(f"radio options: {radio_options}")  # TODO: Put logging behind debug flag
                if len(radio_options) == 0:
                    raise Exception("No radio options found in question")

                answer = "yes"

                if 'driver\'s licence' in radio_text or 'driver\'s license' in radio_text:
                    answer = self.get_answer('driversLicence')

                elif any(keyword in radio_text.lower() for keyword in
                         [
                             'Aboriginal', 'native', 'indigenous', 'tribe', 'first nations',
                             'native american', 'native hawaiian', 'inuit', 'metis', 'maori',
                             'aborigine', 'ancestral', 'native peoples', 'original people',
                             'first people', 'gender', 'race', 'disability', 'latino', 'torres',
                             'do you identify'
                         ]):
                    negative_keywords = ['prefer', 'decline', 'don\'t', 'specified', 'none', 'no']
                    answer = next((option for option in radio_options if
                                   any(neg_keyword in option.lower() for neg_keyword in negative_keywords)), None)

                elif 'assessment' in radio_text:
                    answer = self.get_answer("assessment")

                elif 'clearance' in radio_text:
                    answer = self.get_answer("securityClearance")

                elif 'north korea' in radio_text:
                    answer = 'no'

                elif 'convicted' in radio_text:
                    answer = 'no'

                elif 'previously employ' in radio_text or 'previous employ' in radio_text:
                    answer = 'no'

                elif 'authorized' in radio_text or 'authorised' in radio_text or 'legally' in radio_text:
                    answer = self.get_answer('legallyAuthorized')

                elif any(keyword in radio_text.lower() for keyword in
                         ['certified', 'certificate', 'cpa', 'chartered accountant', 'qualification']):
                    answer = self.get_answer('certifiedProfessional')

                elif 'urgent' in radio_text:
                    answer = self.get_answer('urgentFill')

                elif 'commut' in radio_text or 'on-site' in radio_text or 'hybrid' in radio_text or 'onsite' in radio_text:
                    answer = self.get_answer('commute')

                elif 'remote' in radio_text:
                    answer = self.get_answer('remote')

                elif 'background check' in radio_text:
                    answer = self.get_answer('backgroundCheck')

                elif 'drug test' in radio_text:
                    answer = self.get_answer('drugTest')

                elif 'currently living' in radio_text or 'currently reside' in radio_text or 'right to live' in radio_text:
                    answer = self.get_answer('residency')

                elif 'level of education' in radio_text:
                    for degree in self.checkboxes['degreeCompleted']:
                        if degree.lower() in radio_text:
                            answer = "yes"
                            break

                elif 'experience' in radio_text:
                    for experience in self.experience:
                        if experience.lower() in radio_text:
                            answer = "yes"
                            break

                elif 'data retention' in radio_text:
                    answer = 'no'

                elif 'sponsor' in radio_text:
                    answer = self.get_answer('requireVisa')
                else:
                    answer = radio_options[len(radio_options) - 1]
                    self.record_unprepared_question("radio", radio_text)

                print(f"Choosing answer: {answer}")  # TODO: Put logging behind debug flag
                i = 0
                to_select = None
                for radio in radio_labels:
                    if answer in radio.text.lower():
                        to_select = radio_labels[i]
                    i += 1

                if to_select is None:
                    to_select = radio_labels[len(radio_labels) - 1]

                to_select.click()

                if radio_labels:
                    continue
            except:
                print("An exception occurred while filling up radio field")  # TODO: Put logging behind debug flag

            # Questions check
            try:
                question_text = question.find_element(By.TAG_NAME, 'label').text.lower()
                print( question_text )  # TODO: Put logging behind debug flag

                txt_field_visible = False
                try:
                    txt_field = question.find_element(By.TAG_NAME, 'input')
                    txt_field_visible = True
                except:
                    try:
                        txt_field = question.find_element(By.TAG_NAME, 'textarea')  # TODO: Test textarea
                        txt_field_visible = True
                    except:
                        raise Exception("Could not find textarea or input tag for question")

                text_field_type = txt_field.get_attribute('type').lower()
                if 'numeric' in text_field_type:  # TODO: test numeric type
                    text_field_type = 'numeric'
                elif 'text' in text_field_type:
                    text_field_type = 'text'
                else:
                    raise Exception("Could not determine input type of input field!")

                to_enter = ''
                if 'experience' in question_text or 'how many years in' in question_text:
                    no_of_years = None
                    for experience in self.experience:
                        if experience.lower() in question_text:
                            no_of_years = int(self.experience[experience])
                            break
                    if no_of_years is None:
                        self.record_unprepared_question(text_field_type, question_text)
                        no_of_years = int(self.experience_default)
                    to_enter = no_of_years

                elif 'grade point average' in question_text:
                    to_enter = self.university_gpa

                elif 'first name' in question_text:
                    to_enter = self.personal_info['First Name']

                elif 'last name' in question_text:
                    to_enter = self.personal_info['Last Name']

                elif 'name' in question_text:
                    to_enter = self.personal_info['First Name'] + " " + self.personal_info['Last Name']

                elif 'pronouns' in question_text:
                    to_enter = self.personal_info['Pronouns']

                elif 'phone' in question_text:
                    to_enter = self.personal_info['Mobile Phone Number']

                elif 'linkedin' in question_text:
                    to_enter = self.personal_info['Linkedin']

                elif 'message to hiring' in question_text or 'cover letter' in question_text:
                    to_enter = self.personal_info['MessageToManager']

                elif 'website' in question_text or 'github' in question_text or 'portfolio' in question_text:
                    to_enter = self.personal_info['Website']

                elif 'notice' in question_text or 'weeks' in question_text:
                    if text_field_type == 'numeric':
                        to_enter = int(self.notice_period)
                    else:
                        to_enter = str(self.notice_period)

                elif 'salary' in question_text or 'expectation' in question_text or 'compensation' in question_text or 'CTC' in question_text:
                    if text_field_type == 'numeric':
                        to_enter = int(self.salary_minimum)
                    else:
                        to_enter = float(self.salary_minimum)
                    self.record_unprepared_question(text_field_type, question_text)

                if text_field_type == 'numeric':
                    if not isinstance(to_enter, (int, float)):
                        to_enter = 0
                elif to_enter == '':
                    to_enter = " ‏‏‎ "

                self.enter_text(txt_field, to_enter)
                continue
            except:
                print("An exception occurred while filling up text field")  # TODO: Put logging behind debug flag

            # Date Check
            try:
                date_picker = question.find_element(By.CLASS_NAME, 'artdeco-datepicker__input ')
                date_picker.clear()
                date_picker.send_keys(date.today().strftime("%m/%d/%y"))
                time.sleep(3)
                date_picker.send_keys(Keys.RETURN)
                time.sleep(2)
                continue
            except:
                print("An exception occurred while filling up date picker field")  # TODO: Put logging behind debug flag

            # Dropdown check
            try:
                question_text = question.find_element(By.TAG_NAME, 'label').text.lower()
                print(f"Dropdown question text: {question_text}")  # TODO: Put logging behind debug flag
                dropdown_field = question.find_element(By.TAG_NAME, 'select')

                select = Select(dropdown_field)
                options = [options.text for options in select.options]
                print(f"Dropdown options: {options}")  # TODO: Put logging behind debug flag

                if 'proficiency' in question_text:
                    proficiency = "None"
                    for language in self.languages:
                        if language.lower() in question_text:
                            proficiency = self.languages[language]
                            break
                    self.select_dropdown(dropdown_field, proficiency)

                elif 'clearance' in question_text:
                    answer = self.get_answer('securityClearance')

                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            choice = option
                        else:
                            if 'no' in option.lower():
                                choice = option
                    if choice == "":
                        self.record_unprepared_question(text_field_type, question_text)
                    self.select_dropdown(dropdown_field, choice)

                elif 'assessment' in question_text:
                    answer = self.get_answer('assessment')
                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            choice = option
                        else:
                            if 'no' in option.lower():
                                choice = option
                    # if choice == "":
                    #    choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'commut' in question_text or 'on-site' in question_text or 'hybrid' in question_text or 'onsite' in question_text:
                    answer = self.get_answer('commute')

                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            choice = option
                        else:
                            if 'no' in option.lower():
                                choice = option
                    # if choice == "":
                    #    choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'country code' in question_text:
                    self.select_dropdown(dropdown_field, self.personal_info['Phone Country Code'])

                elif 'north korea' in question_text:
                    choice = ""
                    for option in options:
                        if 'no' in option.lower():
                            choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'previously employed' in question_text or 'previous employment' in question_text:
                    choice = ""
                    for option in options:
                        if 'no' in option.lower():
                            choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'sponsor' in question_text:
                    answer = self.get_answer('requireVisa')
                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            choice = option
                        else:
                            if 'no' in option.lower():
                                choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'above 18' in question_text.lower():  # Check for "above 18" in the question text
                    choice = ""
                    for option in options:
                        if 'yes' in option.lower():  # Select 'yes' option
                            choice = option
                    if choice == "":
                        choice = options[0]  # Default to the first option if 'yes' is not found
                    self.select_dropdown(dropdown_field, choice)

                elif 'currently living' in question_text or 'currently reside' in question_text:
                    answer = self.get_answer('residency')
                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            choice = option
                        else:
                            if 'no' in option.lower():
                                choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'authorized' in question_text or 'authorised' in question_text:
                    answer = self.get_answer('legallyAuthorized')
                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            # find some common words
                            choice = option
                        else:
                            if 'no' in option.lower():
                                choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'citizenship' in question_text:
                    answer = self.get_answer('legallyAuthorized')
                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            if 'no' in option.lower():
                                choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                elif 'clearance' in question_text:
                    answer = self.get_answer('clearance')
                    choice = ""
                    for option in options:
                        if answer == 'yes':
                            choice = option
                        else:
                            if 'no' in option.lower():
                                choice = option
                    if choice == "":
                        choice = options[len(options) - 1]

                    self.select_dropdown(dropdown_field, choice)

                elif any(keyword in question_text.lower() for keyword in
                         [
                             'aboriginal', 'native', 'indigenous', 'tribe', 'first nations',
                             'native american', 'native hawaiian', 'inuit', 'metis', 'maori',
                             'aborigine', 'ancestral', 'native peoples', 'original people',
                             'first people', 'gender', 'race', 'disability', 'latino'
                         ]):
                    negative_keywords = ['prefer', 'decline', 'don\'t', 'specified', 'none']

                    choice = ""
                    choice = next((option for options in option.lower() if
                               any(neg_keyword in option.lower() for neg_keyword in negative_keywords)), None)

                    self.select_dropdown(dropdown_field, choice)

                elif 'email' in question_text:
                    continue  # assume email address is filled in properly by default

                elif 'experience' in question_text or 'understanding' in question_text or 'familiar' in question_text or 'comfortable' in question_text or 'able to' in question_text:
                    answer = 'no'
                    for experience in self.experience:
                        if experience.lower() in question_text and self.experience[experience] > 0:
                            answer = 'yes'
                            break
                    if answer == 'no':
                        # record unlisted experience as unprepared questions
                        self.record_unprepared_question("dropdown", question_text)

                    choice = ""
                    for option in options:
                        if answer in option.lower():
                            choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)

                else:
                    choice = ""
                    for option in options:
                        if 'yes' in option.lower():
                            choice = option
                    if choice == "":
                        choice = options[len(options) - 1]
                    self.select_dropdown(dropdown_field, choice)
                    self.record_unprepared_question("dropdown", question_text)
                continue
            except:
                print("An exception occurred while filling up dropdown field")  # TODO: Put logging behind debug flag

            # Checkbox check for agreeing to terms and service
            try:
                clickable_checkbox = question.find_element(By.TAG_NAME, 'label')
                clickable_checkbox.click()
            except:
                print("An exception occurred while filling up checkbox field")  # TODO: Put logging behind debug flag

    def unfollow(self):
        try:
            follow_checkbox = self.browser.find_element(By.XPATH,
                                                        "//label[contains(.,\'to stay up to date with their page.\')]").click()
            follow_checkbox.click()
        except:
            pass

    def send_resume(self):
        """
        Automatically upload resume and cover letter when applying to jobs
        """
        print("📄 Attempting to upload resume and cover letter...")
        
        try:
            # Check if resume path exists and is accessible
            if not hasattr(self, 'resume_dir') or not self.resume_dir:
                print("❌ No resume path configured in config.yaml")
                return False
            
            # Verify resume file exists
            import os
            if not os.path.exists(self.resume_dir):
                print(f"❌ Resume file not found at: {self.resume_dir}")
                print("💡 Please check the resume path in config.yaml")
                return False
            
            print(f"✅ Resume file found: {self.resume_dir}")
            
            # Try multiple selectors for file upload elements
            file_upload_selectors = [
                "input[name='file']",
                "input[type='file']",
                "input[accept*='.pdf']",
                "input[accept*='.doc']",
                "input[accept*='.docx']",
                "input[accept*='.txt']",
                "input[class*='file']",
                "input[class*='upload']"
            ]
            
            upload_elements_found = False
            
            for selector in file_upload_selectors:
                try:
                    file_inputs = self.browser.find_elements(By.CSS_SELECTOR, selector)
                    if file_inputs:
                        print(f"🔍 Found {len(file_inputs)} file upload elements using selector: {selector}")
                        
                        for upload_input in file_inputs:
                            try:
                                # Try to determine what type of file this input is for
                                upload_context = self.get_upload_context(upload_input)
                                print(f"📋 Upload context: {upload_context}")
                                
                                if 'resume' in upload_context.lower() or 'cv' in upload_context.lower():
                                    print(f"📤 Uploading resume to: {upload_context}")
                                    upload_input.send_keys(self.resume_dir)
                                    print("✅ Resume uploaded successfully!")
                                    upload_elements_found = True
                                    
                                elif 'cover' in upload_context.lower() and self.cover_letter_dir:
                                    if os.path.exists(self.cover_letter_dir):
                                        print(f"📤 Uploading cover letter to: {upload_context}")
                                        upload_input.send_keys(self.cover_letter_dir)
                                        print("✅ Cover letter uploaded successfully!")
                                        upload_elements_found = True
                                    else:
                                        print(f"⚠️  Cover letter file not found: {self.cover_letter_dir}")
                                        
                                elif 'required' in upload_context.lower():
                                    # If it's marked as required but we don't know what type, upload resume
                                    print(f"📤 Uploading resume to required field: {upload_context}")
                                    upload_input.send_keys(self.resume_dir)
                                    print("✅ Resume uploaded to required field!")
                                    upload_elements_found = True
                                    
                                else:
                                    print(f"⚠️  Unknown upload type: {upload_context}")
                                    
                            except Exception as upload_error:
                                print(f"❌ Error uploading to {upload_context}: {str(upload_error)}")
                                continue
                        
                        if upload_elements_found:
                            break
                            
                except Exception as selector_error:
                    print(f"⚠️  Error with selector {selector}: {str(selector_error)}")
                    continue
            
            if not upload_elements_found:
                print("⚠️  No file upload elements found or no successful uploads")
                print("💡 This might be a job that doesn't require resume upload")
                return False
            
            # Wait a moment for uploads to complete
            time.sleep(2)
            
            # Verify uploads were successful by checking for success indicators
            try:
                success_indicators = [
                    "//span[contains(text(), 'uploaded')]",
                    "//span[contains(text(), 'successful')]",
                    "//div[contains(@class, 'success')]",
                    "//div[contains(@class, 'uploaded')]"
                ]
                
                for indicator in success_indicators:
                    try:
                        success_element = self.browser.find_element(By.XPATH, indicator)
                        if success_element.is_displayed():
                            print("✅ Upload verification successful!")
                            break
                    except:
                        continue
                        
            except Exception as verify_error:
                print(f"⚠️  Could not verify upload success: {str(verify_error)}")
            
            return upload_elements_found
            
        except Exception as e:
            print(f"❌ Error in resume upload process: {str(e)}")
            import traceback
            traceback.print_exc()
            return False
    
    def get_upload_context(self, upload_input):
        """
        Determine what type of file upload this input is for
        """
        try:
            # Try to find nearby text that describes what this upload is for
            context_selectors = [
                ".//preceding-sibling::*[1]",
                ".//following-sibling::*[1]",
                ".//ancestor::div[contains(@class, 'form')]//label",
                ".//ancestor::div[contains(@class, 'field')]//label",
                ".//ancestor::div[contains(@class, 'upload')]//label",
                ".//ancestor::div[contains(@class, 'resume')]//label",
                ".//ancestor::div[contains(@class, 'cover')]//label"
            ]
            
            for selector in context_selectors:
                try:
                    context_element = upload_input.find_element(By.XPATH, selector)
                    if context_element and context_element.text.strip():
                        return context_element.text.strip()
                except:
                    continue
            
            # Try to get context from parent elements
            try:
                parent = upload_input.find_element(By.XPATH, "..")
                if parent.text.strip():
                    return parent.text.strip()
            except:
                pass
            
            # Try to get context from aria-label or placeholder
            try:
                aria_label = upload_input.get_attribute('aria-label')
                if aria_label:
                    return aria_label
            except:
                pass
            
            try:
                placeholder = upload_input.get_attribute('placeholder')
                if placeholder:
                    return placeholder
            except:
                pass
            
            # Default context
            return "file upload"
            
        except Exception as e:
            return "file upload"

    def enter_text(self, element, text):
        element.clear()
        element.send_keys(text)

    def select_dropdown(self, element, text):
        select = Select(element)
        select.select_by_visible_text(text)

    # Radio Select
    def radio_select(self, element, label_text, clickLast=False):
        label = element.find_element(By.TAG_NAME, 'label')
        if label_text in label.text.lower() or clickLast == True:
            label.click()

    # Contact info fill-up
    def contact_info(self, form):
        print("Trying to fill up contact info fields")
        frm_el = form.find_elements(By.TAG_NAME, 'label')
        if len(frm_el) > 0:
            for el in frm_el:
                text = el.text.lower()
                if 'email address' in text:
                    continue
                elif 'phone number' in text:
                    try:
                        country_code_picker = el.find_element(By.XPATH,
                                                              '//select[contains(@id,"phoneNumber")][contains(@id,"country")]')
                        self.select_dropdown(country_code_picker, self.personal_info['Phone Country Code'])
                    except Exception as e:
                        print("Country code " + self.personal_info[
                            'Phone Country Code'] + " not found. Please make sure it is same as in LinkedIn.")
                        print(e)
                    try:
                        phone_number_field = el.find_element(By.XPATH,
                                                             '//input[contains(@id,"phoneNumber")][contains(@id,"nationalNumber")]')
                        self.enter_text(phone_number_field, self.personal_info['Mobile Phone Number'])
                    except Exception as e:
                        print("Could not enter phone number:")
                        print(e)

    def fill_up(self):
        try:
            easy_apply_modal_content = self.browser.find_element(By.CLASS_NAME, "jobs-easy-apply-modal__content")
            form = easy_apply_modal_content.find_element(By.TAG_NAME, 'form')
            try:
                label = form.find_element(By.TAG_NAME, 'h3').text.lower()
                print(f"📝 Filling form section: {label}")
                
                if 'home address' in label:
                    self.home_address(form)
                elif 'contact info' in label:
                    self.contact_info(form)
                elif 'resume' in label or 'cv' in label:
                    print("📄 Resume/CV section detected - attempting automatic upload...")
                    resume_upload_success = self.send_resume()
                    if resume_upload_success:
                        print("✅ Resume section completed successfully")
                    else:
                        print("⚠️  Resume upload may have failed - continuing anyway")
                else:
                    self.additional_questions(form)
                    
                print(f"✅ Successfully filled {label} section")
                
            except Exception as e:
                print(f"❌ An exception occurred while filling up the form: {str(e)}")
                traceback.print_exc()
                # Try to continue anyway
                pass
        except Exception as e:
            print(f"❌ An exception occurred while searching for form in modal: {str(e)}")
            # This might be a different type of application form, try to continue
            # Try alternative form selectors
            try:
                alternative_forms = self.browser.find_elements(By.TAG_NAME, 'form')
                if alternative_forms:
                    print(f"🔍 Found {len(alternative_forms)} alternative forms, trying to fill them")
                    for alt_form in alternative_forms:
                        try:
                            self.additional_questions(alt_form)
                        except:
                            continue
            except:
                pass

    def write_to_file(self, company, job_title, link, location, search_location):
        to_write = [company, job_title, link, location, search_location, datetime.now()]
        file_path = self.file_name + ".csv"
        print(f'updated {file_path}.')

        with open(file_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(to_write)

    def record_unprepared_question(self, answer_type, question_text):
        to_write = [answer_type, question_text]
        file_path = self.unprepared_questions_file_name + ".csv"

        try:
            with open(file_path, 'a') as f:
                writer = csv.writer(f)
                writer.writerow(to_write)
                print(f'Updated {file_path} with {to_write}.')
        except:
            print(
                "Special characters in questions are not allowed. Failed to update unprepared questions log.")
            print(question_text)

    def scroll_slow(self, scrollable_element, start=0, end=3600, step=100, reverse=False):
        if reverse:
            start, end = end, start
            step = -step

        for i in range(start, end, step):
            self.browser.execute_script("arguments[0].scrollTo(0, {})".format(i), scrollable_element)
            time.sleep(random.uniform(1.0, 2.6))

    def avoid_lock(self):
        if self.disable_lock:
            return

        pyautogui.keyDown('ctrl')
        pyautogui.press('esc')
        pyautogui.keyUp('ctrl')
        time.sleep(1.0)
        pyautogui.press('esc')

    def get_base_search_url(self, parameters):
        remote_url = ""
        lessthanTenApplicants_url = ""

        if parameters.get('remote'):
            remote_url = "&f_WT=2"
        else:
            remote_url = ""
            # TO DO: Others &f_WT= options { WT=1 onsite, WT=2 remote, WT=3 hybrid, f_WT=1%2C2%2C3 }

        if parameters['lessthanTenApplicants']:
            lessthanTenApplicants_url = "&f_EA=true"

        level = 1
        experience_level = parameters.get('experienceLevel', [])
        experience_url = "f_E="
        for key in experience_level.keys():
            if experience_level[key]:
                experience_url += "%2C" + str(level)
            level += 1

        distance_url = "?distance=" + str(parameters['distance'])

        job_types_url = "f_JT="
        job_types = parameters.get('jobTypes', [])
        # job_types = parameters.get('experienceLevel', [])
        for key in job_types:
            if job_types[key]:
                job_types_url += "%2C" + key[0].upper()

        date_url = ""
        dates = {"all time": "", "month": "&f_TPR=r2592000", "week": "&f_TPR=r604800", "24 hours": "&f_TPR=r86400"}
        date_table = parameters.get('date', [])
        for key in date_table.keys():
            if date_table[key]:
                date_url = dates[key]
                break

        easy_apply_url = "&f_AL=true"

        extra_search_terms = [distance_url, remote_url, lessthanTenApplicants_url, job_types_url, experience_url]
        extra_search_terms_str = '&'.join(
            term for term in extra_search_terms if len(term) > 0) + easy_apply_url + date_url

        return extra_search_terms_str

    def next_job_page(self, position, location, job_page):
        self.browser.get("https://www.linkedin.com/jobs/search/" + self.base_search_url +
                         "&keywords=" + position + location + "&start=" + str(job_page * 25))

        self.avoid_lock()
