# Setup Guide

## Prerequisites

1. **Hostinger VPS** (or similar) with:
   - 1 CPU, 2GB RAM minimum
   - Ubuntu 20.04+ or similar Linux distribution
   - SSH access

2. **Dedicated Gmail Account** for job alerts:
   - Create a new Gmail account specifically for this project
   - Enable 2-factor authentication
   - Generate an app-specific password for IMAP access

3. **Notification Services**:
   - Twilio account for SMS notifications (optional)
   - SMTP credentials for email notifications

## Installation Steps

### 1. VPS Setup

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker and Docker Compose
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. n8n Installation

```bash
# Create n8n directory
mkdir ~/n8n-data
cd ~/n8n-data

# Create docker-compose.yml (see docker-compose.yml in this directory)
# Start n8n
docker-compose up -d

# Access n8n at http://your-vps-ip:5678
```

### 3. Configuration

1. **Email Setup**:
   - Copy `config/email-settings.json.example` to `config/email-settings.json`
   - Fill in Gmail credentials and app password
   - Configure job alert sources

2. **Keywords Setup**:
   - Edit `config/filter-keywords.json`
   - Customize include/exclude keywords for your target roles

3. **Notifications Setup**:
   - Copy `config/notification-settings.json.example` to `config/notification-settings.json`
   - Configure SMS (Twilio) and email settings

### 4. Workflow Import

1. Access n8n web interface
2. Import workflows from `n8n-workflows/` directory
3. Configure credentials in n8n for:
   - Gmail IMAP
   - Twilio (if using SMS)
   - SMTP (for email notifications)

### 5. Testing

1. Send a test job alert email to your configured Gmail account
2. Verify the workflow processes it correctly
3. Confirm notifications are sent via your configured channels

## Security Notes

- Use app-specific passwords for Gmail, not your main password
- Store sensitive credentials in n8n's credential store, not in config files
- Consider using environment variables for production deployment
- Regularly backup your n8n data and workflows

## Troubleshooting

See `docs/setup/troubleshooting.md` for common issues and solutions.
