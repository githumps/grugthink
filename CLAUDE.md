# Claude Development Guide for GrugThink

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

### Development Workflow - MANDATORY RULES

**CRITICAL: These rules are NON-NEGOTIABLE and must be followed for EVERY task:**

1. **ALWAYS run linting FIRST**: `ruff check . --fix && ruff format .` at the start of any task
2. **Update documentation at END of each task** (not during, at the END):
   - Update `docs/CLAUDELOG.md` with detailed changes made
   - Update `docs/CHANGELOG.md` with brief summary
   - Update `CLAUDE.md` with new learnings for future sessions
3. **Ensure tests pass**: All new code must have tests that pass
4. **Verify Docker compatibility**: Changes must work in Docker environment, such as web components being copied
5. **Update all documentation**: API docs, README, etc. for any new features
6. **Run final linting check**: `ruff check . --fix && ruff format .` before task completion

**WORKFLOW ENFORCEMENT:**
- Start task → Run linting → Make changes → End task → Update docs → Final linting
- If ANY rule is missed, the task is INCOMPLETE
- Documentation updates are MANDATORY, not optional

### Deep Codebase Review Guidelines

When conducting comprehensive codebase reviews, focus on these critical areas:

1. **Security Issues (Critical Priority)**:
   - Exposed secrets or tokens in configuration files
   - Weak session secrets or authentication mechanisms
   - Overly permissive CORS configurations
   - Missing input validation on API endpoints

2. **API Consistency Issues**:
   - Field naming inconsistencies (e.g., personality vs force_personality)
   - Inconsistent error response formats across endpoints
   - Missing validation patterns on request models

3. **Code Quality Issues**:
   - Missing type hints throughout codebase
   - Duplicate validation logic in multiple modules  
   - Inefficient database query patterns (N+1 queries)
   - Inconsistent error handling patterns

4. **Configuration Issues**:
   - Overly restrictive validation patterns
   - Deprecated fields still in active use
   - Environment variable validation inconsistencies

**Review Process**: Always provide specific file locations, line numbers, and actionable recommendations for each identified issue.

## Project Structure

### Core Files
- `src/grugthink/bot.py` - Main Discord bot implementation
- `src/grugthink/config.py` - Configuration management and validation
- `src/grugthink/grug_db.py` - Database and vector search functionality
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

### Test Environment Setup
- Global mocks in `conftest.py` replace FAISS, sentence-transformers, and torch
- `requirements-ci.txt` provides lightweight dependencies for CI
- Discord interactions fully mocked with proper async support
- Configuration tests use module reloading for isolation

### Running Tests
```bash
# Run all tests
PYTHONPATH=. pytest

# Run with coverage
PYTHONPATH=. pytest --cov=src --cov-report=html

# Run specific test
PYTHONPATH=. pytest tests/test_bot.py -v
```

## Development Commands

### Complete Test and Lint Cycle
```bash
# MANDATORY: Full development check (run in activated python3.11 venv)
# This MUST be run before finishing any task to ensure GitHub Actions pass
ruff check . --fix
ruff format .
PYTHONPATH=. pytest
```

### Docker Development
```bash
# Build and run container
docker-compose up -d --build

# View logs
docker logs -f grugthink

# Access web dashboard
open http://localhost:8080
```

## Critical Learnings - Bot Isolation & Discord Limits

### Database Isolation for Multi-Instance Bots
**Problem**: Multiple Discord bot instances sharing the same database files cause memory contamination.

**Solution**: Create unique database paths based on Discord token hash:
```python
def _get_unique_db_path():
    if DISCORD_TOKEN:
        import hashlib
        token_hash = hashlib.sha256(DISCORD_TOKEN.encode()).hexdigest()[:12]
        return os.path.join(DATA_DIR, f"grug_lore_{token_hash}.db")
    else:
        return os.path.join(DATA_DIR, "grug_lore.db")
```

