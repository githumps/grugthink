# Production Migration Guide: v3.1.1 → v3.3.0

## Current Production Issues Identified

1. **Configuration Format**: Old JSON+.env format needs migration to YAML
2. **Discord OAuth Missing**: `DISCORD_CLIENT_ID` not configured
3. **Automatic Migration Failed**: Docker startup didn't trigger migration

## Step-by-Step Production Migration

### 1. Backup Current Configuration

```bash
# On your production server
cd /opt/grugthink

# Create backup directory
sudo mkdir -p backups/pre-3.3.0-migration
sudo cp bot_configs.json backups/pre-3.3.0-migration/
sudo cp .env backups/pre-3.3.0-migration/
sudo cp grugthink_config.yaml backups/pre-3.3.0-migration/ 2>/dev/null || true
sudo cp -r data/ backups/pre-3.3.0-migration/
```

### 2. Stop Current Services

```bash
# Stop the current containers
sudo docker-compose down

# Verify containers stopped
sudo docker ps | grep grugthink
```

### 3. Run Manual Migration

The automatic migration failed, so we'll run it manually:

```bash
# Run the migration script directly
sudo python3 migrate_configs.py

# Alternative: Run migration in Docker
sudo docker run --rm -v /opt/grugthink:/app python:3.11 bash -c "cd /app && python migrate_configs.py"
```

### 4. Fix Discord OAuth Configuration

The error `Discord OAuth not configured - missing DISCORD_CLIENT_ID` indicates missing OAuth settings. 

**Option A: Disable OAuth (for bot-only mode)**
Edit your `grugthink_config.yaml`:

```yaml
# Add or update the environment section
environment:
  # ... existing environment variables ...
  DISABLE_OAUTH: "true"  # Add this line
```

**Option B: Configure OAuth (for web dashboard access)**
If you want web dashboard authentication, add these to your `grugthink_config.yaml`:

```yaml
environment:
  # ... existing variables ...
  DISCORD_CLIENT_ID: "your_discord_client_id"
  DISCORD_CLIENT_SECRET: "your_discord_client_secret"
  DISCORD_REDIRECT_URI: "http://your-domain:8080/auth/callback"
```

### 5. Verify Configuration Structure

Your `grugthink_config.yaml` should look like this:

```yaml
# Discord tokens (referenced by bot configs)
discord_tokens:
  "1": "your_bot_token_1"
  "2": "your_bot_token_2"

# Bot configurations
bot_configs:
  bot-uuid-1:
    auto_start: true
    bot_id: "bot-uuid-1"
    name: "Your Bot Name"
    discord_token_id: "1"
    personality: "grug"  # or "big_rob", "adaptive"
    status: "stopped"
    template_id: "pure_grug"  # or "pure_big_rob", "evolution_bot"

# Environment variables
environment:
  LOG_LEVEL: "INFO"
  GRUGTHINK_MULTIBOT_MODE: "true"
  DISABLE_OAUTH: "true"  # Add this if you don't want OAuth
  # ... other environment variables from your .env file
```

### 6. Manual Migration Steps (if script fails)

If `migrate_configs.py` doesn't work, here's how to migrate manually:

```bash
# 1. Check your current bot_configs.json
cat bot_configs.json

# 2. Check your current .env
cat .env

# 3. Create new grugthink_config.yaml manually
sudo nano grugthink_config.yaml
```

Use this template and fill in your values:

```yaml
discord_tokens:
  "1": "YOUR_DISCORD_TOKEN_FROM_ENV"

bot_configs:
  your-bot-id:
    auto_start: true
    bot_id: "your-bot-id"
    name: "Your Bot Name"
    discord_token_id: "1"
    personality: "grug"  # Update based on your bot
    status: "stopped"
    template_id: "pure_grug"

environment:
  LOG_LEVEL: "INFO"
  GRUGTHINK_MULTIBOT_MODE: "true"
  DISABLE_OAUTH: "true"
  # Copy other variables from your .env file
```

### 7. Test Configuration

```bash
# Validate YAML syntax
python3 -c "import yaml; yaml.safe_load(open('grugthink_config.yaml'))"

# Check if migration created backup files
ls -la *.backup

# Start container to test
sudo docker-compose up -d
```

### 8. Verify Bot Startup

```bash
# Check container logs
sudo docker logs grugthink

# Look for successful bot startup messages
sudo docker logs grugthink | grep -E "(Bot.*started|GrugThink Container initialized|Loading bot configs)"

# Check if bots are connecting to Discord
sudo docker logs grugthink | grep -E "(Logged in|Ready|Connected)"
```

## Troubleshooting Common Issues

### Issue 1: Migration Script Not Found
```bash
# If migrate_configs.py is missing, you can migrate manually
# Follow the manual migration steps above
```

### Issue 2: Permission Issues
```bash
# Fix file permissions
sudo chown -R $USER:$USER /opt/grugthink
sudo chmod +r grugthink_config.yaml
```

### Issue 3: YAML Syntax Errors
```bash
# Validate YAML
python3 -c "import yaml; print('Valid YAML' if yaml.safe_load(open('grugthink_config.yaml')) else 'Invalid YAML')"

# Common issues:
# - Incorrect indentation (use spaces, not tabs)
# - Missing quotes around string values
# - Inconsistent key names
```

### Issue 4: Bot Won't Start
```bash
# Check specific error messages
sudo docker logs grugthink | tail -50

# Common fixes:
# - Ensure discord_token_id matches a key in discord_tokens
# - Set auto_start: true for bots that should start
# - Set status: "stopped" (not "running") to trigger startup
```

## Verification Checklist

After migration, verify:

- [ ] `grugthink_config.yaml` exists and has valid YAML syntax
- [ ] Backup files created (`.env.legacy.backup`, `bot_configs.json.migrated.backup`)
- [ ] Container starts without errors
- [ ] Bots connect to Discord successfully
- [ ] Web dashboard accessible (if OAuth configured)
- [ ] Bot responses work in Discord

## Quick Fix Commands

```bash
# Complete migration command sequence
cd /opt/grugthink
sudo docker-compose down
sudo python3 migrate_configs.py || echo "Manual migration needed"
echo "DISABLE_OAUTH: 'true'" | sudo tee -a grugthink_config.yaml
sudo docker-compose up -d
sudo docker logs grugthink
```

## Rollback Procedure (if needed)

```bash
# Stop new version
sudo docker-compose down

# Restore old configuration
sudo cp backups/pre-3.3.0-migration/bot_configs.json .
sudo cp backups/pre-3.3.0-migration/.env .
sudo rm grugthink_config.yaml

# Checkout previous version
sudo git checkout v3.1.1
sudo docker-compose up -d
```

## Success Indicators

You'll know the migration is successful when:

1. **Container starts cleanly**: No configuration errors in logs
2. **Bots connect**: See "Logged in as BotName" messages
3. **Web dashboard works**: Can access http://your-server:8080
4. **Discord responses**: Bots respond to mentions in Discord

Let me know which step you're having trouble with!