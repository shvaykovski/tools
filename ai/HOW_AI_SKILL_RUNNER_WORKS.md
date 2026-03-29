# AI Skill Runner: How It Works

`AI Skill Runner` is a powerful bridge between **Claude Code skills** (and agents) and various AI providers (OpenAI, Anthropic, OpenRouter, Google, or Ollama). It allows you to run specialized AI behaviors on your local system with full access to local scripts and tools.

---

## 🏗️ Core Architecture

The tool follows a modular architecture that separates discovery, prompt assembly, and AI interaction.

### 1. Discovery Process

The runner automatically scans two primary locations:

- **Skills**: `~/.claude/skills/*/SKILL.md` — Multi-file directories containing common logic, scripts, and references.
- **Agents**: `~/.claude/agents/*.md` — Single-file specialized personas.

For each discovered item, the tool parses the **YAML Frontmatter** for metadata like `name`, `description`, `model`, and `tools`.

### 2. System Prompt Engineering

When a skill is selected, the runner dynamically builds a **System Prompt** by merging:

- The main body of the markdown file.
- **Discovery of Scripts**: Lists all files in the skill's `scripts/` directory.
- **Absolute Path Injection**: Provides the AI with the absolute path of the `scripts/` folder.
- **Context Files**: Merges content from `references/` and `examples/` (if `--refs` is enabled).

---

## 🤖 Agentic Intelligence

The tool goes beyond simple chat; it supports an **Agentic Loop** that allows the AI to "act" on your system.

### 1. Auto-Routing

If you don't provide a specific skill name, the runner uses AI to analyze your prompt and the entire skill catalog to pick the **Best-fitting Tool**.

> **Example**: "Review this code" → Automatically selects `code-reviewer`.

### 2. Thought-Action-Observation Loop

This is the core of the tool's power. It implements a reactive loop in both single-shot and interactive modes:

1.  **Thought**: The AI decides it needs to run a script.
2.  **Action**: The AI outputs a code block (e.g., `python ... ` or `bash ... `).
3.  **Execution**: The runner detects the block, executes it locally, and captures the STDOUT/STDERR.
4.  **Observation**: The results are fed back into the AI as a "user message" labeled `OBSERVATION`.
5.  **Refinement**: The AI continues its response based on the data it just gathered.

---

## ⚙️ Script Execution Suite

The runner provides a secure, sandboxed execution environment for several languages:

| Language    | Environment Support                                                             |
| :---------- | :------------------------------------------------------------------------------ |
| **Bash**    | Standard shell access, `PATH` includes the skill's `scripts/` dir.              |
| **Python**  | `PYTHONPATH` points to the skill's `scripts/` dir, allowing `import my_script`. |
| **Node.js** | `NODE_PATH` points to the skill's `scripts/` dir.                               |

### Execution Safety

- **Timeout**: Commands are automatically killed after 30 seconds to prevent hangs.
- **Max Loops**: The agentic loop is capped at 5 steps to prevent recursive AI feedback loops.
- **Temp Files**: Code is executed via uniquely named temporary files to avoid collisions.

---

## 🛠️ CLI Workflow

The runner handles input through several channels:

- **Positional Args**: `python3 ai-skill-runner.py <skill> <prompt>`
- **Piped Stdin**: `cat code.py | python3 ai-skill-runner.py review`
- **Interactive Mode**: `python3 ai-skill-runner.py code-reviewer -i`

### Argument Disambiguation

The tool uses a refined logic to decide if your first argument is a **Skill Name** or the **Start of a Prompt**:

1.  **Qualified Names**: `agent:name` or `skill:name` are always treated as selections.
2.  **Existence Check**: If the first word exactly matches a known skill and more text follows, it selects that skill.
3.  **Fallback**: It treats everything as a prompt and triggers **Auto-Routing**.

---

## 📁 Recommended Skill Structure

To get the most out of the runner, structure your skills as follows:

```text
~/.claude/skills/my-awesome-tool/
├── SKILL.md        # Metadata and main instructions
├── scripts/        # Python/Node/Bash scripts the AI can run
├── references/     # Docs or codebase samples
└── examples/       # Sample inputs and desired outputs
```

The runner's ability to "see" these directories and "run" their contents makes it a versatile tool for local AI-driven automation.

---

## 💡 5 Practical Use Cases

Here are five ways to leverage `AI Skill Runner` by creating specialized skills:

### 1. Code Security Auditor

Create a skill that includes scripts for running static analysis tools like `Bandit` (for Python) or `Semgrep`.

- **Workflow**: The AI receives a security prompt, executes the audit script on the target files, receives the JSON scan report as an `OBSERVATION`, and then explains the vulnerabilities in plain English with code fixes.

### 2. Live API Debugger

Build a skill with a `scripts/` directory containing template `curl` or `requests` scripts.

- **Workflow**: When you ask "Why is my local endpoint failing?", the AI uses the scripts to make real network calls, observes the full headers and body, and uses its reasoning to diagnose auth errors or mismatched schemas.

### 3. Smart Data Transformer

A skill with a Python script utilizing `pandas` or `csv`.

- **Workflow**: Piped data (e.g., `cat data.csv | python3 ai-skill-runner.py transform`) is analyzed. The AI writes code to clean, filter, or reformat the data dynamically while responding to your natural language request.

### 4. Log Pattern Explorer

A skill that uses complex `grep` and `awk` scripts to ingest large logs.

- **Workflow**: Instead of manually searching, you ask "Find any connection timeouts in the last hour." The AI executes the search scripts and highlights the relevant stack traces with a summary of the root cause.

### 5. Documentation Sync Agent

A skill that runs an extraction script to pull comments/types from source files.

- **Workflow**: "Build a README for this module." The AI runs the script to see the actual function signatures, interprets their intent, and generates a structured, up-to-date markdown documentation file.
