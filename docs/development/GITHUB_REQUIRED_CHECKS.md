# Setting Up Required GitHub Checks

To make the scoring sync check **required** (block PR merging), follow these steps:

## 1. Enable Branch Protection

1. Go to: `https://github.com/adamkwhite/job-agent/settings/branches`
2. Click "Add branch protection rule"
3. Branch name pattern: `main`

## 2. Configure Required Checks

Enable these settings:
- ✅ **Require status checks to pass before merging**
  - Add required check: `check-sync` (from check-scoring-sync.yml workflow)
  - Add required check: `SonarCloud Code Analysis`

- ✅ **Require branches to be up to date before merging**

- ✅ **Do not allow bypassing the above settings**

## 3. Other Recommended Settings

- ✅ Require pull request reviews before merging (optional)
- ✅ Require linear history (optional)
- ✅ Include administrators (enforces rules on repo owners too)

## How It Works

Once configured:

1. **Create PR** with changes to `src/agents/job_scorer.py`
2. **GitHub Action runs** automatically
3. **Check fails** if `src/send_digest_to_wes.py` wasn't also modified
4. **PR is blocked** from merging until email template is updated
5. **Green checkmark** appears when both files are updated

## Manual Override

If you need to bypass (not recommended):
- Temporarily disable branch protection
- Or add yourself to allowed bypass list

## Current Status

The workflow is created (`.github/workflows/check-scoring-sync.yml`) but branch protection must be configured manually in GitHub settings.
