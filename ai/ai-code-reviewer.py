#!/usr/bin/env python3

"""
AI Code Reviewer
Analyzes staged git changes or specified files for bugs, security issues, and best practices.

Prerequisites:
    - Python 3.x
    - Git (for staged diff review)
    - Access to at least one supported AI provider (OpenAI, Anthropic, OpenRouter, or Ollama)
    - Local 'ai_core' package

Environment Variables:
    export OPENAI_API_KEY="your_key"
    export ANTHROPIC_API_KEY="your_key"
    export OPENROUTER_API_KEY="your_key"

Usage (Direct Call):
    python3 ai-code-reviewer.py
    python3 ai-code-reviewer.py --files src/main.py src/utils.py
    python3 ai-code-reviewer.py --provider anthropic
    python3 ai-code-reviewer.py --model gpt-4o

Flags:
    --files          Specify list of files to review (disables staged git diff review)
    -p, --provider   AI provider (openai, anthropic, openrouter, or ollama)
    -m, --model      Override the default model name for the provider
"""

import subprocess
import sys
import argparse
from ai_core.colors import RED, GREEN, BLUE, RESET, BOLD
from ai_core.utils import read_files, clean_markdown
from ai_core.ai_client import call_ai
from ai_core.config import DEFAULT_PROVIDER, get_default_model


def get_staged_diff():
    try:
        result = subprocess.run(
            ["git", "diff", "--cached"], capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def review_code(content: str, provider: str, model: str, is_diff: bool = True) -> bool:
    content_type = "git diff" if is_diff else "code files"
    header = "Diff to review:" if is_diff else "Files to review:"

    prompt = f"""
You are an expert code reviewer. Please review the following {content_type} carefully.
If the code looks good, has no major bugs, and follows best practices, respond with exactly 'APPROVE' on the first line.
If there are issues, security vulnerabilities, or bugs, respond with 'REJECT' on the first line, followed by detailed review comments on the next lines.

{header}
{content}
"""
    messages = [{"role": "user", "content": prompt}]
    response_text = call_ai(messages, provider, model, temperature=0.1)
    response_text = clean_markdown(response_text) if response_text else ""

    if not response_text:
        print(f"{RED}⚠️ AI review failed. Skipping.{RESET}")
        return True

    if response_text.upper().startswith("APPROVE"):
        print(f"{GREEN}✅ AI Code Review Passed.{RESET}")
        return True
    else:
        print(f"{RED}❌ AI Code Review Failed:{RESET}\n")
        print(response_text)
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Code Reviewer")
    parser.add_argument("--files", nargs="+", help="Files to review")
    parser.add_argument("-p", "--provider", help="AI provider")
    parser.add_argument("-m", "--model", help="AI model")
    args = parser.parse_args()

    active_provider = args.provider.lower() if args.provider else DEFAULT_PROVIDER
    active_model = args.model or get_default_model(active_provider)

    is_diff = True
    if args.files:
        content = read_files(args.files)
        is_diff = False
    else:
        content = get_staged_diff()

    if not content or not content.strip():
        print(f"{BLUE}ℹ️ No changes or files to review.{RESET}")
        sys.exit(0)

    review_type = "specified files" if args.files else "staged changes"
    print(f"{BLUE}🤖 Running AI Code Review on {review_type} using {BOLD}{active_model}{RESET} ({active_provider})...{RESET}")

    passed = review_code(content, active_provider, active_model, is_diff=is_diff)
    if not passed:
        sys.exit(1)
