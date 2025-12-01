# Testing Workflow for Job Agent

## Problem: Test Runs Pollute Production Data

When testing the digest system, jobs get marked with `digest_sent_at` timestamps even though they were only test emails. This means when you're ready to send the production digest, those jobs won't appear (already marked as "sent").

## Solution: Use --dry-run Flag

### Development/Testing Mode

```bash
# Test scraper (stores + scores jobs)
PYTHONPATH=$PWD job-agent-venv/bin/python src/jobs/weekly_unified_scraper.py --profile wes

# Test digest WITHOUT marking jobs as sent
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py \
  --profile wes \
  --dry-run
```

**Output:**
```
🧪 DRY RUN - Would send to wesvanooyen@gmail.com
  Subject: 🎯 5 Job Matches - 2025-11-30
```

### Production Mode

```bash
# Send REAL digest AND mark jobs as sent
PYTHONPATH=$PWD job-agent-venv/bin/python src/send_profile_digest.py \
  --profile wes
```

## Flag Reference

| Flag | Sends Email? | Marks as Sent? | Use Case |
|------|-------------|----------------|----------|
| *(none)* | ✅ Yes | ✅ Yes | Production digest |
| `--dry-run` | ❌ No | ❌ No | Testing/preview |
| `--force-resend` | ✅ Yes | ❌ No | Re-send previous jobs |

## Testing Checklist

- [ ] Run scraper to get new jobs
- [ ] Test digest with `--dry-run` to verify formatting
- [ ] Fix any issues
- [ ] Run digest without `--dry-run` for production send
- [ ] Verify jobs marked as sent in database

## Common Mistakes

❌ **Wrong:** Test without `--dry-run`, jobs get marked as sent
```bash
# DON'T DO THIS during testing
./src/send_profile_digest.py --profile wes  # Marks jobs as sent!
```

✅ **Correct:** Always use `--dry-run` during testing
```bash
# DO THIS during testing
./src/send_profile_digest.py --profile wes --dry-run  # Safe!
```
