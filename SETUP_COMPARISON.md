# Setup Script Comparison for GrugThink

## TL;DR for ChatGPT/Codex Users 🤖

**Use `setup-codex.sh` instead of `setup.sh`** for ChatGPT/OpenAI Codex workspaces.

## Quick Start for Codex

```bash
chmod +x setup-codex.sh
./setup-codex.sh
```

---

## Detailed Comparison

### `setup.sh` (Production Setup) 🏭

**Purpose**: Full production environment with real ML capabilities  
**Use Case**: Local development, production deployment  
**Download Size**: ~1.5GB+ (includes PyTorch, FAISS, sentence-transformers)  

**Pros:**
- ✅ Full ML functionality with real embeddings
- ✅ Vector search with semantic similarity  
- ✅ Local sentence transformer models
- ✅ Production-ready performance

**Cons:**
- ❌ Large download (~1.5GB+ dependencies)
- ❌ Long installation time (5-15 minutes)
- ❌ May timeout in cloud environments
- ❌ Requires stable internet connection
- ❌ Memory intensive during installation

### `setup-codex.sh` (Lightweight Setup) ⚡

**Purpose**: Fast development environment with mocked ML dependencies  
**Use Case**: ChatGPT/Codex workspaces, CI/CD, quick prototyping  
**Download Size**: ~50MB (lightweight dependencies only)

**Pros:**
- ✅ Fast installation (~30 seconds)
- ✅ Small download size (~50MB)
- ✅ Reliable in cloud environments
- ✅ All tests pass (38/38)
- ✅ Full development workflow support
- ✅ Automatic Python/pip detection

**Cons:**
- ❌ Mocked ML functionality (no real embeddings)
- ❌ Vector search uses keyword matching instead of semantic similarity
- ❌ Not suitable for production deployment

---

## What Works in Each Setup

| Feature | `setup.sh` | `setup-codex.sh` |
|---------|------------|------------------|
| Code development | ✅ | ✅ |
| Running tests | ✅ | ✅ |
| Linting/formatting | ✅ | ✅ |
| Discord bot functionality | ✅ | ✅* |
| Database operations | ✅ | ✅ |
| Vector search | ✅ Real semantic | ✅ Keyword-based |
| Production deployment | ✅ | ❌ |
| CI/CD pipeline | ✅ | ✅ Faster |

\* Discord bot works but uses mocked ML for fact verification

---

## Recommendations

### For ChatGPT/OpenAI Codex Users
**Use `setup-codex.sh`** - it's designed specifically for cloud development environments.

### For Local Development
**Use `setup.sh`** if you need real ML capabilities, otherwise `setup-codex.sh` is faster.

### For Production Deployment
**Always use `setup.sh`** - the mocked dependencies won't work in production.

### For CI/CD
**Use `setup-codex.sh`** - it's faster and more reliable in automated environments.

---

## Troubleshooting

### If `setup-codex.sh` fails:
1. Check Python is available: `python3 --version`
2. Check pip is available: `pip3 --version`
3. Run tests manually: `PYTHONPATH=. python3 -m pytest`

### If you need real ML functionality:
1. Use `setup.sh` instead
2. Or install missing dependencies: `pip install faiss-cpu sentence-transformers`

---

## Environment Detection

The `setup-codex.sh` script automatically detects and uses the best available Python/pip commands:

- Tries: `python3.11`, `python3`, `python`
- Tries: `pip3.11`, `pip3`, `pip`
- Gracefully handles missing commands
- Sets `PYTHONPATH=.` automatically