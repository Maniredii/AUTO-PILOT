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
                        "jobs-box__html-content"
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
            
            # Take a screenshot of the job description area
            try:
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
                        # Remove extra whitespace and normalize
                        text = ' '.join(text.split())
                        print(f"Successfully extracted {len(text)} characters from job description")
                        return text
                    else:
                        print("No text extracted from job description image")
                        return ""
                        
                except Exception as ocr_error:
                    print(f"OCR error: {str(ocr_error)}")
                    return ""
                    
            except Exception as screenshot_error:
                print(f"Screenshot error: {str(screenshot_error)}")
                return ""
                
        except Exception as e:
            print(f"Error in OCR job description reading: {str(e)}")
            return ""
    
    def analyze_job_description(self, job_text):
        """
        Analyze the job description text for key information
        Returns a dictionary with analysis results
        """
        if not job_text:
            return {}
        
        analysis = {
            'has_required_skills': False,
            'has_preferred_skills': False,
            'experience_level': 'unknown',
            'remote_work': False,
            'salary_mentioned': False,
            'tech_stack': [],
            'red_flags': []
        }
        
        job_text_lower = job_text.lower()
        
        # Check for required skills
        required_keywords = ['required', 'must have', 'essential', 'mandatory', 'prerequisites']
        if any(keyword in job_text_lower for keyword in required_keywords):
            analysis['has_required_skills'] = True
        
        # Check for preferred skills
        preferred_keywords = ['preferred', 'nice to have', 'bonus', 'plus', 'advantage']
        if any(keyword in job_text_lower for keyword in preferred_keywords):
            analysis['has_preferred_skills'] = True
        
        # Check experience level
        if 'senior' in job_text_lower or 'lead' in job_text_lower or 'principal' in job_text_lower:
            analysis['experience_level'] = 'senior'
        elif 'junior' in job_text_lower or 'entry' in job_text_lower or 'graduate' in job_text_lower:
            analysis['experience_level'] = 'junior'
        elif 'mid' in job_text_lower or 'intermediate' in job_text_lower:
            analysis['experience_level'] = 'mid'
        
        # Check for remote work
        remote_keywords = ['remote', 'work from home', 'telecommute', 'distributed']
        if any(keyword in job_text_lower for keyword in remote_keywords):
            analysis['remote_work'] = True
        
        # Check for salary information
        salary_keywords = ['salary', 'compensation', 'pay', '$', 'usd', 'annual']
        if any(keyword in job_text_lower for keyword in salary_keywords):
            analysis['salary_mentioned'] = True
        
        # Extract tech stack
        tech_keywords = [
            'python', 'java', 'javascript', 'react', 'angular', 'vue', 'node.js',
            'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'sql', 'mongodb',
            'machine learning', 'ai', 'data science', 'devops', 'agile'
        ]
        
        for tech in tech_keywords:
            if tech in job_text_lower:
                analysis['tech_stack'].append(tech)
        
        # Check for red flags
        red_flag_keywords = [
            'unpaid', 'volunteer', 'commission only', 'no benefits',
            'overtime required', 'weekend work', 'on-call', '24/7'
        ]
        
        for flag in red_flag_keywords:
            if flag in job_text_lower:
                analysis['red_flags'].append(flag)
        
        return analysis

    def should_apply_to_job(self, analysis, job_text):
        """
        Make intelligent decision about whether to apply to a job
        Returns True if should apply, False if should skip
        """
        if not analysis:
            return True  # If we can't analyze, proceed with caution
        
        # Check for major red flags
        if analysis.get('red_flags'):
            red_flags = analysis['red_flags']
            # Skip jobs with certain red flags
            critical_red_flags = ['unpaid', 'volunteer', 'commission only', 'no benefits']
            if any(flag in red_flags for flag in critical_red_flags):
                print(f"❌ Critical red flag detected: {[f for f in red_flags if f in critical_red_flags]}")
                return False
        
        # Check experience level compatibility
        user_experience = getattr(self, 'experience_level', 'mid')  # Default to mid-level
        job_experience = analysis.get('experience_level', 'unknown')
        
        if job_experience != 'unknown':
            if user_experience == 'junior' and job_experience == 'senior':
                print("❌ Job requires senior level, but user is junior")
                return False
            elif user_experience == 'senior' and job_experience == 'junior':
                print("⚠️  Job is junior level, but user is senior - might be overqualified")
                # Don't skip, but note it
        
        # Check for required skills match
        if analysis.get('has_required_skills'):
            # If job has required skills section, check if user has any of the common ones
            user_skills = getattr(self, 'user_skills', [])
            if user_skills:
                job_text_lower = job_text.lower()
                skill_match = any(skill.lower() in job_text_lower for skill in user_skills)
                if not skill_match:
                    print("❌ No skill match found in required skills")
                    return False
        
        # Check for remote work preference
        user_prefers_remote = getattr(self, 'prefer_remote', False)
        if user_prefers_remote and not analysis.get('remote_work'):
            print("⚠️  User prefers remote work, but job is not remote")
            # Don't skip, but note it
        
        # Check tech stack compatibility
        user_tech_stack = getattr(self, 'user_tech_stack', [])
        job_tech_stack = analysis.get('tech_stack', [])
        
        if user_tech_stack and job_tech_stack:
            tech_overlap = set(user_tech_stack) & set(job_tech_stack)
            if tech_overlap:
                print(f"✅ Tech stack overlap: {', '.join(tech_overlap)}")
            else:
                print("⚠️  No tech stack overlap found")
                # Don't skip, but note it
        
        # Overall decision
        # If we have red flags, skip
        if analysis.get('red_flags'):
            return False
        
        # If we have good skill matches, apply
        if analysis.get('has_required_skills') and user_skills:
            return True
        
        # If no major issues, proceed
        print("✅ Job analysis passed. Proceeding with application.")
        return True

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
                            done_applying = self.apply_to_job()
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

    def apply_to_job(self):
        easy_apply_button = None

        try:
            easy_apply_button = self.browser.find_element(By.CLASS_NAME, 'jobs-apply-button')
        except Exception as e:
            print(f"No Easy Apply button found: {str(e)}")
            return False

        try:
            job_description_area = self.browser.find_element(By.CLASS_NAME, "jobs-search__job-details--container")
            print(f"{job_description_area}")
            
            # Read and analyze job description using OCR
            print("Reading job description with OCR...")
            job_description_text = self.read_job_description_ocr(job_description_area)
            
            if job_description_text:
                # Analyze the job description
                analysis = self.analyze_job_description(job_description_text)
                
                print("Job Description Analysis:")
                print(f"  Experience Level: {analysis.get('experience_level', 'unknown')}")
                print(f"  Remote Work: {analysis.get('remote_work', False)}")
                print(f"  Salary Mentioned: {analysis.get('salary_mentioned', False)}")
                print(f"  Tech Stack: {', '.join(analysis.get('tech_stack', []))}")
                
                if analysis.get('red_flags'):
                    print(f"  ⚠️  Red Flags: {', '.join(analysis.get('red_flags', []))}")
                
                # Make decision based on analysis
                should_apply = self.should_apply_to_job(analysis, job_description_text)
                
                if not should_apply:
                    print("❌ Job analysis suggests not to apply. Skipping this job.")
                    return False
                else:
                    print("✅ Job analysis suggests this is a good fit. Proceeding with application.")
            else:
                print("⚠️  Could not read job description with OCR. Proceeding with caution.")
            
            self.scroll_slow(job_description_area, end=1600)
            self.scroll_slow(job_description_area, end=1600, step=400, reverse=True)
        except Exception as e:
            print(f"Error reading job description: {str(e)}")
            # Continue with application even if OCR fails
            pass

        print("Starting the job application...")
        
        # Try to click with retry logic
        max_click_retries = 3
        for click_retry in range(max_click_retries):
            try:
                easy_apply_button.click()
                break
            except Exception as click_error:
                if "element click intercepted" in str(click_error).lower() or "stale element" in str(click_error).lower():
                    if click_retry < max_click_retries - 1:
                        print(f"Click failed, retrying... ({click_retry + 1}/{max_click_retries})")
                        time.sleep(2)
                        # Refresh the button element
                        try:
                            easy_apply_button = self.browser.find_element(By.CLASS_NAME, 'jobs-apply-button')
                        except:
                            pass
                        continue
                    else:
                        # Use JavaScript as last resort
                        self.browser.execute_script("arguments[0].click();", easy_apply_button)
                        break
                else:
                    raise click_error

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

                # Newer error handling
                error_messages = [
                    'enter a valid',
                    'enter a decimal',
                    'Enter a whole number'
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
                    'Cuántos años'
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
            raise Exception("Could not close the applied confirmation window!")

        return True

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
        print("Trying to send resume")
        try:
            file_upload_elements = (By.CSS_SELECTOR, "input[name='file']")
            if len(self.browser.find_elements(file_upload_elements[0], file_upload_elements[1])) > 0:
                input_buttons = self.browser.find_elements(file_upload_elements[0], file_upload_elements[1])
                if len(input_buttons) == 0:
                    raise Exception("No input elements found in element")
                for upload_button in input_buttons:
                    upload_type = upload_button.find_element(By.XPATH, "..").find_element(By.XPATH,
                                                                                          "preceding-sibling::*")
                    if 'resume' in upload_type.text.lower():
                        upload_button.send_keys(self.resume_dir)
                    elif 'cover' in upload_type.text.lower():
                        if self.cover_letter_dir != '':
                            upload_button.send_keys(self.cover_letter_dir)
                        elif 'required' in upload_type.text.lower():
                            upload_button.send_keys(self.resume_dir)
        except:
            print("Failed to upload resume or cover letter!")
            pass

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
                print(f"Filling form section: {label}")
                
                if 'home address' in label:
                    self.home_address(form)
                elif 'contact info' in label:
                    self.contact_info(form)
                elif 'resume' in label:
                    self.send_resume()
                else:
                    self.additional_questions(form)
                    
                print(f"Successfully filled {label} section")
                
            except Exception as e:
                print(f"An exception occurred while filling up the form: {str(e)}")
                traceback.print_exc()
                # Try to continue anyway
                pass
        except Exception as e:
            print(f"An exception occurred while searching for form in modal: {str(e)}")
            # This might be a different type of application form, try to continue
            # Try alternative form selectors
            try:
                alternative_forms = self.browser.find_elements(By.TAG_NAME, 'form')
                if alternative_forms:
                    print(f"Found {len(alternative_forms)} alternative forms, trying to fill them")
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
