#!/bin/bash

# Grug's setup script for Codex

# Set PYTHONPATH so Grug can find his own modules
export PYTHONPATH=.

# Install Grug's tools (dependencies)
pip uninstall -y faiss-cpu numpy || true # Remove any existing faiss-cpu and numpy
pip install --no-cache-dir --force-reinstall faiss-cpu==1.7.4 "numpy<2" # Install specific, known-good versions
pip install -r requirements.txt -r requirements-dev.txt

# Ensure pip-audit is installed for security checks
pip install pip-audit

# Grug also likes clean words, so ensure ruff is available
pip install ruff

# Run Grug's basic health checks
python check_libs.py
python check_model.py
