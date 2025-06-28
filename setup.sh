#!/bin/bash

# Grug's setup script for Codex

# Set PYTHONPATH so Grug can find his own modules
export PYTHONPATH=.

# Install Grug's tools (dependencies)
pip install -r requirements.txt -r requirements-dev.txt

# Ensure pip-audit is installed for security checks
pip install pip-audit

# Grug also likes clean words, so ensure ruff is available
pip install ruff
