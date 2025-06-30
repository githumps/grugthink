# Contributing Guide

Thank you for contributing to GrugThink! This guide will help you get started with development.

## Quick Setup

### Prerequisites
- **Python 3.11+**
- **Docker & Docker Compose**
- **Git**

### Development Environment

```bash
# Clone repository
git clone https://github.com/your-org/grugthink.git
cd grugthink

# Create Python virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Copy configuration
cp grugthink_config.yaml.example grugthink_config.yaml
# Edit with your Discord tokens and API keys
```

### Run Tests

```bash
# Run full test suite
PYTHONPATH=. pytest

# Run with coverage
PYTHONPATH=. pytest --cov=src --cov-report=html

# Run specific test module
PYTHONPATH=. pytest tests/test_bot.py
```

### Start Development Server

```bash
# Start with Docker (recommended)
docker-compose up -d

# Or run locally
python grugthink.py multi-bot

# Access dashboard at http://localhost:8080
```

## Development Workflow

### Code Quality

Before submitting changes, ensure code quality:

```bash
# Format and lint code
ruff check . --fix
ruff format .

# Run tests
PYTHONPATH=. pytest

# All checks must pass before committing
```

### Project Structure

```
grugthink/
├── src/grugthink/          # Main Python package
│   ├── bot.py              # Discord bot implementation
│   ├── bot_manager.py      # Multi-bot orchestration
│   ├── api_server.py       # Web API and dashboard
│   ├── personality_engine.py # Personality system
│   └── grug_db.py          # Database and embeddings
├── docker/                 # Docker configuration
├── tests/                  # Test suite
├── docs/                   # Documentation
└── web/                    # Web dashboard files
```

### Testing Guidelines

#### Test Categories
- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflows
- **API Tests**: REST endpoint validation

#### Writing Tests
- Focus on behavior, not implementation details
- Use meaningful test names: `test_bot_responds_to_mentions`
- Mock external dependencies (Discord API, ML models)
- Maintain 90%+ test coverage

#### Example Test Structure
```python
def test_personality_evolution():
    """Test that personality evolves after sufficient interactions."""
    engine = PersonalityEngine("test.db")
    personality = engine.get_personality("test_server")
    
    # Simulate interactions
    for _ in range(51):  # Trigger evolution at 50 interactions
        engine.record_interaction("test_server", "verification")
    
    evolved = engine.get_personality("test_server")
    assert evolved.evolution_stage > personality.evolution_stage
```

## Architecture Guidelines

### Multi-Bot System
- **BotManager**: Orchestrates multiple bot instances
- **APIServer**: Provides REST API and web dashboard
- **PersonalityEngine**: Manages server-specific personalities
- **GrugDB**: Handles knowledge storage and retrieval

### Best Practices

#### Code Style
- Follow PEP 8 conventions
- Use type hints for function signatures
- Write docstrings for public methods
- Keep functions focused and testable

#### Error Handling
- Log errors with structured logging
- Graceful degradation for optional features
- User-friendly error messages in web interface

#### Security
- Never log sensitive data (tokens, API keys)
- Validate all user inputs
- Use parameterized database queries
- Secure session management for web dashboard

### Adding New Features

#### Personality Templates
```python
# Add new personality in personality_engine.py
PERSONALITY_TEMPLATES["new_type"] = PersonalityTemplate(
    name="New Character",
    response_style="new_style",
    base_context="Character background...",
    speaking_patterns=["pattern1", "pattern2"],
    quirks=["quirk1", "quirk2"]
)
```

#### API Endpoints
```python
# Add endpoint in api_server.py
@self.app.get("/api/new-feature")
async def new_feature():
    """New API endpoint documentation."""
    return {"status": "success", "data": {}}
```

#### Discord Commands
```python
# Add command in bot.py
@app_commands.command(name="new-command")
async def new_command(self, interaction: discord.Interaction):
    """New Discord command."""
    await interaction.response.send_message("Response")
```

## Contribution Types

### Bug Reports
- Use GitHub issue templates
- Include reproduction steps
- Provide system information and logs
- Test with latest version

### Feature Requests
- Describe use case and benefits
- Consider impact on existing functionality
- Provide implementation suggestions if possible

### Pull Requests
1. **Fork** the repository
2. **Create** feature branch from `main`
3. **Implement** changes with tests
4. **Ensure** all tests pass and code is formatted
5. **Submit** pull request with clear description

#### Pull Request Checklist
- [ ] Code follows style guidelines
- [ ] Tests added for new functionality
- [ ] All existing tests pass
- [ ] Documentation updated if needed
- [ ] No breaking changes (or clearly documented)

## Documentation

### Updating Documentation
- Update relevant `.md` files for feature changes
- Include code examples for new APIs
- Update deployment guides for configuration changes
- Keep README.md current with major features

### Documentation Standards
- Use clear, concise language
- Include practical examples
- Maintain consistent formatting
- Link between related documents

## Community Guidelines

### Code of Conduct
- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Follow project maintainer decisions

### Communication
- Use GitHub issues for bug reports and feature requests
- Join discussions with constructive input
- Ask questions if implementation details are unclear

## Getting Help

- **GitHub Issues**: Bug reports and feature requests
- **Security Issues**: See [SECURITY.md](SECURITY.md)
- **Development Questions**: Create GitHub discussion

Thank you for contributing to GrugThink! 🤖