### Discord Embed Field Limits
**Critical**: Discord embed fields have a 1024 character limit that must be respected.

**Implementation**: Always count characters when building embed fields:
```python
MAX_FIELD_LENGTH = 950  # Leave margin for formatting
current_length = 0
for item in items:
    item_text = f"{i+1}. {item}"
    if current_length + len(item_text) + 1 > MAX_FIELD_LENGTH:
        break
    current_length += len(item_text) + 1
```

### Bot Deletion Bug Fix
**Critical**: The `delete_bot` function must be async and properly await `stop_bot()`.

**Solution**:
```python
async def delete_bot(self, bot_id: str) -> bool:
    if self.bots[bot_id].config.status == "running":
        await self.stop_bot(bot_id)  # Must await async function
```

### Key Learnings from Recent Session (2025-07-01)

#### Configuration System Architecture
- **Single-file approach works best**: Eliminated .env file completely, unified everything in grugthink_config.yaml
- **Token references prevent duplication**: Use discord_token_id references instead of storing actual tokens in bot configs
- **Migration scripts essential**: Always provide automated migration when changing config structure
- **Environment variable centralization**: Store all env vars in YAML `environment:` section

#### Bot Manager Token Resolution
- **Critical fix pattern**: When accessing Discord tokens, always get from bot environment, not directly from config
- **Error was**: `instance.task = asyncio.create_task(client.start(config.discord_token))`
- **Fix was**: Get token from `bot_env.get("DISCORD_TOKEN")` first, then pass to start()
- **Root cause**: Config stores token_id reference, actual token is resolved via ConfigManager

#### Personality System Design
- **YAML configuration works excellently**: Complex nested personality configs are maintainable in YAML
- **Separation of concerns**: Keep personality data separate from Python code for easier customization
- **Template + Instance pattern**: Bot templates reference personality configs, bot instances use templates
- **API endpoints essential**: CRUD operations for personalities enable dynamic customization

#### WebSocket Connection Stability
- **Heartbeat mechanism crucial**: Implement 30-second heartbeat to prevent connection drops
- **Authentication can cause issues**: Temporarily disable for debugging, re-enable once stable
- **Error handling important**: Properly handle WebSocketDisconnect and clean up connections
- **Logging helps debugging**: Track connection count and connection events

#### Development Workflow Enforcement
- **Documentation updates are NOT optional**: Must be done at end of every task
- **Linting must be run first AND last**: Start with clean code, end with clean code
- **CLAUDE.md rules must be enforced**: User compliance depends on strict adherence
- **Task completion criteria**: Task is incomplete if documentation not updated

#### File Structure Simplification
- **Fewer files = less confusion**: Single config file much easier to manage
- **Migration = user confidence**: Provide clear migration path for breaking changes
- **Backup important files**: Always backup before deletion (.env -> .env.legacy.backup)
- **Update documentation immediately**: All setup guides must reflect new structure

### Testing Configuration Changes
When modifying `config.py`, ensure tests account for new behavior:
- Set `GRUGTHINK_MULTIBOT_MODE=true` to skip Discord token validation in tests
- Mock environment variables appropriately for default value testing
- Update assertions to match new configuration patterns

## Critical Bug Fixes - Discord Bot Logging & UI Integration (2025-07-01)

### Bot Logs Not Showing in Individual Bot View
**Problem**: Individual bot logs in web UI showed "No logs available" despite Discord conversations happening.

**Root Cause**: Discord bot interactions weren't being logged with `bot_id` field, so API couldn't filter logs per bot.

**Solution**: Add `bot_id` to ALL Discord bot log entries:
```python
def get_bot_id(self):
    """Get the bot ID for logging purposes."""
    return getattr(self.bot_instance.config, 'bot_id', 'unknown-bot')

# Add to all log statements:
log.info(
    "Auto-verification completed", 
    extra={
        "bot_id": self.get_bot_id(),  # THIS IS CRITICAL
        "user_id": str(message.author.id),
        # ... other fields
    }
)
```

