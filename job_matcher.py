#!/usr/bin/env python3
"""
Job Matching and Scoring System
Evaluates job postings and assigns match scores based on user preferences
"""

import re
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

@dataclass
class JobMatch:
    """Job match result with score and reasons"""
    score: float
    reasons: List[str]
    matched_skills: List[str]
    missing_skills: List[str]
    salary_match: bool
    location_match: bool
    experience_match: bool

class JobMatcher:
    """Intelligent job matching system"""
    
    def __init__(self, user_skills: List[str], user_tech_stack: List[str],
                 experience_level: str, prefer_remote: bool,
                 min_salary: int, max_salary: int):
        self.user_skills = [skill.lower() for skill in user_skills]
        self.user_tech_stack = [tech.lower() for tech in user_tech_stack]
        self.experience_level = experience_level.lower()
        self.prefer_remote = prefer_remote
        self.min_salary = min_salary
        self.max_salary = max_salary
        
        # Skill synonyms and variations
        self.skill_synonyms = {
            'python': ['python', 'python3', 'py', 'django', 'flask', 'fastapi'],
            'javascript': ['javascript', 'js', 'node.js', 'nodejs', 'typescript', 'ts'],
            'java': ['java', 'spring', 'spring boot'],
            'react': ['react', 'reactjs', 'react.js'],
            'aws': ['aws', 'amazon web services', 'cloud'],
            'sql': ['sql', 'mysql', 'postgresql', 'postgres', 'database'],
            'docker': ['docker', 'containerization', 'containers'],
            'git': ['git', 'github', 'gitlab', 'version control']
        }
    
    def normalize_skill(self, skill: str) -> str:
        """Normalize skill name for comparison"""
        return skill.lower().strip()
    
    def find_skill_matches(self, text: str) -> Tuple[List[str], List[str]]:
        """Find matching skills in text"""
        text_lower = text.lower()
        matched = []
        missing = []
        
        # Check direct matches
        all_skills = self.user_skills + self.user_tech_stack
        for skill in all_skills:
            normalized = self.normalize_skill(skill)
            if normalized in text_lower:
                matched.append(skill)
            else:
                # Check synonyms
                if skill in self.skill_synonyms:
                    for synonym in self.skill_synonyms[skill]:
                        if synonym in text_lower:
                            matched.append(skill)
                            break
                    else:
                        if skill not in matched:
                            missing.append(skill)
                else:
                    missing.append(skill)
        
        return list(set(matched)), list(set(missing))
    
    def match_experience_level(self, job_description: str) -> Tuple[bool, float]:
        """Match experience level requirements"""
        desc_lower = job_description.lower()
        
        # Experience level keywords
        level_keywords = {
            'junior': ['junior', 'entry', 'entry-level', 'associate', 'graduate', 'intern'],
            'mid': ['mid', 'mid-level', 'intermediate', 'experienced', '2-5 years', '3-5 years'],
            'senior': ['senior', 'lead', 'principal', 'architect', '5+ years', '7+ years', '10+ years']
        }
        
        user_level = self.experience_level
        score = 0.0
        match = False
        
        # Check for user's level
        if user_level in level_keywords:
            for keyword in level_keywords[user_level]:
                if keyword in desc_lower:
                    match = True
                    score = 1.0
                    break
        
        # Check for compatible levels
        if not match:
            if user_level == 'senior':
                # Senior can apply to mid/junior
                if any(kw in desc_lower for kw in level_keywords['mid'] + level_keywords['junior']):
                    match = True
                    score = 0.7
            elif user_level == 'mid':
                # Mid can apply to junior
                if any(kw in desc_lower for kw in level_keywords['junior']):
                    match = True
                    score = 0.8
        
        return match, score
    
    def match_salary(self, job_description: str) -> Tuple[bool, float]:
        """Extract and match salary information"""
        desc_lower = job_description.lower()
        
        # Look for salary ranges
        salary_patterns = [
            r'\$?(\d{1,3}(?:,\d{3})*(?:k|K)?)\s*-\s*\$?(\d{1,3}(?:,\d{3})*(?:k|K)?)',
            r'salary[:\s]+\$?(\d{1,3}(?:,\d{3})*(?:k|K)?)',
            r'(\d{1,3}(?:,\d{3})*(?:k|K)?)\s*per\s*(?:year|annum)'
        ]
        
        found_salaries = []
        for pattern in salary_patterns:
            matches = re.findall(pattern, desc_lower)
            for match in matches:
                if isinstance(match, tuple):
                    found_salaries.extend(match)
                else:
                    found_salaries.append(match)
        
        if not found_salaries:
            # No salary info - assume it might be acceptable
            return True, 0.5
        
        # Parse salary values
        for salary_str in found_salaries:
            try:
                # Remove $ and convert k/K to thousands
                clean = salary_str.replace('$', '').replace(',', '')
                if 'k' in clean.lower():
                    value = int(clean.lower().replace('k', '')) * 1000
                else:
                    value = int(clean)
                
                # Check if within range
                if self.min_salary <= value <= self.max_salary:
                    return True, 1.0
                elif value < self.min_salary:
                    return False, 0.3
                else:
                    # Above max - still acceptable but less ideal
                    return True, 0.7
            except:
                continue
        
        return True, 0.5  # Default: acceptable
    
    def match_location(self, job_location: str, job_description: str) -> Tuple[bool, float]:
        """Match location preferences"""
        location_lower = job_location.lower()
        desc_lower = job_description.lower()
        
        # Check for remote
        remote_keywords = ['remote', 'work from home', 'wfh', 'distributed', 'anywhere']
        is_remote = any(kw in location_lower or kw in desc_lower for kw in remote_keywords)
        
        if self.prefer_remote:
            if is_remote:
                return True, 1.0
            else:
                return True, 0.6  # On-site but still acceptable
        else:
            if is_remote:
                return True, 0.8  # Remote is fine even if not preferred
            else:
                return True, 1.0  # On-site matches preference
    
    def calculate_match_score(self, job_title: str, company: str, 
                            job_description: str, job_location: str) -> JobMatch:
        """Calculate overall match score for a job"""
        reasons = []
        matched_skills = []
        missing_skills = []
        
        # Combine all text for skill matching
        all_text = f"{job_title} {job_description}".lower()
        
        # Skill matching (40% weight)
        matched, missing = self.find_skill_matches(all_text)
        matched_skills = matched
        missing_skills = missing[:5]  # Limit missing skills
        
        skill_score = len(matched) / max(len(self.user_skills + self.user_tech_stack), 1)
        if skill_score > 0.5:
            reasons.append(f"Matched {len(matched)} required skills")
        else:
            reasons.append(f"Only matched {len(matched)} skills")
        
        # Experience level matching (20% weight)
        exp_match, exp_score = self.match_experience_level(job_description)
        if exp_match:
            reasons.append("Experience level matches")
        else:
            reasons.append("Experience level may not match")
        
        # Salary matching (20% weight)
        salary_match, salary_score = self.match_salary(job_description)
        if salary_score >= 0.8:
            reasons.append("Salary range matches")
        elif salary_score >= 0.5:
            reasons.append("Salary information available")
        else:
            reasons.append("Salary may be below expectations")
        
        # Location matching (20% weight)
        loc_match, loc_score = self.match_location(job_location, job_description)
        if loc_score >= 0.9:
            reasons.append("Location preference matches")
        elif loc_score >= 0.7:
            reasons.append("Location is acceptable")
        
        # Calculate weighted score
        total_score = (
            skill_score * 0.4 +
            exp_score * 0.2 +
            salary_score * 0.2 +
            loc_score * 0.2
        )
        
        return JobMatch(
            score=total_score,
            reasons=reasons,
            matched_skills=matched_skills,
            missing_skills=missing_skills,
            salary_match=salary_match,
            location_match=loc_match,
            experience_match=exp_match
        )
    
    def should_apply(self, match: JobMatch, min_score: float = 0.6) -> bool:
        """Determine if job should be applied to based on match score"""
        return match.score >= min_score

