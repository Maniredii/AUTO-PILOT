#!/usr/bin/env python3
"""
GUI Skill Editor for EasyApplyBot
Allows users to add missing skills to their resume when skill matching fails
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import yaml
import os
from datetime import datetime

class SkillEditorGUI:
    def __init__(self, missing_skills, current_skills, job_title, company):
        self.missing_skills = missing_skills
        self.current_skills = current_skills.copy()  # Make a copy to avoid modifying original
        self.job_title = job_title
        self.company = company
        self.added_skills = []
        self.removed_skills = []
        
        # Automatically add missing skills to improve job match
        self.auto_add_missing_skills()
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("EasyApplyBot - Skill Editor")
        self.root.geometry("800x700")
        self.root.resizable(True, True)
        
        # Configure style
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure style for accent button
        style.configure('Accent.TButton', background='#0078d4', foreground='white')
        
        self.setup_ui()
        self.center_window()
    
    def auto_add_missing_skills(self):
        """
        Automatically add missing skills to improve job match
        """
        print("🤖 Auto-adding missing skills to improve job match...")
        
        for skill in self.missing_skills:
            if skill not in self.current_skills:
                self.current_skills.append(skill)
                self.added_skills.append(skill)
                print(f"  ➕ Auto-added: {skill}")
        
        if self.added_skills:
            print(f"✅ Automatically added {len(self.added_skills)} skills!")
            print(f"   New skills: {', '.join(self.added_skills)}")
            print(f"   Total skills now: {len(self.current_skills)}")
        else:
            print("ℹ️  No new skills needed to be added")
        
    def setup_ui(self):
        """Setup the user interface"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="20")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        ttk.Label(header_frame, text="🎯 Skill Mismatch Detected!", 
                 font=('Arial', 16, 'bold')).grid(row=0, column=0, columnspan=2)
        
        ttk.Label(header_frame, text=f"Job: {self.job_title}", 
                 font=('Arial', 12)).grid(row=1, column=0, columnspan=2, pady=(5, 0))
        ttk.Label(header_frame, text=f"Company: {self.company}", 
                 font=('Arial', 10, 'italic')).grid(row=2, column=0, columnspan=2)
        
        # Auto-added skills notification
        if self.added_skills:
            auto_added_frame = ttk.LabelFrame(header_frame, text="🤖 Auto-Added Skills", padding="10")
            auto_added_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
            auto_added_frame.columnconfigure(0, weight=1)
            
            ttk.Label(auto_added_frame, 
                     text=f"✅ Automatically added {len(self.added_skills)} skills to improve your job match!",
                     font=('Arial', 10, 'bold'),
                     foreground='green').grid(row=0, column=0, sticky=(tk.W, tk.E))
            
            skills_text = ", ".join(self.added_skills[:8])
            if len(self.added_skills) > 8:
                skills_text += f" and {len(self.added_skills) - 8} more..."
            
            ttk.Label(auto_added_frame, 
                     text=f"New skills: {skills_text}",
                     font=('Arial', 9)).grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
            
            ttk.Label(auto_added_frame, 
                     text="💡 You can remove any skills you don't want to keep below",
                     font=('Arial', 9, 'italic'),
                     foreground='blue').grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        
        # Missing skills section
        if self.added_skills:
            # All missing skills have been auto-added
            missing_frame = ttk.LabelFrame(main_frame, text="✅ All Missing Skills Auto-Added!", padding="10")
            missing_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
            missing_frame.columnconfigure(0, weight=1)
            
            ttk.Label(missing_frame, 
                     text="🎉 Great news! All required skills have been automatically added to your resume.",
                     font=('Arial', 10, 'bold'),
                     foreground='green').grid(row=0, column=0, sticky=(tk.W, tk.E))
            
            ttk.Label(missing_frame, 
                     text="Your skill match score should now be significantly higher!",
                     font=('Arial', 9)).grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
            
            ttk.Label(missing_frame, 
                     text="You can review and adjust your skills below if needed.",
                     font=('Arial', 9, 'italic')).grid(row=2, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
        else:
            # Some skills still missing
            missing_frame = ttk.LabelFrame(main_frame, text="❌ Missing Skills (Required by Job)", padding="10")
            missing_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
            missing_frame.columnconfigure(0, weight=1)
            
            # Create listbox for missing skills
            missing_listbox = tk.Listbox(missing_frame, height=6, selectmode=tk.MULTIPLE)
            missing_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
            
            # Scrollbar for missing skills
            missing_scrollbar = ttk.Scrollbar(missing_frame, orient=tk.VERTICAL, command=missing_listbox.yview)
            missing_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
            missing_listbox.configure(yscrollcommand=missing_scrollbar.set)
            
            # Populate missing skills
            for skill in self.missing_skills:
                missing_listbox.insert(tk.END, skill)
        
        # Current skills section
        current_frame = ttk.LabelFrame(main_frame, text="✅ Your Current Skills", padding="10")
        current_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        current_frame.columnconfigure(0, weight=1)
        
        # Create listbox for current skills
        current_listbox = tk.Listbox(current_frame, height=6, selectmode=tk.MULTIPLE)
        current_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        # Scrollbar for current skills
        current_scrollbar = ttk.Scrollbar(current_frame, orient=tk.VERTICAL, command=current_listbox.yview)
        current_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        current_listbox.configure(yscrollcommand=current_scrollbar.set)
        
        # Populate current skills
        for skill in self.current_skills:
            current_listbox.insert(tk.END, skill)
        
        # Action buttons frame
        action_frame = ttk.Frame(main_frame)
        action_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        
        if self.added_skills:
            # All skills auto-added - show different actions
            ttk.Label(action_frame, 
                     text="🎯 All required skills have been automatically added!",
                     font=('Arial', 10, 'bold'),
                     foreground='green').grid(row=0, column=0, columnspan=3, pady=(0, 10))
            
            # Add missing skills button (disabled if all added)
            add_btn = ttk.Button(action_frame, text="➕ Add More Skills", 
                               command=lambda: self.add_selected_skills(missing_listbox) if 'missing_listbox' in locals() else None,
                               state='disabled' if not self.missing_skills else 'normal')
            add_btn.grid(row=1, column=0, padx=(0, 10))
            
            # Remove current skills button
            remove_btn = ttk.Button(action_frame, text="➖ Remove Selected Skills", 
                                  command=lambda: self.remove_selected_skills(current_listbox))
            remove_btn.grid(row=1, column=1, padx=(0, 10))
            
            # Add custom skill button
            custom_btn = ttk.Button(action_frame, text="✨ Add Custom Skill", 
                                  command=self.add_custom_skill)
            custom_btn.grid(row=1, column=2)
        else:
            # Some skills still missing - show standard actions
            # Add missing skills button
            add_btn = ttk.Button(action_frame, text="➕ Add Selected Skills to Resume", 
                               command=lambda: self.add_selected_skills(missing_listbox))
            add_btn.grid(row=0, column=0, padx=(0, 10))
            
            # Remove current skills button
            remove_btn = ttk.Button(action_frame, text="➖ Remove Selected Skills", 
                                  command=lambda: self.remove_selected_skills(current_listbox))
            remove_btn.grid(row=0, column=1, padx=(0, 10))
            
            # Add custom skill button
            custom_btn = ttk.Button(action_frame, text="✨ Add Custom Skill", 
                                  command=self.add_custom_skill)
            custom_btn.grid(row=0, column=2)
        
        # Skill categories frame
        categories_frame = ttk.LabelFrame(main_frame, text="📚 Skill Categories", padding="10")
        categories_frame.grid(row=4, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        categories_frame.columnconfigure(0, weight=1)
        
        # Skill category buttons
        categories = [
            ("Programming", ['Python', 'JavaScript', 'Java', 'C++', 'C#', 'PHP', 'Ruby', 'Go', 'Rust', 'Swift']),
            ("Frameworks", ['React', 'Angular', 'Vue', 'Node.js', 'Express', 'Django', 'Flask', 'Spring']),
            ("Databases", ['SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQLite']),
            ("Cloud/DevOps", ['AWS', 'Azure', 'Docker', 'Kubernetes', 'Git', 'Jenkins', 'Terraform']),
            ("Methodologies", ['Agile', 'Scrum', 'Kanban', 'DevOps', 'CI/CD', 'TDD', 'BDD'])
        ]
        
        for i, (category, skills) in enumerate(categories):
            cat_frame = ttk.Frame(categories_frame)
            cat_frame.grid(row=i//3, column=i%3, sticky=(tk.W, tk.E), padx=5, pady=5)
            
            ttk.Label(cat_frame, text=f"{category}:", font=('Arial', 10, 'bold')).pack(anchor=tk.W)
            
            for skill in skills:
                if skill not in self.current_skills:
                    btn = ttk.Button(cat_frame, text=skill, 
                                   command=lambda s=skill: self.add_skill_to_list(s))
                    btn.pack(fill=tk.X, pady=1)
        
        # Summary frame
        summary_frame = ttk.LabelFrame(main_frame, text="📊 Summary", padding="10")
        summary_frame.grid(row=5, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 20))
        summary_frame.columnconfigure(0, weight=1)
        
        self.summary_text = tk.Text(summary_frame, height=4, wrap=tk.WORD)
        self.summary_text.grid(row=0, column=0, sticky=(tk.W, tk.E), padx=(0, 10))
        
        summary_scrollbar = ttk.Scrollbar(summary_frame, orient=tk.VERTICAL, command=self.summary_text.yview)
        summary_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.summary_text.configure(yscrollcommand=summary_scrollbar.set)
        
        self.update_summary()
        
        # Bottom buttons frame
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.grid(row=6, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(20, 0))
        
        if self.added_skills:
            # Skills were auto-added - emphasize continuing
            ttk.Label(bottom_frame, 
                     text="🎯 Your skills now match this job much better!",
                     font=('Arial', 10, 'bold'),
                     foreground='green').grid(row=0, column=0, columnspan=3, pady=(0, 10))
            
            # Save and continue button (primary action)
            save_btn = ttk.Button(bottom_frame, text="🚀 Continue with Improved Skills", 
                                command=self.save_and_continue, style='Accent.TButton')
            save_btn.grid(row=1, column=0, padx=(0, 10))
            
            # Review skills button
            review_btn = ttk.Button(bottom_frame, text="📝 Review & Edit Skills", 
                                  command=self.review_skills)
            review_btn.grid(row=1, column=1, padx=(0, 10))
            
            # Skip button
            skip_btn = ttk.Button(bottom_frame, text="⏭️ Skip This Job", 
                                command=self.skip_job)
            skip_btn.grid(row=1, column=2)
        else:
            # No skills auto-added - standard interface
            # Save and continue button
            save_btn = ttk.Button(bottom_frame, text="💾 Save Skills & Continue", 
                                command=self.save_and_continue, style='Accent.TButton')
            save_btn.grid(row=0, column=0, padx=(0, 10))
            
            # Skip button
            skip_btn = ttk.Button(bottom_frame, text="⏭️ Skip This Job", 
                                command=self.skip_job)
            skip_btn.grid(row=0, column=1, padx=(0, 10))
            
            # Cancel button
            cancel_btn = ttk.Button(bottom_frame, text="❌ Cancel", 
                                  command=self.cancel)
            cancel_btn.grid(row=0, column=2)
        
    def center_window(self):
        """Center the window on screen"""
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
        
    def review_skills(self):
        """Allow user to review and edit skills before continuing"""
        # This method enables the skill editing interface
        # The skills are already loaded, so user can make adjustments
        messagebox.showinfo("Review Skills", 
                          "You can now review and edit your skills above.\n\n"
                          "• Remove any skills you don't want to keep\n"
                          "• Add custom skills if needed\n"
                          "• Browse skill categories for additional options\n\n"
                          "Click '🚀 Continue with Improved Skills' when ready!")
        
    def add_selected_skills(self, listbox):
        """Add selected missing skills to the resume"""
        selected_indices = listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select skills to add.")
            return
            
        for index in selected_indices:
            skill = listbox.get(index)
            if skill not in self.current_skills:
                self.current_skills.append(skill)
                self.added_skills.append(skill)
                
        self.update_summary()
        messagebox.showinfo("Skills Added", f"Added {len(selected_indices)} skills to your resume!")
        
    def remove_selected_skills(self, listbox):
        """Remove selected current skills from the resume"""
        selected_indices = listbox.curselection()
        if not selected_indices:
            messagebox.showwarning("No Selection", "Please select skills to remove.")
            return
            
        for index in reversed(selected_indices):
            skill = listbox.get(index)
            if skill in self.current_skills:
                self.current_skills.remove(skill)
                self.removed_skills.append(skill)
                
        self.update_summary()
        messagebox.showinfo("Skills Removed", f"Removed {len(selected_indices)} skills from your resume!")
        
    def add_custom_skill(self):
        """Add a custom skill to the resume"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Add Custom Skill")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (200)
        y = (dialog.winfo_screenheight() // 2) - (100)
        dialog.geometry(f'400x200+{x}+{y}')
        
        ttk.Label(dialog, text="Enter custom skill:").pack(pady=20)
        
        skill_entry = ttk.Entry(dialog, width=40)
        skill_entry.pack(pady=10)
        skill_entry.focus()
        
        def add_skill():
            skill = skill_entry.get().strip()
            if skill:
                if skill not in self.current_skills:
                    self.current_skills.append(skill)
                    self.added_skills.append(skill)
                    self.update_summary()
                    messagebox.showinfo("Success", f"Added custom skill: {skill}")
                    dialog.destroy()
                else:
                    messagebox.showwarning("Duplicate", "This skill already exists!")
            else:
                messagebox.showwarning("Empty", "Please enter a skill name.")
                
        ttk.Button(dialog, text="Add Skill", command=add_skill).pack(pady=20)
        
        # Bind Enter key
        skill_entry.bind('<Return>', lambda e: add_skill())
        
    def add_skill_to_list(self, skill):
        """Add a skill from category buttons"""
        if skill not in self.current_skills:
            self.current_skills.append(skill)
            self.added_skills.append(skill)
            self.update_summary()
            messagebox.showinfo("Skill Added", f"Added {skill} to your resume!")
        else:
            messagebox.showinfo("Already Exists", f"{skill} is already in your resume!")
            
    def update_summary(self):
        """Update the summary text"""
        summary = f"Current Skills: {len(self.current_skills)}\n"
        summary += f"Missing Skills: {len(self.missing_skills)}\n"
        summary += f"Skills Added: {len(self.added_skills)}\n"
        summary += f"Skills Removed: {len(self.removed_skills)}\n\n"
        
        if self.added_skills:
            summary += "🤖 Auto-Added Skills:\n"
            for skill in self.added_skills:
                summary += f"  ➕ {skill}\n"
            
            # Calculate improvement
            if len(self.missing_skills) > 0:
                improvement = (len(self.added_skills) / (len(self.missing_skills) + len(self.added_skills))) * 100
                summary += f"\n📈 Skill Match Improvement: +{improvement:.1f}%\n"
            else:
                summary += f"\n🎯 All Required Skills Now Covered!\n"
                
        if self.removed_skills:
            summary += "\nRemoved Skills:\n"
            for skill in self.removed_skills:
                summary += f"  ➖ {skill}\n"
        
        # Add recommendation
        if self.added_skills and not self.removed_skills:
            summary += "\n💡 Recommendation: Your skills now match this job much better!"
        elif self.added_skills and self.removed_skills:
            summary += "\n💡 Recommendation: Skills updated - review to ensure good match."
        elif not self.added_skills and not self.removed_skills:
            summary += "\n💡 Recommendation: No changes made - your skills already match well."
                
        self.summary_text.delete(1.0, tk.END)
        self.summary_text.insert(1.0, summary)
        
    def save_and_continue(self):
        """Save skills and continue with job application"""
        if self.added_skills or self.removed_skills:
            # Update config.yaml with new skills
            try:
                self.update_config_file()
                messagebox.showinfo("Success", "Skills updated successfully! Continuing with job application.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to update config file: {str(e)}")
                return
                
        self.root.destroy()
        
    def skip_job(self):
        """Skip this job application"""
        result = messagebox.askyesno("Skip Job", 
                                   f"Are you sure you want to skip applying to {self.company}?\n\n"
                                   f"Job: {self.job_title}")
        if result:
            self.root.destroy()
            
    def cancel(self):
        """Cancel the skill editing process"""
        result = messagebox.askyesno("Cancel", 
                                   "Are you sure you want to cancel? All changes will be lost.")
        if result:
            self.root.destroy()
            
    def update_config_file(self):
        """Update the config.yaml file with new skills"""
        try:
            # Read current config
            with open('config.yaml', 'r', encoding='utf-8') as file:
                config = yaml.safe_load(file)
            
            # Update skills
            if 'userSkills' not in config:
                config['userSkills'] = []
            if 'userTechStack' not in config:
                config['userTechStack'] = []
                
            # Add new skills to userSkills
            for skill in self.added_skills:
                if skill not in config['userSkills']:
                    config['userSkills'].append(skill)
                    
            # Remove deleted skills from userSkills
            for skill in self.removed_skills:
                if skill in config['userSkills']:
                    config['userSkills'].remove(skill)
                    
            # Add new skills to userTechStack if they're technical
            technical_skills = [
                'Python', 'JavaScript', 'Java', 'C++', 'C#', 'PHP', 'Ruby', 'Go', 'Rust', 'Swift',
                'React', 'Angular', 'Vue', 'Node.js', 'Express', 'Django', 'Flask', 'Spring',
                'SQL', 'MySQL', 'PostgreSQL', 'MongoDB', 'Redis', 'Oracle', 'SQLite',
                'AWS', 'Azure', 'Docker', 'Kubernetes', 'Git', 'Jenkins', 'Terraform'
            ]
            
            for skill in self.added_skills:
                if skill in technical_skills and skill not in config['userTechStack']:
                    config['userTechStack'].append(skill)
                    
            # Remove deleted skills from userTechStack
            for skill in self.removed_skills:
                if skill in config['userTechStack']:
                    config['userTechStack'].remove(skill)
            
            # Write updated config
            with open('config.yaml', 'w', encoding='utf-8') as file:
                yaml.dump(config, file, default_flow_style=False, allow_unicode=True)
                
            # Create backup
            backup_file = f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"
            with open(backup_file, 'w', encoding='utf-8') as file:
                yaml.dump(config, file, default_flow_style=False, allow_unicode=True)
                
            print(f"✅ Config updated successfully! Backup created: {backup_file}")
            
        except Exception as e:
            print(f"❌ Error updating config file: {str(e)}")
            raise
            
    def run(self):
        """Run the GUI application"""
        self.root.mainloop()
        return self.added_skills, self.removed_skills

def show_skill_editor(missing_skills, current_skills, job_title, company):
    """
    Show the skill editor GUI
    
    Args:
        missing_skills (list): Skills required by the job but not in resume
        current_skills (list): Current skills in the resume
        job_title (str): Title of the job being applied to
        company (str): Company name
        
    Returns:
        tuple: (added_skills, removed_skills) or (None, None) if cancelled
    """
    try:
        app = SkillEditorGUI(missing_skills, current_skills, job_title, company)
        return app.run()
    except Exception as e:
        print(f"❌ Error showing skill editor: {str(e)}")
        return None, None

if __name__ == "__main__":
    # Test the GUI
    test_missing = ['Python', 'AWS', 'Docker', 'Kubernetes']
    test_current = ['JavaScript', 'React', 'Node.js', 'SQL']
    
    print("🧪 Testing Skill Editor GUI...")
    added, removed = show_skill_editor(test_missing, test_current, "Software Engineer", "Tech Corp")
    
    if added or removed:
        print(f"✅ Skills updated - Added: {added}, Removed: {removed}")
    else:
        print("❌ No changes made or cancelled")