**Key Learning**: Multi-bot container requires `bot_id` in every log entry for proper filtering.

### Google Search Disabled Warning
**Problem**: Bot showed "Google Search is disabled" warning despite API keys being configured.

**Root Cause**: Template configuration had `default_google_search: false` in pure_grug template.

**Solution**: Change template config:
```yaml
bot_templates:
  pure_grug:
    default_google_search: true  # Changed from false
```

**Key Learning**: Template settings override global API key availability - both must be enabled.

### Template Editing UI Missing
**Problem**: No way to edit bot templates through web interface.

**Solution**: Implement complete template CRUD in `web/static/js/dashboard.js`:
- Add Edit/Delete buttons to template cards
- Create Bootstrap modal for template editing
- Implement `editTemplate()`, `saveTemplate()`, `deleteTemplate()` methods
- Form validation for personality, embedder, API keys, Google Search settings

**Key Learning**: Frontend template management requires:
1. Modal UI for complex forms
2. API integration for CRUD operations  
3. Form validation matching backend Pydantic models
4. Proper error handling and user feedback

### Docker Web File Synchronization
**Problem**: Changes to web files weren't reflected in Docker container.

**Root Cause**: Docker build copies from `docker/web/` but development happens in `web/`.

**Solution**: Always run `cp -r web/* docker/web/` before Docker rebuild.

**Key Learning**: Web development workflow requires:
1. Edit files in `web/` directory
2. Copy to `docker/web/` before container rebuild
3. Rebuild container to see changes
4. This must be done for EVERY frontend change

### Multi-Bot Logging Architecture
**Critical Pattern**: In multi-bot containers, every log entry MUST include identifying information:

```python
# Required fields for multi-bot logging:
extra = {
    "bot_id": self.get_bot_id(),        # Which bot instance
    "user_id": str(user.id),            # Which Discord user  
    "server_id": str(guild.id),         # Which Discord server
    # ... other contextual data
}
```

**API Filtering**: Bot logs API filters using `bot_id`:
```python
bot_logs = [log for log in RECENT_LOGS if log.get("bot_id") == bot_id]
```

### Line Length Linting Fixes
**Pattern**: When log statements exceed 120 characters, format as multi-line:
```python
# Instead of:
log.error("Error", extra={"bot_id": self.get_bot_id(), "error": str(exc), "user_id": str(user.id), "server_id": server_id})

# Use:
log.error(
    "Error",
    extra={
        "bot_id": self.get_bot_id(),
        "error": str(exc), 
        "user_id": str(user.id),
        "server_id": server_id,
    },
)
```

### Testing Individual Bot Logs
**Verification Process**:
1. Interact with bot on Discord (mention bot name with statement)
2. Check bot logs in web UI (Bot Instances → View Logs button)
3. Should see Discord interaction with bot_id, user_id, server_id
4. If "No logs available" → bot_id not being added to log entries

**Debug Commands**:
```bash
# Check if logs have bot_id field:
docker logs grugthink | grep "bot_id"

# Test individual bot logs API:
curl -s http://localhost:8080/api/bots/grug-main/logs
```

## Advanced UI Issues & Solutions (2025-07-01 Session 2)

### Modal Overlay Stacking Issue (Refresh Button Getting Darker)
**Problem**: Each click of "Refresh" in bot logs modal made page darker due to modal overlay accumulation.

**Root Cause**: Creating new Bootstrap modal instances without reusing existing ones.

**Solution**: Always reuse existing modal instances:
```javascript
// WRONG - creates new instance every time:
const bootstrapModal = new bootstrap.Modal(modal);
bootstrapModal.show();

// CORRECT - reuse existing instance:
let bootstrapModal = bootstrap.Modal.getInstance(modal);
if (!bootstrapModal) {
    bootstrapModal = new bootstrap.Modal(modal);
}
bootstrapModal.show();
```

**Key Learning**: Bootstrap modals must be reused, not recreated, to prevent overlay stacking.

