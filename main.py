import json
import os
import random
import time
import traceback
from datetime import datetime, timedelta

import yaml
from validate_email import validate_email

from protected_linkedin_bot import ProtectedLinkedInEasyApply


def load_hibernation_config() -> dict:
    """Load anti-ban configuration with hibernation settings."""
    try:
        with open('anti_ban_config.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("anti_ban_config.json not found. Please ensure the configuration file is present.")
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in anti_ban_config.json: {exc}")


def validate_yaml():
    with open("config.yaml", 'r', encoding='utf-8') as stream:
        try:
            parameters = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            raise exc

    mandatory_params = ['email',
                        'password',
                        'disableAntiLock',
                        'remote',
                        'lessthanTenApplicants',
                        'experienceLevel',
                        'jobTypes',
                        'date',
                        'positions',
                        'locations',
                        'residentStatus',
                        'distance',
                        'outputFileDirectory',
                        'checkboxes',
                        'universityGpa',
                        'languages',
                        'experience',
                        'personalInfo',
                        'eeo',
                        'uploads']

    for mandatory_param in mandatory_params:
        if mandatory_param not in parameters:
            raise Exception(mandatory_param + ' is not defined in the config.yaml file!')

    assert validate_email(parameters['email'])
    assert len(str(parameters['password'])) > 0
    assert isinstance(parameters['disableAntiLock'], bool)
    assert isinstance(parameters['remote'], bool)
    assert isinstance(parameters['lessthanTenApplicants'], bool)
    assert isinstance(parameters['residentStatus'], bool)
    assert len(parameters['experienceLevel']) > 0
    experience_level = parameters.get('experienceLevel', [])
    at_least_one_experience = False

    for key in experience_level.keys():
        if experience_level[key]:
            at_least_one_experience = True
    assert at_least_one_experience

    assert len(parameters['jobTypes']) > 0
    job_types = parameters.get('jobTypes', [])
    at_least_one_job_type = False
    for key in job_types.keys():
        if job_types[key]:
            at_least_one_job_type = True

    assert at_least_one_job_type
    assert len(parameters['date']) > 0
    date = parameters.get('date', [])
    at_least_one_date = False

    for key in date.keys():
        if date[key]:
            at_least_one_date = True
    assert at_least_one_date

    approved_distances = {0, 5, 10, 25, 50, 100}
    assert parameters['distance'] in approved_distances
    assert len(parameters['positions']) > 0
    assert len(parameters['locations']) > 0
    assert len(parameters['uploads']) >= 1 and 'resume' in parameters['uploads']
    assert len(parameters['checkboxes']) > 0

    checkboxes = parameters.get('checkboxes', [])
    assert isinstance(checkboxes['driversLicence'], bool)
    assert isinstance(checkboxes['requireVisa'], bool)
    assert isinstance(checkboxes['legallyAuthorized'], bool)
    assert isinstance(checkboxes['certifiedProfessional'], bool)
    assert isinstance(checkboxes['urgentFill'], bool)
    assert isinstance(checkboxes['commute'], bool)
    assert isinstance(checkboxes['backgroundCheck'], bool)
    assert isinstance(checkboxes['securityClearance'], bool)
    assert 'degreeCompleted' in checkboxes
    assert isinstance(parameters['universityGpa'], (int, float))

    languages = parameters.get('languages', [])
    language_types = {'none', 'conversational', 'professional', 'native or bilingual'}
    for language in languages:
        assert languages[language].lower() in language_types

    experience = parameters.get('experience', [])
    for tech in experience:
        assert isinstance(experience[tech], int)
    assert 'default' in experience

    assert len(parameters['personalInfo'])
    personal_info = parameters.get('personalInfo', [])
    for info in personal_info:
        assert personal_info[info] != ''

    assert len(parameters['eeo'])
    eeo = parameters.get('eeo', [])
    for survey_question in eeo:
        assert eeo[survey_question] != ''

    return parameters


def _close_bot_session(bot: ProtectedLinkedInEasyApply):
    """Gracefully close browser resources if custom shutdown isn't available."""
    if bot is None:
        return

    shutdown_called = False
    if hasattr(bot, 'logout_and_close') and callable(getattr(bot, 'logout_and_close')):
        try:
            bot.logout_and_close()
            shutdown_called = True
        except Exception as exc:
            print(f"⚠️  Error during logout_and_close(): {exc}")
            traceback.print_exc()

    if shutdown_called:
        return

    try:
        if hasattr(bot, 'browser_context') and bot.browser_context:
            try:
                bot.browser_context.close()
            except Exception:
                traceback.print_exc()
        elif hasattr(bot, 'browser') and bot.browser and hasattr(bot.browser, 'close'):
            try:
                bot.browser.close()
            except Exception:
                traceback.print_exc()
    finally:
        if hasattr(bot, 'anti_detection'):
            try:
                bot.anti_detection.save_session_data()
            except Exception as exc:
                print(f"⚠️  Could not save session data: {exc}")


def run_hibernation_session():
    """Executes a single, short-lived hibernation session of the bot."""
    print("\n--- [START] Hibernation Session ---")

    anti_ban_config = load_hibernation_config()
    hibernation_config = anti_ban_config.get('hibernation_mode', {})

    parameters = validate_yaml()

    max_applications = max(1, int(hibernation_config.get('max_applications_per_session', 1)))
    min_session_minutes = max(1, int(hibernation_config.get('min_session_duration_minutes', 5)))
    max_session_minutes = max(min_session_minutes, int(hibernation_config.get('max_session_duration_minutes', 15)))
    session_duration_minutes = random.randint(min_session_minutes, max_session_minutes)
    session_end_time = datetime.now() + timedelta(minutes=session_duration_minutes)

    chance_of_human_activity = float(hibernation_config.get('chance_of_human_activity', 0.9))

    bot = None
    try:
        bot = ProtectedLinkedInEasyApply(parameters, use_stealth_browser=True)

        # Initialize browser
        if hasattr(bot, 'initialize_browser') and not bot.initialize_browser():
            raise RuntimeError("Failed to initialize browser")

        # Login
        if hasattr(bot, 'protected_login') and not bot.protected_login():
            raise RuntimeError("Failed to login")

        # Simulate human-like browsing before applying
        if random.random() < chance_of_human_activity:
            simulated_minutes = random.randint(2, 5)
            print(f"🤖 Simulating human-like browsing for {simulated_minutes} minutes...")
            time.sleep(simulated_minutes * 60)

        # Run single application session (method doesn't accept parameters)
        if hasattr(bot, 'bot') and hasattr(bot.bot, 'run_single_application_session'):
            bot.bot.run_single_application_session()
        elif hasattr(bot, 'protected_start_applying'):
            print("⚠️  run_single_application_session() not found – falling back to protected_start_applying().")
            bot.protected_start_applying()
        elif hasattr(bot, 'run'):
            bot.run()
        else:
            raise RuntimeError("No compatible application method found on ProtectedLinkedInEasyApply")

        # Wait to complete session window
        remaining_seconds = (session_end_time - datetime.now()).total_seconds()
        if remaining_seconds > 0:
            print(f"😴 Waiting {remaining_seconds/60:.2f} minutes to complete session window...")
            time.sleep(remaining_seconds)

        print("--- [END] Hibernation Session Completed Successfully ---")

    except Exception as exc:
        print(f"--- [ERROR] Hibernation session failed: {exc} ---")
        traceback.print_exc()
    finally:
        _close_bot_session(bot)
        print("--- [SHUTDOWN] Bot has been terminated. ---\n")


def calculate_next_run_time():
    """Calculates and prints the next recommended run time based on hibernation config."""
    anti_ban_config = load_hibernation_config()
    hibernation_config = anti_ban_config.get('hibernation_mode', {})

    min_h = float(hibernation_config.get('min_hibernation_hours', 8))
    max_h = float(hibernation_config.get('max_hibernation_hours', 48))

    if max_h < min_h:
        max_h = min_h

    sleep_hours = random.uniform(min_h, max_h)
    next_run_time = datetime.now() + timedelta(hours=sleep_hours)

    print("==============================================")
    print(f"Next recommended run time: {next_run_time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Time to wait: {sleep_hours:.2f} hours.")
    print("==============================================\n")


if __name__ == "__main__":
    print("=" * 70)
    print("🌙 LINKEDIN EASY APPLY BOT - HIBERNATION MODE")
    print("=" * 70)
    print("✅ Hibernation strategy: ENABLED")
    print("✅ Anti-ban system: ENABLED")
    print("✅ Stealth browser: ENABLED")
    print("=" * 70)

    run_hibernation_session()
    calculate_next_run_time()