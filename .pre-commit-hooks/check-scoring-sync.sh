#!/bin/bash
# Pre-commit hook to check if scoring changes are accompanied by email template updates

# Colors for output
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# Get list of staged files
STAGED_FILES=$(git diff --cached --name-only)

# Check if scoring-related files are staged
SCORING_CHANGED=$(echo "$STAGED_FILES" | grep -E '(src/agents/job_scorer.py|config/filter-keywords.json)' || true)
EMAIL_CHANGED=$(echo "$STAGED_FILES" | grep 'src/send_digest_to_wes.py' || true)

# If scoring files changed but email template didn't
if [ -n "$SCORING_CHANGED" ] && [ -z "$EMAIL_CHANGED" ]; then
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${YELLOW}⚠️  WARNING: Scoring System Changes Detected${NC}"
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "You changed: ${GREEN}$SCORING_CHANGED${NC}"
    echo ""
    echo -e "${YELLOW}Did you update the email template?${NC}"
    echo -e "  📝 File: ${GREEN}src/send_digest_to_wes.py${NC} (lines 222-238)"
    echo ""
    echo -e "${YELLOW}Full checklist:${NC}"
    echo -e "  📋 ${GREEN}docs/development/SCORING_UPDATE_CHECKLIST.md${NC}"
    echo ""
    echo -e "${YELLOW}Other files to consider:${NC}"
    echo "  - CLAUDE.md (if categories/ranges changed)"
    echo "  - tests/unit/test_job_scorer.py"
    echo ""
    echo -e "${YELLOW}To proceed anyway:${NC}"
    echo "  Continue committing - this is just a reminder, not a blocker"
    echo ""
    echo -e "${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

    # Exit 0 to allow commit (it's a warning, not an error)
    exit 0
fi

# If both changed, show success
if [ -n "$SCORING_CHANGED" ] && [ -n "$EMAIL_CHANGED" ]; then
    echo -e "${GREEN}✅ Scoring changes detected - email template also updated${NC}"
fi

exit 0