### Comprehensive Template Editing UI
**Problem**: Template editing only showed basic fields, missing advanced personality configuration.

**Solution**: Expanded template editing form with organized sections:
1. **Basic Information**: Name, Description
2. **Personality Configuration**: Base personality selection
3. **AI & ML Features**: Embedder settings with descriptions
4. **API Integrations**: Gemini, Ollama, Google Search with help text
5. **Advanced Configuration**: Custom environment variables (JSON), log levels

**Implementation Patterns**:
```javascript
// JSON validation for custom environment variables:
let customEnv = {};
try {
    const customEnvText = document.getElementById('edit-template-custom-env').value.trim();
    if (customEnvText) {
        customEnv = JSON.parse(customEnvText);
    }
} catch (error) {
    this.showAlert('Invalid JSON in Custom Environment Variables', 'danger');
    return;
}

// Form sections with Bootstrap styling:
<h6 class="text-primary mb-3 mt-4">Section Title</h6>
<div class="form-text">Helpful description for users</div>
```

**Key Learning**: Complex forms need organized sections, validation, and helpful descriptions for better UX.

### Bot Logging Troubleshooting Process
**Issue**: Bot logs showed "No logs available" despite bot interactions happening.

**Root Cause Discovered**: StructuredLogger JSON formatting incompatible with InMemoryLogHandler extraction.

**The Problem**: 
- Bot uses `StructuredLogger` which converts log messages to JSON format
- `InMemoryLogHandler` expected `bot_id` in `record.extra`, but it was embedded in JSON message
- Handler couldn't extract `bot_id` from JSON-formatted messages

**Solution**: Enhanced InMemoryLogHandler to parse JSON messages:
```python
def emit(self, record: logging.LogRecord) -> None:
    message = record.getMessage()
    
    # Try to parse JSON message from StructuredLogger
    structured_data = None
    try:
        structured_data = json.loads(message)
    except (json.JSONDecodeError, TypeError):
        # Not a JSON message, use as-is
        pass
    
    # Extract message and other data
    if structured_data and isinstance(structured_data, dict):
        actual_message = structured_data.get("message", message)
        bot_id = structured_data.get("bot_id")
    else:
        actual_message = message
        bot_id = None
    
    # Extract bot_id from various sources (JSON, record attributes, extra)
    if bot_id:
        log_entry["bot_id"] = bot_id
    # ... other extraction methods
```

**Additional Issues Found**:
- Bot status was `stopped` in config, preventing Discord connection
- Changed `status: stopped` to `status: running` in `grugthink_config.yaml`

**Diagnostic Process**:
1. Check if bot is actually connecting to Discord: `docker logs grugthink | grep -i "discord\|logged\|ready"`
2. Verify logging infrastructure: Look for InMemoryLogHandler setup
3. Check authentication: API endpoints require authentication for access
4. Test log capture: Verify RECENT_LOGS is being populated
5. **NEW**: Check if StructuredLogger messages are being parsed correctly

**Common Causes**:
- Bot not actually started/connected to Discord
- Missing `bot_id` in log entries (fixed in previous session)
- **StructuredLogger JSON format not compatible with log handler (FIXED)**
- Authentication issues preventing API access
- Logging handler not attached properly
- **Bot status set to "stopped" in configuration**

**Debug Pattern**:
```bash
# Check Discord connection status:
docker logs grugthink | grep -v "GET\|POST\|WebSocket" | tail -20

# Look for actual bot interactions:
docker logs grugthink | grep -E "(Auto-verification|bot_id|interaction)"

# Check bot configuration status:
grep -A5 "bot_configs:" grugthink_config.yaml
```

**Key Learning**: When using StructuredLogger with custom log handlers, ensure handlers can parse the JSON-formatted messages to extract metadata like `bot_id`.

### Frontend-Backend Template Field Synchronization
**Critical Pattern**: When adding new template fields, must update both:

