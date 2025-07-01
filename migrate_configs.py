#!/usr/bin/env python3
"""
Configuration Migration Script for GrugThink

Migrates from two-file system (bot_configs.json + grugthink_config.yaml)
to single-file system (grugthink_config.yaml only).
"""

import json
import os
import sys
from pathlib import Path

import yaml

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from grugthink.config_manager import ConfigManager
from grugthink.grug_structured_logger import get_logger

log = get_logger(__name__)


def main():
    """Perform the migration from JSON to YAML config."""

    print("🔄 GrugThink Configuration Migration")
    print("=" * 50)

    # Check if files exist
    json_file = "bot_configs.json"
    yaml_file = "grugthink_config.yaml"

    if not os.path.exists(json_file):
        print(f"❌ {json_file} not found. No migration needed.")
        return

    if not os.path.exists(yaml_file):
        print(f"❌ {yaml_file} not found. Please ensure your YAML config exists first.")
        return

    print("📁 Found configuration files:")
    print(f"   - {json_file}")
    print(f"   - {yaml_file}")

    # Load and display current configurations
    print("\n📊 Current Configuration Summary:")

    with open(json_file, "r") as f:
        json_configs = json.load(f)

    print(f"   JSON file contains {len(json_configs)} bot configuration(s):")
    for config in json_configs:
        print(f"     - {config['name']} (ID: {config['bot_id']})")
        print(f"       Token: {config['discord_token'][:20]}...")
        print(f"       Personality: {config.get('force_personality', 'adaptive')}")

    with open(yaml_file, "r") as f:
        yaml_config = yaml.safe_load(f)

    discord_tokens = yaml_config.get("api_keys", {}).get("discord", {}).get("tokens", [])
    print(f"   YAML file contains {len(discord_tokens)} Discord token(s):")
    for token_data in discord_tokens:
        print(f"     - {token_data['name']} (ID: {token_data['id']})")

    # Confirm migration
    print("\n🚀 Ready to migrate!")
    print("This will:")
    print(f"   1. Add bot configurations to {yaml_file}")
    print("   2. Reference existing Discord tokens by ID")
    print("   3. Add any missing Discord tokens to the YAML config")
    print(f"   4. Backup {json_file} to {json_file}.migrated.backup")
    print(f"   5. Remove the original {json_file}")

    response = input("\nProceed with migration? (y/N): ").strip().lower()
    if response != "y":
        print("❌ Migration cancelled.")
        return

    try:
        # Initialize ConfigManager
        config_manager = ConfigManager(yaml_file)

        # Perform migration
        print("\n🔄 Starting migration...")
        migration_map = config_manager.migrate_from_json(json_file)

        print("✅ Migration completed successfully!")
        print(f"   Migrated {len(migration_map)} bot configuration(s)")

        # Display migration summary
        print("\n📋 Migration Summary:")
        bot_configs = config_manager.list_bot_configs()
        for bot_id, config in bot_configs.items():
            print(f"   - {config['name']} (ID: {bot_id})")
            print(f"     Discord Token ID: {config['discord_token_id']}")
            print(f"     Template: {config['template_id']}")
            print(f"     Personality: {config.get('force_personality', 'adaptive')}")

        print("\n🎉 Migration Complete!")
        print(f"Your bot configurations are now stored in {yaml_file}")
        print(f"The old {json_file} has been backed up as {json_file}.migrated.backup")

        # Verify the backup was created
        if os.path.exists(f"{json_file}.migrated.backup"):
            print(f"✅ Backup verified: {json_file}.migrated.backup")
        else:
            print("⚠️  Backup not found - please check manually")

        print("\n🚀 Next Steps:")
        print("   1. Test your bot functionality")
        print(f"   2. If everything works, you can delete {json_file}.migrated.backup")
        print(f"   3. The system now uses only {yaml_file} for all configuration")

    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        log.error("Migration failed", extra={"error": str(e)})
        sys.exit(1)


if __name__ == "__main__":
    main()
