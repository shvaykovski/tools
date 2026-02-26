#!/usr/bin/env python3

"""
# Set env vars to use local LLM:

export OPENAI_API_KEY="local" # or your OpenAI API key
export AI_BASH_URL="http://localhost:11434/v1/chat/completions" # or your LLM API URL
export AI_BASH_MODEL="qwen2.5:7b" # or your LLM model

# Add alias to your .bashrc or .zshrc:
alias ai="python3 ~/.local/bin/tools/ai/ai-helper.py"
"""

import sys
import os
import json
import urllib.request
import urllib.error
import subprocess
import argparse
import platform

# Configuration
API_KEY = os.getenv("OPENAI_API_KEY", "")
API_URL = os.getenv("AI_BASH_URL", "https://api.openai.com/v1/chat/completions")
MODEL = os.getenv("AI_BASH_MODEL", "gpt-4o-mini")

# Color constants
YELLOW = "\033[1;33m"
BLUE = "\033[1;34m"
RED = "\033[1;31m"
RESET = "\033[0m"
BOLD = "\033[1m"


def get_system_context():
    """Gathers information about the current system to help the AI generate better commands."""
    try:
        os_name = platform.system()
        os_version = (
            platform.mac_ver()[0] if os_name == "Darwin" else platform.release()
        )
        shell = os.path.basename(os.getenv("SHELL", "bash"))
        return f"OS: {os_name} (version {os_version}), Shell: {shell}, Working Dir: {os.getcwd()}"
    except Exception:
        return "OS: macOS/Linux"


def ask_ai(question: str) -> str:
    """Queries the AI for a terminal command."""
    if not API_KEY and "openai.com" in API_URL:
        print(
            f"{RED}Error: OPENAI_API_KEY environment variable is not set.{RESET}",
            file=sys.stderr,
        )
        sys.exit(1)

    ctx = get_system_context()
    system_prompt = (
        "You are a terminal command assistant. The user describes a task, and you provide the exact shell command. "
        f"Context: {ctx}. "
        "Rules:\n"
        "1. Reply ONLY with the raw command on a single line.\n"
        "2. No markdown, no backticks, no markdown blocks, no explanations.\n"
        "3. Ensure the command is compatible with the provided OS and shell.\n"
        "4. If multiple commands are needed, join them with && or |."
    )

    payload = {
        "model": MODEL,
        "temperature": 0.1,
        "max_tokens": 500,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": question},
        ],
    }

    try:
        req = urllib.request.Request(
            API_URL,
            data=json.dumps(payload).encode(),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {API_KEY}",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            res_data = json.loads(response.read())
            content = res_data["choices"][0]["message"]["content"].strip()

            # Post-processing to remove any unwanted formatting
            if "```" in content:
                content = (
                    content.split("```")[-2].split("\n", 1)[-1]
                    if content.count("```") >= 2
                    else content
                )
            return content.strip("`").strip()

    except urllib.error.HTTPError as e:
        print(f"{RED}API Error: {e.code} - {e.reason}{RESET}", file=sys.stderr)
        try:
            error_details = json.loads(e.read())
            print(
                f"Details: {error_details.get('error', {}).get('message')}",
                file=sys.stderr,
            )
        except:
            pass
        sys.exit(1)
    except Exception as e:
        print(f"{RED}Error: {e}{RESET}", file=sys.stderr)
        sys.exit(1)


def copy_to_clipboard(text: str):
    """Copies text to the clipboard using pbcopy (macOS) or xclip/xsel (Linux)."""
    try:
        if platform.system() == "Darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
        else:
            # Try xclip then xsel for Linux
            try:
                subprocess.run(
                    ["xclip", "-selection", "clipboard"],
                    input=text.encode(),
                    check=True,
                )
            except (FileNotFoundError, subprocess.CalledProcessError):
                subprocess.run(
                    ["xsel", "--clipboard", "--input"], input=text.encode(), check=True
                )
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser(
        description="AI-powered terminal assistant that generates shell commands from natural language.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", nargs="*", help="Description of the task to perform")
    parser.add_argument(
        "-e", "--execute", action="store_true", help="Execute the command immediately"
    )
    parser.add_argument(
        "-c", "--copy", action="store_true", help="Copy command to clipboard and exit"
    )

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if not args.query:
        print(f"{RED}Error: No query provided.{RESET}")
        sys.exit(1)

    query = " ".join(args.query)

    print(f"{BLUE}🔍 Thinking...{RESET}", end="\r")
    cmd = ask_ai(query)
    print(" " * 20, end="\r")  # Clear "Thinking..." line

    if not cmd:
        print(f"{RED}No command generated.{RESET}")
        sys.exit(1)

    print(f"\n  {YELLOW}➜  {BOLD}{cmd}{RESET}\n")

    if args.copy:
        copy_to_clipboard(cmd)
        print(f"📋 Command copied to clipboard.")
        return

    if args.execute:
        subprocess.call(cmd, shell=True)
        return

    try:
        prompt = (
            f" [{BOLD}y{RESET}]execute, [{BOLD}c{RESET}]opy, [{BOLD}n{RESET}]abort: "
        )
        choice = input(prompt).strip().lower()

        if choice == "y":
            subprocess.call(cmd, shell=True)
        elif choice == "c":
            copy_to_clipboard(cmd)
            print("📋 Command copied to clipboard.")
        else:
            print("Aborted.")

    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(0)


if __name__ == "__main__":
    main()