1. **Backend API** (if needed): Template validation/storage
2. **Frontend Form**: Add input elements with proper IDs
3. **Form Population**: `document.getElementById().value = template.field`
4. **Form Submission**: Include field in `templateData` object
5. **Validation**: Client-side validation before submission

**Field Naming Convention**:
- Form IDs: `edit-template-{field-name}`
- Template object: `template.{field_name}`
- HTML elements: Consistent with backend field names

### Web File Synchronization Workflow
**MANDATORY STEP**: Always copy web files to Docker directory:
```bash
cp -r web/* docker/web/
docker-compose down && docker-compose up -d --build
```

**Why This Matters**:
- Development happens in `web/` directory
- Docker builds from `docker/web/` directory  
- Frontend changes are invisible until files are synchronized
- Must be done for EVERY frontend modification

### Bootstrap Form UX Best Practices
**Learned Patterns**:
1. **Section Headers**: Use `<h6 class="text-primary mb-3 mt-4">` for form sections
2. **Help Text**: Add `<div class="form-text">` for field descriptions
3. **Monospace Fields**: Use `font-monospace` class for JSON/code inputs
4. **Validation Feedback**: Show clear error messages for invalid input
5. **Progressive Enhancement**: Start with basic fields, add advanced ones with clear labeling

**Form Organization**:
- Group related fields under clear headings
- Provide context for complex settings
- Use checkboxes with descriptive labels
- Include examples in placeholders for complex fields

## Critical Bug Fixes - Bot Status & Multi-Bot Conversations (2025-07-01 Session 3)

### Bot Auto-Start Issue Resolution
**Problem**: Bots marked as `status: running` in config weren't actually connecting to Discord.

**Root Cause**: Bot manager's `start_bot()` method has early return when `config.status == "running"`:
```python
if config.status == "running":
    log.warning("Bot already running", extra={"bot_id": bot_id})
    return True
```

**Solution**: Change bot status from `running` to `stopped` in configuration to trigger actual startup:
```yaml
bot_configs:
  grug-main:
    status: stopped  # Changed from "running"
```

**Key Learning**: Configuration status must reflect actual runtime state, not desired state. Use `stopped` for auto-start.

### Bot Personality Display Fix
**Problem**: Web UI showed "adaptive" instead of "big_rob" for bots using `pure_big_rob` template.

**Root Cause**: Bot status lookup only checked explicit `personality` field, ignored template-derived personality.

**Solution**: Enhanced `get_bot_status()` in `bot_manager.py:254-263`:
```python
# If no explicit personality, try to get it from the template
if not actual_personality and self.config_manager:
    template_id = getattr(config, "template_id", "evolution_bot") 
    template = self.config_manager.get_template(template_id)
    if template:
        template_dict = template if isinstance(template, dict) else template.__dict__
        actual_personality = template_dict.get("personality")
```

**Key Learning**: Always fall back to template personality when bot config doesn't specify explicit personality.

### Multi-Bot Discord Conversations
**Problem**: Only one bot could respond per channel, no bot-to-bot interactions.

**Root Cause**: Message filtering blocked all bot messages except "Markov" bots:
```python
if message.author.bot:
    if "markov" not in message.author.name.lower():
        return
```

**Solution**: Enhanced bot message filtering in `bot.py:454-465`:
```python
if message.author.bot:
    # Allow interaction with Markov bots
    is_markov_bot = "markov" in message.author.name.lower()
    # Allow interaction with other GrugThink bots (check if message mentions this bot)
    is_mentioning_this_bot = self.client.user and (
        f"<@{self.client.user.id}>" in message.content or
        f"<@!{self.client.user.id}>" in message.content
    )
    # Allow if it's a Markov bot, or if another bot is mentioning this specific bot
    if not (is_markov_bot or is_mentioning_this_bot):
        return
```

