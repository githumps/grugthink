# Cleanup Failed v3.3.0 Release

## Issue
The v3.3.0 release failed because GitHub Actions was referencing the old Docker path `docker/multi-bot/Dockerfile.multibot` instead of the current `docker/Dockerfile`.

## Steps to Clean Up

### 1. Delete the Failed GitHub Release
1. Go to https://github.com/githumps/grugthink/releases
2. Find the v3.3.0 release
3. Click "Edit" 
4. Click "Delete this release"
5. Confirm deletion

### 2. Delete the Git Tag Locally and Remotely

```bash
# Delete the local tag
git tag -d v3.3.0

# Delete the remote tag
git push --delete origin v3.3.0

# Verify tag is gone
git tag -l | grep v3.3.0
git ls-remote --tags origin | grep v3.3.0
```

### 3. Verify Cleanup
```bash
# Check that tag is completely removed
git tag -l | grep v3.3.0  # Should return nothing
git ls-remote --tags origin | grep v3.3.0  # Should return nothing
```

## What Was Fixed
- Updated `.github/workflows/release.yml` to use correct Dockerfile path
- Changed `docker/multi-bot/Dockerfile.multibot` to `docker/Dockerfile`

## Next Steps
After cleanup, you can re-create the release:

```bash
# Re-create the tag
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

# Push the tag (this will trigger the fixed workflow)
git push origin v3.3.0
```

The GitHub Actions workflow will now build successfully with the correct Docker path.