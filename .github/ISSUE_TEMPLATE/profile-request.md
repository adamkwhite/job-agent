---
name: Profile Creation Request
about: Request a new job alert profile
title: 'New Profile: [Your Name]'
labels: profile-request
assignees: ''

---

## Profile Request

Fill out the template below to create your job alert profile.

### Instructions

1. Fill in all fields below (follow the comments for guidance)
2. Delete or skip optional sections you don't need
3. Submit this issue when complete

### My Profile

```
# ==============================================================================
# JOB AGENT PROFILE TEMPLATE
# ==============================================================================
# Fill in the fields below - lines starting with # are comments (will be ignored)
# Use commas to separate multiple values
# ==============================================================================

# ==============================================================================
# BASIC INFO
# ==============================================================================

# Your full name
name:

# Your email address (where digests will be sent)
email:

# Should this profile receive weekly digest emails? (yes/no)
enabled: yes

# ==============================================================================
# EMAIL CREDENTIALS (Optional - only if you want your own inbox)
# ==============================================================================
# Leave blank to receive digests with jobs from the shared inbox

# Gmail address that receives job alerts (e.g., yourname.jobalerts@gmail.com)
email_username:

# Environment variable name for your Gmail app password
app_password_env:

# ==============================================================================
# SCORING - TARGET SENIORITY
# ==============================================================================
# Options: intern, junior, mid-level, senior, staff, lead, principal, director, vp, cto, head, architect

target_seniority:

# ==============================================================================
# SCORING - DOMAIN KEYWORDS
# ==============================================================================
# Technologies, industries, or domains (e.g., robotics, ai, python, product, saas)

domain_keywords:

# ==============================================================================
# SCORING - ROLE TYPES
# ==============================================================================

# Engineering roles
engineering_roles:

# Data/ML roles
data_roles:

# DevOps/Platform roles
devops_roles:

# Product roles
product_roles:

# ==============================================================================
# SCORING - COMPANY PREFERENCES
# ==============================================================================

# Company stages (e.g., startup, series a, series b, growth, public)
company_stage:

# Keywords to AVOID in job titles
avoid_keywords:

# ==============================================================================
# SCORING - LOCATION PREFERENCES
# ==============================================================================

# Remote work keywords
remote_keywords: remote, work from home, wfh, anywhere, distributed

# Hybrid work keywords
hybrid_keywords: hybrid

# Cities you'd consider for hybrid/onsite
preferred_cities:

# Regions you'd consider
preferred_regions:

# ==============================================================================
# SCORING - FILTERING (Advanced - most users can skip this)
# ==============================================================================

# How aggressively to filter software roles? (conservative/moderate/aggressive)
filtering_aggression: conservative

# Bonus points for hardware companies (0-10)
hardware_company_boost: 0

# Penalty for software companies (0 to -20)
software_company_penalty: 0

# ==============================================================================
# DIGEST SETTINGS
# ==============================================================================

# Minimum grade to include in weekly digest (A/B/C/D/F)
digest_min_grade: C

# Minimum score to include (0-115)
digest_min_score: 63

# Minimum location score (0-15)
digest_min_location_score: 8

# How often to send digests? (weekly/daily)
digest_frequency: weekly

# ==============================================================================
# NOTIFICATIONS (Instant alerts for great matches)
# ==============================================================================

# Send instant notifications? (yes/no)
notifications_enabled: yes

# Minimum grade for notifications (A/B/C/D/F)
notifications_min_grade: B

# Minimum score for notifications (0-115)
notifications_min_score: 80

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