**Additional Features**:
- Bot-specific acknowledgment responses when mentioned by other bots
- Enhanced logging for bot-to-bot interactions with `is_grugthink_bot` field  
- Personality-appropriate "thinking" messages for bot interactions

**Usage**: Multiple bots can now respond in same channel when mentioned by name or @mention. Bots can reply to each other at least once when specifically mentioned.

### Rate Limiting Fix for Multi-Bot Responses
**Problem**: When multiple bots were mentioned in same message, only first bot could respond due to global rate limiting.

**Root Cause**: Rate limiting was per-user globally, not per-bot-per-user:
```python
def is_rate_limited(user_id: int) -> bool:
    now = time.time()
    if user_id in user_cooldowns and now - user_cooldowns[user_id] < 5:
        return True
    user_cooldowns[user_id] = now
    return False
```

**Solution**: Modified rate limiting to be per-bot-per-user in `bot.py:210-226`:
```python
def is_rate_limited(user_id: int, bot_id: str = None) -> bool:
    """Check if user is rate limited for a specific bot or globally."""
    now = time.time()
    
    if bot_id:
        # Check per-bot rate limiting (allows multiple bots to respond)
        key = f"{user_id}:{bot_id}"
        if key in user_cooldowns and now - user_cooldowns[key] < 5:
            return True
        user_cooldowns[key] = now
        return False
    # ... legacy behavior for backwards compatibility
```

**Updated Usage**: Pass bot_id to rate limiting checks:
```python
if is_rate_limited(message.author.id, self.get_bot_id()):
```

**Result**: When user mentions multiple bots like "big rob would beat grug", both bots can now respond simultaneously without rate limiting conflicts.

### Bot Logging Enhancement
**Status**: Logs now properly include `bot_id` field and support UUID-based bot identifiers for filtering in web UI.

**Implementation**: Enhanced structured logging includes both `is_markov_bot` and `is_grugthink_bot` flags for different bot interaction types.

### Bot Configuration Status Management
**Critical Pattern**: For auto-starting bots in multi-bot containers:

1. **Set status to `stopped` for auto-start**: Auto-start logic checks `auto_start_flag is not False or bot_status == "running"`
2. **Include explicit personality field**: Don't rely only on template personality, add explicit `personality: big_rob` 
3. **Use proper status transitions**: `stopped` → `starting` → `running` → `stopped`

**Example Correct Configuration**:
```yaml
bot_configs:
  bot-uuid:
    auto_start: true      # Explicit auto-start flag
    bot_id: bot-uuid
    name: Big Rob - Dev
    personality: big_rob  # Explicit personality
    status: stopped       # Runtime status (will be updated when started)
    template_id: pure_big_rob
    discord_token_id: '4'
```

### Auto-Start Configuration Fix (2025-07-01 Session 3 Part 2)
**Problem**: Bots with `auto_start: true` weren't starting on Docker container startup.

**Root Cause 1**: BotConfig dataclass missing `auto_start` field, causing config loading to fail silently.

**Root Cause 2**: Confusion between configuration status (`running`) and runtime state - bots set to `status: running` hit early return in `start_bot()`.

**Solution**: 
1. Added `auto_start` field to BotConfig dataclass in `bot_manager.py:44`:
```python
auto_start: Optional[bool] = None  # Whether to auto-start this bot on container startup
```

2. Updated auto-start logic to prioritize explicit flags in `main.py:108-109`:
```python
# Priority: explicit auto_start flag, then status "running"  
should_start = auto_start_flag is True or (auto_start_flag is None and bot_status == "running")
```

3. Set proper configuration pattern:
   - `auto_start: true` for bots that should start automatically
   - `status: stopped` to avoid early returns in start_bot()
   - `status` represents runtime state, `auto_start` represents startup behavior

**Key Learning**: Separate configuration intent (`auto_start`) from runtime state (`status`) to avoid startup conflicts.

### Cross-Bot Insults (2025-07-03 Session)
**Problem**: Bots saw mentions from others but rarely responded with playful jabs.

