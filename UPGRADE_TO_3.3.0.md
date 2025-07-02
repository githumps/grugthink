# GrugThink v3.3.0 Upgrade Guide

## Upgrading from v3.1.1 to v3.3.0

This guide provides step-by-step instructions for upgrading GrugThink from version 3.1.1 to 3.3.0. Version 3.3.0 includes major cross-bot interaction features, dark mode, enhanced personality systems, and configuration improvements.

## 🚀 What's New in v3.3.0

### Major Features
- **Cross-Bot Interactions**: Bots can now engage in intelligent conversations with each other
- **Enhanced Insult System**: 12 unique personality-driven insults per bot type
- **Cross-Bot Knowledge Sharing**: Bots understand each other's personalities and traits
- **Dark Mode**: Complete web interface dark mode with localStorage persistence
- **Improved UI**: Better bot logs, template management, and dashboard experience

### Breaking Changes from v3.1.1
- **Configuration System**: Unified YAML configuration (automated migration included)
- **Package Import**: Bot module now lazily loaded to prevent Discord token requirements during import

## 📋 Pre-Upgrade Checklist

Before upgrading, ensure you have:

1. **Backup your data**:
   ```bash
   # Backup your current configuration
   cp grugthink_config.json grugthink_config.json.backup
   cp .env .env.backup
   
   # Backup your database files
   cp -r data/ data_backup/
   ```

2. **Note your current setup**:
   - Document your current bot configurations
   - Note any custom environment variables
   - Record your Discord tokens and API keys

3. **Stop all running bots**:
   ```bash
   # If using Docker
   docker-compose down
   
   # If running directly
   # Stop any running GrugThink processes
   ```

## 🔄 Upgrade Process

### Option 1: Docker Upgrade (Recommended)

1. **Pull the new version**:
   ```bash
   git pull origin main
   # or
   git checkout v3.3.0
   ```

2. **Rebuild containers**:
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

3. **Verify upgrade**:
   ```bash
   docker logs grugthink | grep "GrugThink Container initialized"
   ```

### Option 2: Direct Python Upgrade

1. **Update the codebase**:
   ```bash
   git pull origin main
   # or
   git checkout v3.3.0
   ```

2. **Update dependencies**:
   ```bash
   pip install -r requirements.txt -r requirements-dev.txt
   ```

3. **Start the application**:
   ```bash
   python grugthink.py multi-bot --api-port 8080
   ```

## 🔧 Automatic Migration

GrugThink v3.3.0 includes **automatic migration** that will:

1. **Convert your configuration** from JSON+.env to unified YAML
2. **Preserve all bot settings** including personalities and tokens
3. **Create backup files** of your old configuration
4. **Update database paths** for better bot isolation

### What happens during migration:

```
✅ Old files found: grugthink_config.json, .env
✅ Converting to grugthink_config.yaml
✅ Backing up old files: grugthink_config.json.migrated.backup, .env.legacy.backup
✅ Bot configurations preserved
✅ Discord tokens migrated securely
✅ Environment variables moved to YAML
```

## 🆕 New Features Setup

### 1. Cross-Bot Interactions

No setup required! Cross-bot interactions work automatically when you have multiple bots in the same Discord channel.

**Example interactions**:
```
User: "big rob could beat grug in a soccer match"
Big Rob: "TRUE - Grug's a caveman, innit? Simple as, he'd be lost with a football"
Grug: "Big Rob weak. Grug strongest!" (auto-insult after 2 seconds)
```

### 2. Dark Mode

Access via the web dashboard:
1. Open http://localhost:8080
2. Click the 🌙/☀️ toggle in the top navigation
3. Preference is saved automatically

### 3. Enhanced Bot Templates

New bot creation now includes:
- Expanded personality options
- Better trait configuration
- Enhanced API integration settings

## 🔍 Verification Steps

After upgrading, verify everything works:

1. **Check web dashboard**: http://localhost:8080
2. **Verify bot status**: All bots should show "Running" status
3. **Test Discord interactions**: Mention a bot in Discord
4. **Test cross-bot features**: Have multiple bots in same channel
5. **Check dark mode**: Toggle between light/dark themes

## 🐛 Troubleshooting

### Configuration Issues

If you see configuration errors:

```bash
# Check if migration completed
ls -la | grep -E "(grugthink_config\\.yaml|.*\\.backup)"

# Verify YAML syntax
python -c "import yaml; yaml.safe_load(open('grugthink_config.yaml'))"
```

### Bot Connection Issues

If bots won't connect:

1. **Check Discord tokens** in `grugthink_config.yaml`
2. **Verify bot permissions** in Discord
3. **Check logs** for specific error messages:
   ```bash
   docker logs grugthink | grep -i error
   ```

### Cross-Bot Features Not Working

If cross-bot interactions aren't working:

1. **Ensure multiple bots** are in the same Discord channel
2. **Check bot-specific logs** via web dashboard
3. **Verify bot personalities** are properly configured

## 🆘 Rollback Procedure

If you need to rollback to v3.1.1:

1. **Stop current version**:
   ```bash
   docker-compose down
   ```

2. **Restore backups**:
   ```bash
   cp grugthink_config.json.backup grugthink_config.json
   cp .env.backup .env
   rm grugthink_config.yaml  # Remove new config
   ```

3. **Checkout previous version**:
   ```bash
   git checkout v3.1.1
   docker-compose up -d --build
   ```

## 📞 Support

If you encounter issues during upgrade:

1. **Check the logs** for specific error messages
2. **Review the troubleshooting section** above
3. **Consult the documentation** in the repository
4. **File an issue** with detailed error information

## 🎉 Enjoy v3.3.0!

Your bots can now:
- Have intelligent conversations with each other
- Use personality-driven insults and responses
- Access each other's knowledge and traits
- Provide a better user experience with dark mode

The upgrade maintains full compatibility with your existing bot personalities and learned memories while adding these powerful new features.