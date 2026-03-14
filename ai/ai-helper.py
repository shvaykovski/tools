#!/usr/bin/env python3

"""
AI Terminal Assistant
Generates shell commands from natural language descriptions using various AI providers.

Prerequisites:
    - Python 3.x
    - Access to at least one supported AI provider (OpenAI, Anthropic, OpenRouter, or Ollama)
    - Local 'ai_core' package

Environment Variables:
    export OPENAI_API_KEY="your_key"
    export ANTHROPIC_API_KEY="your_key"
    export OPENROUTER_API_KEY="your_key"

Usage (Direct Call):
    python3 ai-helper.py "list all files larger than 100MB"
    python3 ai-helper.py "convert all png to jpg" -e
    python3 ai-helper.py "how to check disk usage" -c
    python3 ai-helper.py --provider anthropic "search for a text in files"
    python3 ai-helper.py --model gpt-4o "reconcile git branch"

Flags:
    -a, --ask        Ask for an explanation instead of a direct command
    -e, --execute    Execute the generated command immediately after generation
    -c, --copy       Copy the command to clipboard and exit
    -p, --provider   AI provider (openai, anthropic, openrouter, or ollama)
    -m, --model      Override the default model name for the provider
"""

import sys
import subprocess
import argparse
from ai_core.colors import YELLOW, BLUE, RED, RESET, BOLD, format_markdown
from ai_core.utils import get_system_context, copy_to_clipboard, clean_markdown
from ai_core.ai_client import call_ai
from ai_core.config import DEFAULT_PROVIDER, get_default_model


def ask_ai_helper(
    question: str, provider: str, model_override: str = None, ask_mode: bool = False
) -> str:
    """Queries the AI for a terminal command or explanation."""
    ctx = get_system_context()

    if ask_mode:
        system_prompt = (
            "You are a helpful terminal assistant. The user asks how to do something or for an explanation. "
            f"Context: {ctx}. "
            "Rules:\n"
            "1. Provide a brief, concise explanation.\n"
            "2. Include markdown formatting for commands if needed.\n"
            "3. Keep it short and to the point."
        )
    else:
        system_prompt = (
            "You are a terminal command assistant. The user describes a task, and you provide the exact shell command. "
            f"Context: {ctx}. "
            "Rules:\n"
            "1. Reply ONLY with the raw command on a single line.\n"
            "2. No markdown, no backticks, no markdown blocks, no explanations.\n"
            "3. IMPORTANT: DO NOT wrap the command in triple backticks or any markdown. Just the raw text.\n"
            "4. Ensure the command is compatible with the provided OS and shell.\n"
            "5. If multiple commands are needed, join them with && or |."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    # Resolve model
    active_model = model_override or get_default_model(provider)

    content = call_ai(messages, provider, active_model)

    if not content:
        return ""

    if ask_mode:
        return clean_markdown(content)

    # Post-processing for command mode
    content = clean_markdown(content)
    return content.strip("`").strip()


def main():
    parser = argparse.ArgumentParser(
        description="AI-powered terminal assistant that generates shell commands from natural language.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", nargs="*", help="Description of the task to perform")
    parser.add_argument(
        "-a", "--ask", action="store_true", help="Ask for an explanation"
    )
    parser.add_argument(
        "-e", "--execute", action="store_true", help="Execute command immediately"
    )
    parser.add_argument(
        "-c", "--copy", action="store_true", help="Copy command to clipboard"
    )
    parser.add_argument("-m", "--model", help="Override AI Model")
    parser.add_argument(
        "-p",
        "--provider",
        choices=["openai", "anthropic", "openrouter", "ollama"],
        default=DEFAULT_PROVIDER,
        help="AI provider",
    )

    if len(sys.argv) == 1:
        print(__doc__)
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if not args.query:
        print(f"{RED}Error: No query provided.{RESET}")
        sys.exit(1)

    query = " ".join(args.query)

    print(f"{BLUE}🔍 Thinking...{RESET}", end="\r")
    cmd = ask_ai_helper(query, args.provider, args.model, args.ask)
    sys.stdout.write("\033[2K\r")
    sys.stdout.flush()

    if not cmd:
        print(f"{RED}No response generated.{RESET}")
        sys.exit(1)

    if args.ask:
        formatted_cmd = format_markdown(cmd)
        print(f"{formatted_cmd}\n")
        sys.exit(0)

    print(f"\n  {YELLOW}➜  {BOLD}{cmd}{RESET}\n")

    if args.copy:
        copy_to_clipboard(cmd)
        print(f"📋 Command copied to clipboard.")
        return

    if args.execute:
        try:
            subprocess.run(cmd, shell=True, check=True)
        except subprocess.CalledProcessError as e:
            print(f"{RED}Command failed with exit code {e.returncode}{RESET}")
        except Exception as e:
            print(f"{RED}Error executing command: {e}{RESET}")
        return

    try:
        prompt = (
            f" [{BOLD}y{RESET}]execute, [{BOLD}c{RESET}]opy, [{BOLD}n{RESET}]abort: "
        )
        choice = input(prompt).strip().lower()

        if choice == "y":
            subprocess.run(cmd, shell=True, check=True)
        elif choice == "c":
            copy_to_clipboard(cmd)
            print("📋 Command copied to clipboard.")
        else:
            print("Aborted.")

    except (KeyboardInterrupt, subprocess.CalledProcessError):
        print("\nAborted.")
        sys.exit(0)


if __name__ == "__main__":
    main()