**Solution**: Added `generate_shit_talk()` helper in `bot.py` and initially appended results in `handle_auto_verification`. Bots issued a short insult when another bot talked about them.

**Key Learning**: Maintain per-mention response tracking to keep conversations civil while letting personalities shine.

### Separate Insult Messages (2025-07-04 Session)
**Problem**: Appending insults to verification messages made replies awkward.

**Solution**: Moved insult handling to `on_message` so bots send their jab as its own message once per mention.

**Key Learning**: Decoupling insult logic from verification keeps conversation flow natural and prevents quoting the previous bot.


### Pairwise Insult Control (2025-07-05 Session)
**Problem**: Bots would get stuck in endless insult loops when they saw each other's replies.

**Solution**: Introduced `_pair_key` and an LRU cache to track when each bot has already insulted the other. `on_message` now checks this cache so each bot fires back only once per pair.

**Key Learning**: Track per-pair insult state to keep conversations short and prevent runaway back-and-forth.

### Lazy Bot Import & Topic Context (2025-07-06 Session)
**Problem**: Importing the package raised `Missing DISCORD_TOKEN`, and bots were quoting each other when humans mentioned them.

**Solution**: Added a lazy `__getattr__` loader for the `bot` module and limited topic-based cross-bot context to human statements without other bot names.

**Key Learning**: Load optional modules lazily to avoid unnecessary configuration requirements and keep bot replies focused.

### Cross-Bot Insult Timing Fix (2025-07-02 Session)
**Problem**: When a bot mentioned another bot in their response, the mentioned bot would immediately send an insult before the original bot finished their main response. Insults appeared before the "Thinking..." message was replaced with the actual reply.

**Root Cause**: The insult logic in `on_message` executed immediately when detecting a bot mention, without waiting for the original bot to complete their response flow.

**Solution**: Added 2-second delay using `await asyncio.sleep(2)` before sending insult message in `bot.py:620`.

**Key Learning**: Cross-bot interactions need timing coordination - add delays to prevent race conditions between main responses and secondary reactions like insults.

### Expanded Cross-Bot Insult Variety (2025-07-02 Session)
**Problem**: Bots were using the same repetitive insults, making cross-bot interactions predictable and boring.

**Solution**: Enhanced `generate_shit_talk()` function with 12 unique insults per personality type:
- **Caveman**: Primitive insults with mammoth, rock, hunting, and cave themes
- **British Working Class**: Authentic UK slang with proper dialect ("tosser", "plonker", "muppet", etc.)
- **Adaptive**: Sophisticated analytical insults matching the personality's intellectual tone

**Implementation**: Used `random.choice()` for variety and personality-specific insult arrays in `bot.py:135-199`.

**Key Learning**: Personality-driven content variety significantly improves user engagement - each bot type should have unique, thematic responses that match their character.

### Enhanced Cross-Bot Knowledge Sharing (2025-07-02 Session)
**Problem**: Bots knew each other's memories but not personality information, leading to generic cross-bot interactions.

**Solution**: Enhanced the cross-bot memory system to include personality information:
- **Global Bot Manager Access**: Added `_global_bot_manager` reference in `main.py` for cross-bot communication
- **Personality Information Sharing**: New `get_cross_bot_personality_info()` function accesses bot personalities
- **Rich Context in Memory Sharing**: Modified `get_cross_bot_memories()` to include personality descriptions
- **Intelligent Bot Matching**: Pattern matching for bot identification (grug, big_rob, etc.)
- **Fallback Data**: Hardcoded personality info for single-bot mode

**Implementation**: Enhanced context now provides descriptions like "(Grug - caveman who fights sabertooths and hunts mammoth) [strength: physical, smarts: primitive]"

**Result**: Bots have authentic knowledge about each other - Big Rob knows Grug is a caveman, Grug knows Big Rob has strong football opinions.

**Key Learning**: Cross-bot interactions are dramatically improved when bots have access to each other's personality information, not just memories.
