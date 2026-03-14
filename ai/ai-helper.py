#!/usr/bin/env python3

"""
AI Terminal Assistant
Generates shell commands from natural language descriptions.

Environment Variables:
    export OPENAI_API_KEY="your_key"
    export ANTHROPIC_API_KEY="your_key"
    export OPENROUTER_API_KEY="your_key"
    export AI_BASH_URL="https://api.openai.com/v1/chat/completions"
    export AI_BASH_MODEL="gpt-4o-mini"

Usage:
    ai "list all files larger than 100MB"
    ai "convert all png to jpg" -e
    ai "how to check disk usage" -c

Flags:
    -a, --ask        Ask for an explanation instead of a command
    -e, --execute    Execute the generated command immediately
    -c, --copy       Copy the command to clipboard and exit
    -u, --url        Override the API URL
    -m, --model      Override the model name
    -p, --provider   AI provider (openai, anthropic, or openrouter)

Alias Recommendation (add to .bashrc or .zshrc):
    alias ai="python3 /Users/maximshvaykovski/.local/bin/tools/ai/ai-helper.py"
"""

import sys
import os
import re
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
CYAN = "\033[0;36m"
GREEN = "\033[0;32m"
RESET = "\033[0m"
BOLD = "\033[1m"


def format_markdown(text: str) -> str:
    """Applies basic ANSI color formatting to markdown text."""
    # Code blocks
    text = re.sub(
        r"```[^\n]*\n(.*?)```",
        lambda m: CYAN + m.group(1).strip() + RESET,
        text,
        flags=re.DOTALL,
    )
    # Inline code
    text = re.sub(r"`([^`]+)`", CYAN + r"\1" + RESET, text)
    # Bold
    text = re.sub(r"\*\*(.*?)\*\*", BOLD + r"\1" + RESET, text)
    # Headers
    text = re.sub(
        r"^(#{1,6})\s*(.*)",
        lambda m: BOLD + BLUE + m.group(2) + RESET,
        text,
        flags=re.MULTILINE,
    )

    # Minimize excessive repetitive newlines
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text


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


def ask_ai(question: str, provider: str, ask_mode: bool = False) -> str:
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
            "3. Ensure the command is compatible with the provided OS and shell.\n"
            "4. If multiple commands are needed, join them with && or |."
        )

    if provider == "anthropic":
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not anthropic_key:
            print(
                f"{RED}Error: ANTHROPIC_API_KEY environment variable is not set.{RESET}",
                file=sys.stderr,
            )
            sys.exit(1)

        url = "https://api.anthropic.com/v1/messages"
        model = MODEL if MODEL != "gpt-4o-mini" else "claude-3-5-sonnet-20241022"
        payload = {
            "model": model,
            "max_tokens": 500,
            "temperature": 0.1,
            "system": system_prompt,
            "messages": [{"role": "user", "content": question}],
        }
        headers = {
            "Content-Type": "application/json",
            "x-api-key": anthropic_key,
            "anthropic-version": "2023-06-01",
        }
    elif provider == "openrouter":
        openrouter_key = os.getenv("OPENROUTER_API_KEY", "")
        if not openrouter_key:
            print(
                f"{RED}Error: OPENROUTER_API_KEY environment variable is not set.{RESET}",
                file=sys.stderr,
            )
            sys.exit(1)

        url = "https://openrouter.ai/api/v1/chat/completions"
        model = MODEL if MODEL != "gpt-4o-mini" else "google/gemini-flash-1.5"
        payload = {
            "model": model,
            "temperature": 0.1,
            "max_tokens": 500,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {openrouter_key}",
            "HTTP-Referer": "https://github.com/maximshvaykovski/ai-helper",
            "X-Title": "AI Terminal Assistant",
        }
    else:
        if not API_KEY and "openai.com" in API_URL:
            print(
                f"{RED}Error: OPENAI_API_KEY environment variable is not set.{RESET}",
                file=sys.stderr,
            )
            sys.exit(1)

        url = API_URL
        payload = {
            "model": MODEL,
            "temperature": 0.1,
            "max_tokens": 500,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        }
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        }

    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode(),
            headers=headers,
        )
        with urllib.request.urlopen(req, timeout=20) as response:
            res_data = json.loads(response.read())

            if provider == "anthropic":
                content = res_data["content"][0]["text"].strip()
            else:
                content = res_data["choices"][0]["message"]["content"].strip()

            if ask_mode:
                return content.strip()

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
    global API_URL, MODEL

    parser = argparse.ArgumentParser(
        description="AI-powered terminal assistant that generates shell commands from natural language.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("query", nargs="*", help="Description of the task to perform")
    parser.add_argument(
        "-a",
        "--ask",
        action="store_true",
        help="Ask for an explanation instead of a command",
    )
    parser.add_argument(
        "-e", "--execute", action="store_true", help="Execute the command immediately"
    )
    parser.add_argument(
        "-c", "--copy", action="store_true", help="Copy command to clipboard and exit"
    )
    parser.add_argument("-u", "--url", help="Override AI API URL")
    parser.add_argument("-m", "--model", help="Override AI Model")
    parser.add_argument(
        "-p",
        "--provider",
        choices=["openai", "anthropic", "openrouter"],
        default="openai",
        help="AI provider (openai for OpenAI/Local, anthropic for Claude, openrouter for OpenRouter)",
    )

    if len(sys.argv) == 1:
        print(__doc__)
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Configuration overrides
    if args.url:
        API_URL = args.url
    if args.model:
        MODEL = args.model

    if not args.query:
        print(f"{RED}Error: No query provided.{RESET}")
        sys.exit(1)

    query = " ".join(args.query)

    print(f"{BLUE}🔍 Thinking...{RESET}", end="\r")
    cmd = ask_ai(query, args.provider, args.ask)
    sys.stdout.write("\033[2K\r")  # Clear "Thinking..." line completely
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
            try:
                subprocess.run(cmd, shell=True, check=True)
            except subprocess.CalledProcessError as e:
                print(f"{RED}Command failed with exit code {e.returncode}{RESET}")
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
