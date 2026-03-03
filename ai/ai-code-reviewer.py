#!/usr/bin/env python3

import subprocess
import json
import urllib.request
import urllib.error
import sys
import os
import argparse


AI_PROVIDER = os.getenv("AI_PROVIDER", "ollama").lower()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv(
    "OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions"
)
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
ANTHROPIC_BASE_URL = os.getenv(
    "ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1/messages"
)
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-haiku-4-5")

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5-coder:7b")


def get_staged_diff():
    try:
        # Get staged changes only
        result = subprocess.run(
            ["git", "diff", "--cached"], capture_output=True, text=True, check=True
        )
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"Failed to get git diff: {e}", file=sys.stderr)
        return ""


def get_files_content(file_paths):
    combined_content = ""
    for path in file_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    combined_content += f"--- {path} ---\n{content}\n\n"
            except Exception as e:
                print(f"⚠️ Error reading '{path}': {e}", file=sys.stderr)
        else:
            print(
                f"⚠️ Warning: File '{path}' not found or is not a file.", file=sys.stderr
            )
    return combined_content


def review_code(content: str, is_diff: bool = True) -> bool:
    content_type = "git diff" if is_diff else "code files"
    header = "Diff to review:" if is_diff else "Files to review:"

    prompt = f"""
You are an expert code reviewer. Please review the following {content_type} carefully.
If the code looks good, has no major bugs, and follows best practices, respond with exactly 'APPROVE' on the first line.
If there are issues, security vulnerabilities, or bugs, respond with 'REJECT' on the first line, followed by detailed review comments on the next lines.

{header}
{content}
"""
    headers = {"Content-Type": "application/json"}

    if AI_PROVIDER == "openai":
        if not OPENAI_API_KEY:
            print(
                f"⚠️ OpenAI provider selected but OPENAI_API_KEY is not set. Skipping AI review.",
                file=sys.stderr,
            )
            return True
        url = OPENAI_BASE_URL
        headers["Authorization"] = f"Bearer {OPENAI_API_KEY}"
        data = {
            "model": OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.1,
        }
    elif AI_PROVIDER == "anthropic":
        if not ANTHROPIC_API_KEY:
            print(
                f"⚠️ Anthropic provider selected but ANTHROPIC_API_KEY is not set. Skipping AI review.",
                file=sys.stderr,
            )
            return True
        url = ANTHROPIC_BASE_URL
        headers["x-api-key"] = ANTHROPIC_API_KEY
        headers["anthropic-version"] = "2023-06-01"
        data = {
            "model": ANTHROPIC_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 4096,
            "temperature": 0.1,
        }
    else:  # Default to Ollama
        url = OLLAMA_BASE_URL
        data = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1},
        }

    try:
        req = urllib.request.Request(
            url, data=json.dumps(data).encode("utf-8"), headers=headers
        )
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode())

            if AI_PROVIDER == "openai":
                response_text = result["choices"][0]["message"]["content"].strip()
                prompt_tokens = result["usage"]["prompt_tokens"]
                output_tokens = result["usage"]["completion_tokens"]
            elif AI_PROVIDER == "anthropic":
                response_text = result["content"][0]["text"].strip()
                prompt_tokens = result["usage"]["input_tokens"]
                output_tokens = result["usage"]["output_tokens"]
            else:  # Ollama
                response_text = result.get("response", "").strip()
                prompt_tokens = result.get("prompt_eval_count", 0)
                output_tokens = result.get("eval_count", 0)

            print(f"📊 Tokens: {prompt_tokens} (in) / {output_tokens} (out)")

            if response_text.upper().startswith("APPROVE"):
                print("✅ AI Code Review Passed.")
                return True
            else:
                print("❌ AI Code Review Failed:\n")
                print(response_text)
                return False

    except urllib.error.URLError as e:
        print(
            f"⚠️ Could not connect to {AI_PROVIDER} ({e}). Skipping AI review.",
            file=sys.stderr,
        )
        return True
    except Exception as e:
        print(f"⚠️ Error during AI review: {e}. Skipping.", file=sys.stderr)
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Code Reviewer")
    parser.add_argument(
        "--files",
        nargs="+",
        help="List of files to check (disables default git diff check)",
    )
    args = parser.parse_args()

    is_diff = True
    if args.files:
        content = get_files_content(args.files)
        is_diff = False
    else:
        content = get_staged_diff()

    if not content or not content.strip():
        print("ℹ️ No changes or files to review.")
        sys.exit(0)

    active_model = (
        OPENAI_MODEL
        if AI_PROVIDER == "openai"
        else (ANTHROPIC_MODEL if AI_PROVIDER == "anthropic" else OLLAMA_MODEL)
    )

    review_type = "specified files" if args.files else "staged changes"
    print(
        f"🤖 Running AI Code Review on {review_type} using {active_model} ({AI_PROVIDER})..."
    )

    passed = review_code(content, is_diff=is_diff)
    if not passed:
        sys.exit(1)
