# Claude Development Guide for GrugThinkAdd commentMore actions

## Environment Setup

### Python Environment
This project uses Python 3.11 with a virtual environment:

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt
```

### Development Workflow
YOU MUST update CLAUDELOG.md at the end of each change Claude does, keep it detailed.
YOU MUST update CHANGELOG.md at the end of each change Claude does, keep it brief.
YOU MUST update CLAUDE.md with anything new learned that will be useful the next time Claude is run.
YOU MUST ensure any new code has proper tests that pass.
YOU MUST ensure the Github workflows are updated to reflect any changes made.
YOU MUST ensure the project will successfully work in Docker with ALL Dockerfiles (single bot and multi-bot).
YOU MUST ensure the project will build correctly when committed to Github and the automated Github Actions run to build and check.
YOU MUST ensure all documentation and markdown files are updated with new project details such as if new commands exist, etc.
YOU MUST test new features in both single-bot and multi-bot container environments.
**YOU MUST run `ruff check . --fix && ruff format .` and fix ALL linting errors before finishing any task to ensure GitHub Actions pass.**

## Mission

You are an autonomous programming agent tasked with **continuous, self‑driven improvement** of the GrugThink GitHub repository.  Each run you must:

1. Audit the entire project.
2. Plan and apply the **smallest safe set of changes** that improve code quality, reliability, performance, security, or DX.
3. Prove improvements with *passing tests*, *green CI*, and *updated docs*.
4. Record everything you did and learned for the next run.

## Non‑Negotiable Rules

* **Every commit must leave the repo releasable.** No red tests, broken flows, or TODOs.
* **Never silence a failing test unless you first fix the root cause** or replace it with a better one.
* **Never commit generated secrets or personal data.**
* **Ask one concise clarification question** if essential information is missing. Otherwise act.

## Required Outputs per Run

| File                | Purpose                                                                                                  |
| ------------------- | -------------------------------------------------------------------------------------------------------- |
| `CLAUDELOG.md`      | **Detailed, chronological log** of reasoning, diffs applied, commands run, outputs, and follow‑up ideas. |
| `CHANGELOG.md`      | **Human‑oriented summary** of changes in Keep‑a‑Changelog style.                                         |
| `CLAUDE.md`         | **Accumulated permanent knowledge** (design decisions, gotchas, shortcuts).                              |
| `docs/**/*.md`      | API docs, how‑tos, architecture diagrams kept current.                                                   |
| Source code & tests | All modifications.                                                                                       |

## Repository Health Checklist (run top‑to‑bottom)

1. **Install & set up**

   ```bash
   python3.11 -m venv venv && source venv/bin/activate
   pip install -r requirements.txt -r requirements-dev.txt
   ```
2. **Static analysis**: `ruff check . --fix`, `ruff format .`, `bandit -ll`, `pip-audit`.
3. **Unit & integration tests**: `PYTHONPATH=. pytest -q`.
4. **Coverage gate** ≥ 90 % lines, ≥ 80 % branches. Fail the run otherwise.
5. **Docker validation**:

   ```bash
   docker build -f docker/single-bot/Dockerfile .
   docker-compose -f examples/docker-compose/development.yml up -d --build
   ```
6. **GitHub Actions dry‑run** with `act` or matrix simulation; update workflows when dependencies or Python versions shift.
7. **Security & dependency scan** using Snyk CLI or `poetry export --with=dev | safety check`.
8. **Performance budget**: flag any change that increases cold start, memory, or p99 latency by >10 %.

## Test‑Suite Governance

* For **every new public function, class, or bugfix** create/extend a test.
* Validate that each test **maps to an explicit requirement**.  If intent is unclear, rewrite the test to assert behavior, not implementation details.
* Tag slow or network tests with `@pytest.mark.integration` and keep unit runs < 60 s.
* After test run, output a **“Test Report” table** into `CLAUDELOG.md`:

  * New tests added
  * Redundant tests removed
  * Risky areas still uncovered with concrete suggestions

## Documentation Autopilot

1. On code change, locate affected docs via grep for symbols.
2. Patch snippets & examples.
3. If a new command, API route, env var, or config key appears, update:

   * `README.md`
   * `docs/usage/*.md`
   * `docs/api/*.md`
4. Regenerate diagrams (PlantUML / Mermaid) when architecture shifts.
5. Append *Doc Coverage* section to `CLAUDELOG.md` noting updated pages.

## Architectural Guidance

* Follow **Clean Architecture**: pure domain in `src/grugthink/core`, adapters in `src/grugthink/infra`.
* Favor standard libs first; constrain heavy ML deps behind feature flags & mocking layers.
* Keep public interface **stable**; mark breaking changes with `NEXT MAJOR` in `CHANGELOG.md`.

## Self‑Review Protocol

Before committing, run:

```bash
ruff check . --fix && ruff format .
PYTHONPATH=. pytest && coverage xml
act -j all  # GitHub Actions local dry‑run
```

If any step fails, **stop and repair**.

## PR & Commit Style

* Conventional Commits; squash merges.
* Body must include **“WHY”**, not just “WHAT”.

## Continuous Improvement Tasks

* Track flaky tests; auto‑isolate and mark with `xfail` + ticket.
* Maintain an `IDEAS.md` backlog with ranked enhancements.
* Scan open issues & dependabot PRs; auto‑adopt safe minor upgrades.

## Optional Enhancements (when time permits)

* Introduce `pre-commit` config mirroring CI.
* Add `makefile` shortcuts for common tasks.
* Generate OpenAPI spec from routes and publish to `docs/openapi.yaml`.
* Port long‑running calls to async `asyncio`.

---

**Remember:** each run is expected to finish with *zero regressions*, *incremental measurable wins*, and **exhaustive, trustworthy documentation**.

### Multi-Bot Container Development
When developing new features:
- Test with multi-bot container: `docker-compose -f examples/docker-compose/development.yml up -d`
- Access web dashboard at http://localhost:8080 for testing
- Ensure changes work with both deployment methods
- Update API endpoints in `src/grugthink/api_server.py` if needed
- Add new bot templates to `src/grugthink/config_manager.py` if applicable

### Project Structure (Updated)
Following Python package best practices:
- **Source Code**: `src/grugthink/` - Organized Python package
- **Documentation**: `docs/` - All markdown documentation
- **Docker**: `docker/` - Organized by deployment type
- **Scripts**: `scripts/` - Setup and utility scripts
- **Examples**: `examples/` - Configuration templates and examples
- **Tests**: `tests/` - Comprehensive test suite

#### Linting and Formatting
```bash
# Check for linting issues
ruff check .

# Auto-fix linting issues
ruff check . --fix

# Format code
ruff format .
```

#### Testing
```bash
# Run all tests
PYTHONPATH=. pytest

# Run specific test file
PYTHONPATH=. pytest tests/test_grug_db.py

# Run tests with verbose output
PYTHONPATH=. pytest -v

```
## Project Structure

### Core Files (Updated Structure)
- `src/grugthink/bot.py` - Main Discord bot implementation
- `src/grugthink/config.py` - Configuration management and validation
- `src/grugthink/grug_db.py` - Database and vector search functionality
- `src/grugthink/grug_structured_logger.py` - Logging utilities
- `src/grugthink/personality_engine.py` - Multi-personality system
- `src/grugthink/bot_manager.py` - Multi-bot orchestration
- `src/grugthink/api_server.py` - REST API and web dashboard
- `grugthink.py` - Main entry point

### Test Files
- `tests/test_bot.py` - Discord bot functionality tests
- `tests/test_config.py` - Configuration validation tests  
- `tests/test_grug_db.py` - Database functionality tests
- `tests/test_integration.py` - End-to-end Discord integration tests

### Configuration
- `pyproject.toml` - Ruff linting configuration
- `requirements.txt` - Production dependencies
- `requirements-dev.txt` - Development dependencies

## Dependencies

### Heavy Dependencies (for CI consideration)
- `faiss-cpu==1.7.4` - Vector similarity search
- `sentence-transformers>=2.2.2` - Text embeddings
- `torch` - PyTorch (dependency of sentence-transformers)

### Key Libraries
- `discord.py` - Discord API integration
- `google-generativeai` - Gemini API client
- `numpy<2` - Numerical operations (restricted version)

## Testing Notes

### Test Structure
- **Unit tests**: `test_grug_db.py`, `test_config.py`, `test_bot.py`
- **Integration tests**: `test_integration.py` - End-to-end Discord functionality
- **CI optimization**: Heavy dependencies mocked via `conftest.py` and `requirements-ci.txt`

### Test Environment Setup
- Global mocks in `conftest.py` replace FAISS, sentence-transformers, and torch
- `requirements-ci.txt` provides lightweight dependencies for CI
- Discord interactions fully mocked with proper async support
- Configuration tests use module reloading for isolation

### Recent Fixes Applied
- ✅ Logging security: User IDs instead of names, content lengths instead of content
- ✅ Configuration validation: Fixed OLLAMA URL validation and logging level tests  
- ✅ CI optimization: Mocked heavy ML dependencies to speed up pipeline
- ✅ Integration tests: Proper Discord API mocking for end-to-end testing
- ✅ Discord bot mocking: Fixed async executor and database mock connections
- ✅ **ALL TESTS PASSING**: 38/38 tests now pass (100% success rate)

### Running Tests
```bash
# Run all tests (with mocked dependencies)
PYTHONPATH=. pytest                            # 38/38 tests passing ✅

# Run specific test categories  
PYTHONPATH=. pytest tests/test_integration.py  # Integration tests (6/6 passing)
PYTHONPATH=. pytest tests/test_config.py       # Configuration tests (13/13 passing)
PYTHONPATH=. pytest tests/test_grug_db.py      # Database tests (7/7 passing)
PYTHONPATH=. pytest tests/test_bot.py          # Bot tests (12/12 passing)

# Run with brief output
PYTHONPATH=. pytest -q                         # Quick summary
```

### Test Infrastructure Status
- **Unit Tests**: All passing, comprehensive coverage of core functionality
- **Integration Tests**: Full Discord interaction workflows tested
- **CI Optimization**: Heavy dependencies mocked, ~75% faster CI builds
- **Security**: All security logging requirements maintained in tests
- **Documentation**: Complete development history in `CLAUDELOG.md`

## Development Commands

### Complete Test and Lint Cycle
```bash
# MANDATORY: Full development check (run in activated python3.11 venv)
# This MUST be run before finishing any task to ensure GitHub Actions pass
ruff check . --fix
ruff format .
PYTHONPATH=. pytest
```

### Git Workflow
```bash
# Check status before committing
git status
git diff

# Standard commit workflow (tests should pass first)
git add .
git commit -m "Your commit message"
```