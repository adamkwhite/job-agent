# Profile Management

This directory contains user profiles for the job agent system. Each profile defines scoring criteria, preferences, and notification settings.

## Quick Start - Creating a New Profile

### Step 1: Copy the Template

```bash
cp profiles/TEMPLATE.txt profiles/yourname.txt
```

### Step 2: Edit Your Profile

Open `profiles/yourname.txt` and fill in your information:

```bash
vim profiles/yourname.txt
# or
code profiles/yourname.txt
```

The template has clear comments explaining each field. Just fill in your preferences!

### Step 3: Generate JSON

```bash
python scripts/generate_profile_json.py yourname
```

This creates `profiles/yourname.json` automatically.

### Step 4: Add Email Credentials (Optional)

If you want your own job alerts inbox, add to `.env`:

```bash
echo "YOUR_GMAIL_APP_PASSWORD=your-app-password-here" >> .env
```

Replace `YOUR_GMAIL_APP_PASSWORD` with whatever you named it in the template.

### Step 5: Test Your Profile

```bash
./run-tui.sh
```

Select your profile from the list and run a test scrape!

## File Formats

### Text Template (`.txt`) - Human-Friendly
- Easy to read and edit
- Comments explain each field
- Comma-separated lists
- Example: `profiles/TEMPLATE.txt`

### JSON Profile (`.json`) - System Format
- Auto-generated from `.txt` files
- Used by the job agent system
- Don't edit directly - update the `.txt` and regenerate
- Example: `profiles/adam.json`

## Profile Options Explained

### Basic Info
- **name**: Your full name
- **email**: Where weekly digest emails are sent
- **enabled**: `yes` to receive weekly digest emails, `no` to disable (jobs still scored, just no email sent)

### Email Credentials (Optional)
- **email_username**: Gmail address for job alerts (e.g., `yourname.jobalerts@gmail.com`)
- **app_password_env**: Environment variable name in `.env` file

If you DON'T have your own inbox, leave these blank. You'll still get digests with jobs from the shared inbox.

### Scoring - Target Seniority
What level are you targeting?
- Options: `intern`, `junior`, `mid-level`, `senior`, `staff`, `lead`, `principal`, `director`, `vp`, `cto`, `head`, `architect`
- Example: `senior, staff, lead, principal`

### Scoring - Domain Keywords
Technologies, industries, or domains you care about:
- Examples: `robotics`, `hardware`, `ai`, `python`, `product`, `saas`, `devops`
- More keywords = better matching

### Scoring - Role Types
Categories of roles you're interested in:
- **Engineering**: Software engineer, developer, architect
- **Data**: Data scientist, ML engineer, data engineer
- **DevOps**: DevOps, SRE, platform engineer
- **Product**: Product manager, product lead

### Company Preferences
- **company_stage**: `startup`, `seed`, `series a`, `series b`, `series c`, `growth`, `public`
- **avoid_keywords**: Auto-reject if these appear in title (e.g., `junior`, `intern`)

### Location Preferences
- **remote_keywords**: Indicates remote work (`remote`, `wfh`, `anywhere`)
- **hybrid_keywords**: Indicates hybrid work (`hybrid`)
- **preferred_cities**: Cities you'd consider for hybrid/onsite
- **preferred_regions**: Regions you'd consider

### Filtering (Advanced)
For hardware-focused profiles:
- **filtering_aggression**: `conservative`/`moderate`/`aggressive` (how strictly to filter software roles)
- **hardware_company_boost**: Bonus points for hardware companies (0-10)
- **software_company_penalty**: Penalty for software companies (0 to -20)

For software profiles, keep these at default (0).

### Digest Settings
- **digest_min_grade**: Minimum grade to include (`A`/`B`/`C`/`D`)
- **digest_min_score**: Minimum score (0-115)
- **digest_frequency**: `weekly` or `daily`

### Notifications
Instant alerts for great matches:
- **notifications_enabled**: `yes` or `no`
- **notifications_min_grade**: Minimum grade for alerts (usually `B`)
- **notifications_min_score**: Minimum score for alerts (usually 80)

## Examples

See existing profiles for reference:
- `profiles/wes.json` - VP/Director roles in Robotics/Hardware
- `profiles/adam.json` - Senior/Staff roles in Software/Product
- `profiles/eli.json` - Director/VP/CTO roles in Fintech/Healthtech

## Updating an Existing Profile

### Option 1: Regenerate from Text (Recommended)
1. Edit `profiles/yourname.txt`
2. Run `python scripts/generate_profile_json.py yourname`
3. Test with `./run-tui.sh`

### Option 2: Edit JSON Directly
1. Edit `profiles/yourname.json` directly
2. Test with `./run-tui.sh`

**Note:** If you edit JSON directly, create a `.txt` backup for easier future updates!

## Troubleshooting

### "Profile text file not found"
```bash
# Copy the template first:
cp profiles/TEMPLATE.txt profiles/yourname.txt
```

### "No such file or directory: .env"
```bash
# Create .env file:
cp .env.example .env
# Add your credentials to .env
```

### "Profile not appearing in TUI"
- Make sure `enabled: yes` in your text template
- Regenerate JSON: `python scripts/generate_profile_json.py yourname`
- Check that `profiles/yourname.json` exists

### "Jobs not being scored for my profile"
- Check that email is valid in profile
- Verify `enabled: true` in the JSON file
- Run with `--profile yourname` flag to test

## Need Help?

See the full documentation:
- [`docs/development/ADDING_NEW_PROFILES.md`](../docs/development/ADDING_NEW_PROFILES.md) - Detailed profile creation guide
- [`docs/development/MULTI_PROFILE_GUIDE.md`](../docs/development/MULTI_PROFILE_GUIDE.md) - How multi-profile system works
- [`CLAUDE.md`](../CLAUDE.md) - Project overview and architecture
