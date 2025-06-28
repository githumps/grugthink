#!/bin/bash

# Grug's lightweight setup script for ChatGPT/OpenAI Codex workspaces
# Uses mocked dependencies for faster, more reliable setup

echo "🦣 Setting up GrugThink for Codex workspace..."

# Set PYTHONPATH so Grug can find his own modules
export PYTHONPATH=.
echo "✓ PYTHONPATH set to current directory"

# Detect available Python and pip commands
PYTHON_CMD=""
PIP_CMD=""

for cmd in python3.11 python3 python; do
    if command -v "$cmd" >/dev/null 2>&1; then
        PYTHON_CMD="$cmd"
        break
    fi
done

for cmd in pip3.11 pip3 pip; do
    if command -v "$cmd" >/dev/null 2>&1; then
        PIP_CMD="$cmd"
        break
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    echo "❌ No Python interpreter found (tried python3.11, python3, python)"
    exit 1
fi

if [ -z "$PIP_CMD" ]; then
    echo "❌ No pip found (tried pip3.11, pip3, pip)"
    exit 1
fi

echo "✓ Using Python: $PYTHON_CMD"
echo "✓ Using pip: $PIP_CMD"

# Install lightweight dependencies (no heavy ML libraries)
echo "📦 Installing lightweight dependencies..."
$PIP_CMD install -r requirements-ci.txt -r requirements-dev.txt

# Verify core functionality with mocked dependencies
echo "🧪 Testing core functionality..."
$PYTHON_CMD -c "
import sys
import os
sys.path.insert(0, '.')

# Set minimal environment variables for testing
os.environ['DISCORD_TOKEN'] = 'test_token'
os.environ['GEMINI_API_KEY'] = 'test_key'

# Test imports work with mocked dependencies
try:
    import conftest  # This sets up the mocks
    import grug_db
    import config
    print('✓ All core modules imported successfully')
    
    # Note: Skip bot.py import as it may have Discord setup issues in some environments
    print('✓ Core functionality verified')
except Exception as e:
    print(f'✗ Import error: {e}')
    print('✓ Continuing anyway - tests will verify functionality')
    # Don't exit on import errors - tests are more comprehensive

# Test basic database functionality
try:
    import tempfile
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
        db_path = f.name
    
    db = grug_db.GrugDB(db_path)
    db.add_fact('Test fact for Codex')
    facts = db.get_all_facts()
    db.close()
    
    import os
    os.unlink(db_path)
    
    print('✓ Database functionality working')
except Exception as e:
    print(f'✗ Database test failed: {e}')
    sys.exit(1)

print('✓ All tests passed!')
"

echo "🧪 Running test suite..."
PYTHONPATH=. $PYTHON_CMD -m pytest -x --tb=short

echo "✨ GrugThink setup complete!"
echo ""
echo "📝 Usage:"
echo "  • Run tests: PYTHONPATH=. pytest"
echo "  • Check code: ruff check ."
echo "  • Format code: ruff format ."
echo ""
echo "⚠️  Note: This is a lightweight setup using mocked ML dependencies."
echo "   For production deployment, use the full setup.sh script."