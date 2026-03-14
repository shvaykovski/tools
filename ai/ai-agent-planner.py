#!/usr/bin/env python3

"""
AI Agent Planner
Iterative CLI tool to generate comprehensive implementation plans.

Environment Variables:
    export OPENAI_API_KEY="your_key"
    export ANTHROPIC_API_KEY="your_key"
    export OPENROUTER_API_KEY="your_key"
    export OLLAMA_BASE_URL="http://localhost:11434"
    export AI_PLANNER_MODEL="gpt-4o"

Usage:
    python3 ai-agent-planner.py "Build a web scraper"
    python3 ai-agent-planner.py --provider ollama "Refactor this module" --files src/logic.py
"""

import sys
import os
import json
import urllib.request
import urllib.error
import argparse
import platform
from datetime import datetime

# Configuration mirrors ai-helper.py and ai-code-reviewer.py
OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENROUTER_KEY = os.getenv("OPENROUTER_API_KEY", "")
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

# Defaults
DEFAULT_MODEL = os.getenv("AI_PLANNER_MODEL", "gpt-4o")
API_URL = os.getenv("AI_PLANNER_URL", "https://api.openai.com/v1/chat/completions")

# ANSI Colors for Terminal UI
YELLOW = "\033[1;33m"
BLUE = "\033[1;34m"
RED = "\033[1;31m"
CYAN = "\033[0;36m"
GREEN = "\033[0;32m"
RESET = "\033[0m"
BOLD = "\033[1m"


def get_system_context():
    """Gathers system info to aid planning (OS, Shell, Directory)."""
    try:
        os_name = platform.system()
        shell = os.path.basename(os.getenv("SHELL", "bash"))
        return f"OS: {os_name}, Shell: {shell}, CWD: {os.getcwd()}"
    except Exception:
        return "Standard macOS/Linux environment"


def read_files(file_paths):
    """Reads content of specified files to provide as context."""
    context = ""
    for path in file_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    context += f"\n--- FILE: {path} ---\n{content}\n"
            except Exception as e:
                print(f"{RED}Error reading {path}: {e}{RESET}")
    return context


def call_ai(messages, provider, model_override=None):
    """Generic wrapper for various AI providers using urllib."""
    headers = {"Content-Type": "application/json"}
    model = model_override or DEFAULT_MODEL

    if provider == "anthropic":
        url = "https://api.anthropic.com/v1/messages"
        headers.update({"x-api-key": ANTHROPIC_KEY, "anthropic-version": "2023-06-01"})
        system_msg = messages[0]["content"] if messages[0]["role"] == "system" else ""
        user_msgs = [m for m in messages if m["role"] != "system"]
        data = {
            "model": "claude-3-5-sonnet-20241022" if model.startswith("gpt") else model,
            "system": system_msg,
            "messages": user_msgs,
            "max_tokens": 4096,
            "temperature": 0.2,
        }
    elif provider == "openrouter":
        url = "https://openrouter.ai/api/v1/chat/completions"
        headers.update(
            {
                "Authorization": f"Bearer {OPENROUTER_KEY}",
                "HTTP-Referer": "https://github.com/maximshvaykovski/tools",
                "X-Title": "AI Agent Planner",
            }
        )
        data = {"model": model, "messages": messages, "temperature": 0.2}
    elif provider == "ollama":
        url = f"{OLLAMA_URL}/api/chat"
        ollama_model = model if model != "gpt-4o" else "qwen2.5-coder:7b"
        data = {
            "model": ollama_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.2},
        }
    else:  # OpenAI
        url = API_URL
        headers["Authorization"] = f"Bearer {OPENAI_KEY}"
        data = {"model": model, "messages": messages, "temperature": 0.2}

    try:
        req = urllib.request.Request(
            url, data=json.dumps(data).encode(), headers=headers
        )
        with urllib.request.urlopen(req, timeout=90) as response:
            res = json.loads(response.read())
            if provider == "anthropic":
                return res["content"][0]["text"].strip()
            elif provider == "ollama":
                return res["message"]["content"].strip()
            return res["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"{RED}API Error ({provider}): {e}{RESET}")
        sys.exit(1)


def save_plan(plan_content):
    """Handles the final phase of saving the plan to a file."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    default_name = f"plan-{timestamp}.md"

    print(f"\n{BLUE}💾 Would you like to save this plan to a file?{RESET}")
    choice = input(f" [{BOLD}y{RESET}]es / [{BOLD}n{RESET}]o: ").strip().lower()

    if choice == "y":
        filename = input(
            f" Enter filename (default: {YELLOW}{default_name}{RESET}): "
        ).strip()
        if not filename:
            filename = default_name

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(plan_content)
            print(f"{GREEN}✨ Plan successfully saved to: {BOLD}{filename}{RESET}")
        except Exception as e:
            print(f"{RED}Error saving file: {e}{RESET}")
    else:
        print("Plan not saved.")


def main():
    parser = argparse.ArgumentParser(description="AI Agent Planner")
    parser.add_argument("goal", nargs="*", help="Goal or task to plan for")
    parser.add_argument("-f", "--files", nargs="+", help="Local files for context")
    parser.add_argument(
        "-p",
        "--provider",
        choices=["openai", "anthropic", "openrouter", "ollama"],
        default="ollama",
    )
    parser.add_argument(
        "-m", "--model", default="qwen2.5-coder:7b", help="Override default model"
    )

    args = parser.parse_args()
    if not args.goal and not args.files:
        parser.print_help()
        sys.exit(0)

    goal_text = " ".join(args.goal)
    file_context = read_files(args.files) if args.files else ""

    system_prompt = (
        "You are an AI Agent Planner. Create a detailed technical implementation plan in Markdown. "
        f"Context: {get_system_context()}. "
        "Rules:\n"
        "1. If you need clarification, ask EXACTLY ONE question.\n"
        "2. If you have enough info, provide a full Markdown plan.\n"
        "3. Start responses with 'QUESTION:' or 'PLAN:'."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Goal: {goal_text}\n\nFiles Context:\n{file_context}",
        },
    ]

    active_model = args.model or DEFAULT_MODEL
    print(f"{BLUE}🤖 Planning with {active_model} ({args.provider})...{RESET}")

    final_plan = ""
    while True:
        print(f"{CYAN}🔍 Thinking...{RESET}", end="\r")
        response = call_ai(messages, args.provider, args.model)
        sys.stdout.write("\033[2K\r")

        if response.startswith("QUESTION:"):
            print(f"\n{YELLOW}🤔 Question:{RESET} {response[9:].strip()}")
            try:
                ans = input(f"\n{BOLD}Answer ('exit' to quit): {RESET}").strip()
                if ans.lower() in ["exit", "quit"]:
                    break
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": ans})
            except KeyboardInterrupt:
                break
        elif response.startswith("PLAN:"):
            final_plan = response[5:].strip()
            print(f"\n{GREEN}✅ Final Plan Generated:{RESET}\n\n{final_plan}\n")
            save_plan(final_plan)
            break
        else:
            # Fallback for models that might miss the prefix
            print(f"\n{response}\n")
            save_plan(response)
            break


if __name__ == "__main__":
    main()
