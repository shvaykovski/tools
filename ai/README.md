# AI Tools Suite

A collection of powerful, modular AI agents and scripts designed to automate research, technical planning, code review, and terminal tasks.

## 🧰 Tools Catalog

| Script                       | Purpose                | Key Features                                                      |
| :--------------------------- | :--------------------- | :---------------------------------------------------------------- |
| **`ai-orchestrator.py`**     | **Master Agent**       | Chains Research and Planning into a unified agentic flow.         |
| **`ai-agent-researcher.py`** | **Research Agent**     | Multi-query web search via SearXNG & scraping with `trafilatura`. |
| **`ai-agent-planner.py`**    | **Planning Agent**     | Iterative technical plan generation with feedback loops.          |
| **`ai-helper.py`**           | **Terminal Assistant** | Natural language to shell commands (with execute/copy options).   |
| **`ai-code-reviewer.py`**    | **Code Reviewer**      | Analyzes staged git changes or specific files for bugs/security.  |
| **`whisper-transcribe.py`**  | **Transcription**      | Converts audio files to text using OpenAI Whisper.                |

---

## 🚀 Setup & Installation

### 1. Prerequisites

- **Python 3.10+**
- **SearXNG**: Required for `ai-agent-researcher` and `ai-orchestrator`.
- **Dependencies**:
  It is strongly recommended to use a virtual environment:
  ```bash
  cd ai
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
  _Note: All scripts should be executed within this virtual environment._

### 2. Environment Variables

Configure your providers in your shell profile (e.g., `~/.zshrc` or `~/.bashrc`):

```bash
# AI Providers
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="xsk-..."
export OPENROUTER_API_KEY="sk-or-..."
export GOOGLE_AI_API_KEY="AIza..."

# Optional: Local/Service URLs
export OLLAMA_BASE_URL="http://localhost:11434"
export SEARXNG_URL="http://localhost:8889"

# Defaults
export AI_DEFAULT_PROVIDER="ollama"  # openai, anthropic, openrouter, google
```

---

## 🌐 Provider Configuration

### Google AI

1. **API Key**: Set `GOOGLE_AI_API_KEY` for standard AI Studio access.

### Ollama (Local)

Ensure Ollama is running. By default, it uses `qwen3.5:4b`. You can override this:

```bash
export OLLAMA_MODEL="llama3.1"
```

---

## 🛠 Usage Examples

_Ensure your virtual environment is activated (`source .venv/bin/activate`) before running scripts._

### End-to-End Orchestration

Research a topic and build a technical plan automatically:

```bash
./ai-orchestrator.py "Architect a real-time chat app using WebSockets and Redis"
```

### Deep Web Research

Scrape 10 sources and generate a report:

```bash
./ai-agent-researcher.py --limit 10 "Latest advancements in solid state batteries 2025"
```

### Interactive Planning

Generate a plan and provide iterative feedback:

```bash
./ai-agent-planner.py "Refactor my auth logic" -f src/auth.py
```

### Terminal Assistance

Execute a complex command immediately:

```bash
./ai-helper.py -e "find logs older than 7 days and compress them"
```

### Code Review

Review staged git changes before committing:

```bash
./ai-code-reviewer.py
```

---

## 🏗 Core Architecture (`ai_core`)

The suite is built on a shared internal package for consistency:

- `ai_client.py`: Unified interface for all LLM providers.
- `config.py`: Global configuration and environment handling.
- `utils.py`: Context assembly, file I/O, and terminal formatting.
- `colors.py`: Beautiful ANSI terminal output.
