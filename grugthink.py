#!/usr/bin/env python3
"""
GrugThink - Adaptable Discord Personality Engine

Main entry point for the GrugThink bot system.
Supports both single bot and multi-bot container deployments.
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))


def main():
    """Main entry point that delegates to appropriate module."""
    print(f"[DEBUG] grugthink.py main() called with args: {sys.argv}")
    if len(sys.argv) > 1 and sys.argv[1] == "multi-bot":
        # Multi-bot container mode
        import asyncio

        from grugthink.main import main as multi_main

        sys.argv.pop(1)  # Remove 'multi-bot' argument

        # Set up proper event loop policy for different platforms
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        asyncio.run(multi_main())
    else:
        # Single bot mode (default)
        from grugthink.bot import main as bot_main

        bot_main()


if __name__ == "__main__":
    main()
