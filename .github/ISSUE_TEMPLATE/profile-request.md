---
name: Profile Creation Request
about: Request a new job alert profile
title: 'New Profile: [Your Name]'
labels: profile-request
assignees: ''

---

## Profile Request

I'd like to create a job alert profile for the job agent system.

### Instructions

1. Download the profile template: [profiles/TEMPLATE.txt](https://raw.githubusercontent.com/adamkwhite/job-agent/main/profiles/TEMPLATE.txt)
2. Fill in your information (see comments in the file for guidance)
3. Paste the completed template below
4. Submit this issue

### My Completed Profile

```
# ==============================================================================
# JOB AGENT PROFILE TEMPLATE
# ==============================================================================
# Paste your completed profile template here
# Make sure to include ALL sections from TEMPLATE.txt
# ==============================================================================

# Your full name
name:

# Your email address (where digests will be sent)
email:

# Should this profile receive weekly digest emails? (yes/no)
enabled: yes

# ... (rest of template - copy from TEMPLATE.txt and fill in)

```

### Email Credentials Setup

**Do you want your own dedicated job alerts inbox?** (Optional)

- [ ] Yes, I'll set up `myname.jobalerts@gmail.com` and provide app password
- [ ] No, just send me digests with jobs from the shared inbox

If yes, you'll need to:
1. Create a Gmail account (e.g., `yourname.jobalerts@gmail.com`)
2. Generate an app password (see [Gmail App Passwords Guide](https://support.google.com/accounts/answer/185833))
3. Securely share the app password with Adam (encrypted email/1Password/etc.)

### Questions or Special Requests

<!-- Any specific preferences, questions, or customizations? -->


---

**For maintainers:**
- [ ] Download profile text from this issue
- [ ] Save as `profiles/{name}.txt`
- [ ] Run `python scripts/generate_profile_json.py {name}`
- [ ] If email credentials provided, add to `.env` file
- [ ] Test profile with `./run-tui.sh`
- [ ] Close issue and notify user
