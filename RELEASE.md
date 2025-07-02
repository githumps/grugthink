# GrugThink Release Process

This document outlines the complete process for creating and publishing a new GrugThink release.

## Pre-Release Checklist

1. **All tests pass**:
   ```bash
   ruff check . --fix && ruff format .
   PYTHONPATH=. pytest
   ```

2. **Version numbers updated**:
   - Update `src/grugthink/__init__.py` version
   - Move unreleased section in `docs/CHANGELOG.md` to new version

3. **Documentation updated**:
   - Update `docs/CLAUDELOG.md` with session notes
   - Update `CLAUDE.md` with key learnings
   - Create upgrade guide if needed (e.g., `UPGRADE_TO_X.X.X.md`)

## Release Process

### 1. Final Code Review
```bash
# Ensure working directory is clean
git status

# Run final tests and linting
ruff check . --fix && ruff format .
PYTHONPATH=. pytest -q

# Commit any final changes
git add .
git commit -m "Release preparation for vX.X.X

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"
```

### 2. Create Git Tag
```bash
# Create annotated tag with descriptive message
git tag -a v3.3.0 -m "Release v3.3.0: Enhanced Cross-Bot Interactions

Major Features:
- Cross-bot personality-aware conversations
- Enhanced insult system with 12 variations per personality
- Cross-bot knowledge sharing with rich context
- Dark mode for web interface
- Improved UI and bot management

Breaking Changes:
- Configuration migrated from JSON+.env to YAML (automatic migration included)

Upgrade from v3.1.1: See UPGRADE_TO_3.3.0.md for instructions"

# Verify tag was created
git tag -l | grep v3.3.0
git show v3.3.0
```

### 3. Push Release
```bash
# Push commits and tags to origin
git push origin main
git push origin v3.3.0

# Verify tag is on GitHub
git ls-remote --tags origin | grep v3.3.0
```

### 4. Create GitHub Release

1. **Go to GitHub Releases**: Navigate to `https://github.com/your-repo/grugthink/releases`

2. **Create New Release**:
   - **Tag version**: Select `v3.3.0`
   - **Release title**: `GrugThink v3.3.0: Enhanced Cross-Bot Interactions`
   - **Description**: Use the template below

3. **Release Description Template**:
```markdown
# 🚀 GrugThink v3.3.0: Enhanced Cross-Bot Interactions

## 🌟 What's New

### Cross-Bot Features
- **Personality-Aware Conversations**: Bots now understand each other's personalities and traits
- **Enhanced Insult System**: 12 unique variations per personality type (caveman, British working class, adaptive)
- **Rich Knowledge Sharing**: Bots access each other's memories with full personality context
- **Smart Interactions**: Bots can reference previous conversations and personality traits

### UI & Experience
- **Dark Mode**: Complete web interface dark mode with localStorage persistence  
- **Improved Bot Logs**: Individual bot log viewing with interactive modals
- **Enhanced Dashboard**: Better template management and bot monitoring

## 📋 Upgrade Instructions

**From v3.1.1**: This release includes automatic migration from JSON+.env to YAML configuration.

### Quick Upgrade (Docker)
```bash
git pull origin main
docker-compose down && docker-compose up -d --build
```

### Detailed Instructions
See [UPGRADE_TO_3.3.0.md](./UPGRADE_TO_3.3.0.md) for complete upgrade instructions, troubleshooting, and rollback procedures.

## 🔄 Migration & Compatibility

- ✅ **Automatic Migration**: JSON+.env configuration automatically converted to YAML
- ✅ **Backward Compatible**: All existing bot personalities and memories preserved
- ✅ **Safe Upgrade**: Old configuration files backed up automatically
- ✅ **Zero Downtime**: Upgrade process designed for minimal disruption

## 🐛 Bug Fixes

- Fixed cross-bot insult timing to prevent interrupting main responses
- Enhanced cross-bot knowledge system with personality information
- Improved web interface stability and responsiveness

## 🧪 Testing

All 43 tests pass with comprehensive coverage of new cross-bot features.

---

**Full Changelog**: [CHANGELOG.md](./docs/CHANGELOG.md)
```

### 5. Post-Release Verification

```bash
# Test the release
git checkout v3.3.0
docker-compose up -d --build

# Verify functionality
curl -s http://localhost:8080/api/health
docker logs grugthink | grep "GrugThink Container initialized"

# Return to main branch
git checkout main
```

## Release Naming Convention

Use semantic versioning with descriptive messages:

- **Major releases** (X.0.0): Breaking changes, new architecture
  ```bash
  git tag -a v4.0.0 -m "Release v4.0.0: Complete Architecture Overhaul"
  ```

- **Minor releases** (X.Y.0): New features, enhancements
  ```bash
  git tag -a v3.3.0 -m "Release v3.3.0: Enhanced Cross-Bot Interactions"
  ```

- **Patch releases** (X.Y.Z): Bug fixes, small improvements
  ```bash
  git tag -a v3.3.1 -m "Release v3.3.1: Fix cross-bot memory sharing bug"
  ```

## Hotfix Process

For urgent fixes:

1. **Create hotfix branch**:
   ```bash
   git checkout -b hotfix/v3.3.1 v3.3.0
   ```

2. **Apply fix and test**:
   ```bash
   # Make fixes
   git commit -m "Fix critical bug"
   ```

3. **Release hotfix**:
   ```bash
   git tag -a v3.3.1 -m "Release v3.3.1: Critical bug fix"
   git push origin hotfix/v3.3.1
   git push origin v3.3.1
   ```

4. **Merge back to main**:
   ```bash
   git checkout main
   git merge hotfix/v3.3.1
   git push origin main
   ```

## Release Artifacts

Each release should include:
- ✅ Git tag with descriptive message
- ✅ GitHub release with changelog
- ✅ Updated documentation
- ✅ Upgrade instructions (if needed)
- ✅ Docker images (if using registry)

## Emergency Release

For security or critical issues:
1. Follow hotfix process
2. Notify users immediately
3. Include security advisory in release notes
4. Update SECURITY.md if needed