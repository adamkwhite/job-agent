#!/bin/bash
# Deploy job-agent to Hostinger VPS
# Run from local machine: ./scripts/deploy_to_vps.sh
#
# What this does:
#   1. Clones repo on VPS (or pulls latest)
#   2. Copies gitignored files (.env, profiles/, DB, connections)
#   3. Installs Python deps + Playwright browsers
#   4. Sets up cron jobs
#
# Prerequisites: ssh hostinger works (SSH config entry exists)

set -e

VPS="hostinger"
LOCAL_PROJECT="/home/adam/Code/job-agent"
REMOTE_PROJECT="/home/adam/job-agent"

echo "=== Job Agent VPS Deployment ==="
echo "Target: $VPS:$REMOTE_PROJECT"
echo ""

# -------------------------------------------------------------------
# Step 1: Clone repo (or pull latest)
# -------------------------------------------------------------------
echo "[1/6] Setting up repository..."
ssh "$VPS" bash -s "$REMOTE_PROJECT" << 'REMOTE_REPO'
REMOTE_PROJECT="$1"
if [ -d "$REMOTE_PROJECT/.git" ]; then
    cd "$REMOTE_PROJECT"
    git pull --ff-only
    echo "  ✓ Pulled latest changes"
else
    git clone https://github.com/adamkwhite/job-agent.git "$REMOTE_PROJECT"
    echo "  ✓ Cloned repository"
fi
REMOTE_REPO

# -------------------------------------------------------------------
# Step 2: Copy gitignored files
# -------------------------------------------------------------------
echo "[2/6] Copying gitignored files..."

# .env
scp "$LOCAL_PROJECT/.env" "$VPS:$REMOTE_PROJECT/.env"
echo "  ✓ .env"

# profiles/
scp "$LOCAL_PROJECT/profiles/"*.json "$VPS:$REMOTE_PROJECT/profiles/"
echo "  ✓ profiles/*.json"

# SQLite database
ssh "$VPS" "mkdir -p $REMOTE_PROJECT/data"
scp "$LOCAL_PROJECT/data/jobs.db" "$VPS:$REMOTE_PROJECT/data/jobs.db"
echo "  ✓ data/jobs.db"

# LinkedIn connections (if any exist)
if ls "$LOCAL_PROJECT"/data/profiles/*/connections*.* > /dev/null 2>&1; then
    for dir in "$LOCAL_PROJECT"/data/profiles/*/; do
        profile_name=$(basename "$dir")
        ssh "$VPS" "mkdir -p $REMOTE_PROJECT/data/profiles/$profile_name"
        scp "$dir"connections*.* "$VPS:$REMOTE_PROJECT/data/profiles/$profile_name/" 2>/dev/null || true
    done
    echo "  ✓ LinkedIn connections data"
else
    echo "  - No LinkedIn connections data to copy"
fi

# -------------------------------------------------------------------
# Step 3: Install system dependencies
# -------------------------------------------------------------------
echo "[3/6] Installing system dependencies..."
ssh "$VPS" bash << 'REMOTE_DEPS'
sudo apt-get update -qq
sudo apt-get install -y -qq python3-venv python3-pip > /dev/null 2>&1
echo "  ✓ System packages"
REMOTE_DEPS

# -------------------------------------------------------------------
# Step 4: Create venv and install Python dependencies
# -------------------------------------------------------------------
echo "[4/6] Setting up Python environment..."
ssh "$VPS" bash -s "$REMOTE_PROJECT" << 'REMOTE_PYTHON'
REMOTE_PROJECT="$1"
cd "$REMOTE_PROJECT"

if [ ! -d "job-agent-venv" ]; then
    python3 -m venv job-agent-venv
    echo "  ✓ Created virtualenv"
else
    echo "  ✓ Virtualenv already exists"
fi

source job-agent-venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
echo "  ✓ Python dependencies installed"

# Install Playwright browsers (needed for career page scraping)
playwright install chromium --with-deps
echo "  ✓ Playwright Chromium installed"
REMOTE_PYTHON

# -------------------------------------------------------------------
# Step 5: Create logs and backups directories
# -------------------------------------------------------------------
echo "[5/6] Creating directories..."
ssh "$VPS" "mkdir -p $REMOTE_PROJECT/logs $REMOTE_PROJECT/data/backups"
echo "  ✓ logs/ and data/backups/"

# -------------------------------------------------------------------
# Step 6: Setup cron jobs
# -------------------------------------------------------------------
echo "[6/6] Setting up cron jobs..."
ssh "$VPS" bash -s "$REMOTE_PROJECT" << 'REMOTE_CRON'
REMOTE_PROJECT="$1"

# Make scripts executable
chmod +x "$REMOTE_PROJECT/scripts/run_unified_scraper.sh"
chmod +x "$REMOTE_PROJECT/scripts/backup_database.sh"

# Build crontab (replace any existing job-agent entries)
EXISTING=$(crontab -l 2>/dev/null | grep -v "job-agent" || true)
{
    echo "$EXISTING"
    echo "# Job Agent - daily scraper at 6am ET"
    echo "0 6 * * * $REMOTE_PROJECT/scripts/run_unified_scraper.sh"
    echo "# Job Agent - daily DB backup at 3am"
    echo "0 3 * * * cd $REMOTE_PROJECT && $REMOTE_PROJECT/scripts/backup_database.sh 2>&1"
} | crontab -

echo "  ✓ Cron jobs installed:"
crontab -l | grep "job-agent"
REMOTE_CRON

echo ""
echo "=== Deployment Complete ==="
echo ""
echo "Next steps:"
echo "  1. Verify: ssh $VPS 'cd $REMOTE_PROJECT && source job-agent-venv/bin/activate && PYTHONPATH=. python3 src/jobs/weekly_unified_scraper.py --all-inboxes --email-limit 5 --companies-only'"
echo "  2. Check timezone: ssh $VPS 'timedatectl'"
echo "     (cron uses server timezone — if not ET, adjust cron schedule)"
echo "  3. Remove local cron jobs once verified: crontab -r"
echo "  4. Remove Windows Task Scheduler 'Start WSL' task"
