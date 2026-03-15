#!/usr/bin/env python3

"""
AI Agent Planner
Iterative CLI tool to generate comprehensive technical implementation plans.

Prerequisites:
    - Python 3.x
    - Access to at least one supported AI provider (OpenAI, Anthropic, OpenRouter, or Ollama)
    - Local 'ai_core' package

Environment Variables:
    export OPENAI_API_KEY="your_key"
    export ANTHROPIC_API_KEY="your_key"
    export OPENROUTER_API_KEY="your_key"

Usage (Direct Call):
    python3 ai-agent-planner.py "Build a web scraper"
    python3 ai-agent-planner.py --provider ollama "Refactor this module" --files src/logic.py
    python3 ai-agent-planner.py --provider anthropic "Design a microservice architecture"
    python3 ai-agent-planner.py --model gpt-4o "Plan a database migration"

Flags:
    -f, --files      Path to local files to be used as context for planning
    -p, --provider   AI provider (openai, anthropic, openrouter, or ollama)
    -m, --model      Override the default model name for the provider
"""

import sys
import argparse
from ai_core.colors import YELLOW, BLUE, RED, CYAN, GREEN, RESET, BOLD
from ai_core.utils import (
    get_system_context,
    read_files_context,
    save_to_file,
    clean_markdown,
)
from ai_core.ai_client import call_ai
from ai_core.config import DEFAULT_PROVIDER, get_default_model


def main():
    parser = argparse.ArgumentParser(description="AI Agent Planner")
    parser.add_argument("goal", nargs="*", help="Goal or task to plan for")
    parser.add_argument("-f", "--files", nargs="+", help="Local files for context")
    parser.add_argument(
        "-p",
        "--provider",
        choices=["openai", "anthropic", "openrouter", "ollama"],
        default=DEFAULT_PROVIDER,
    )
    parser.add_argument("-m", "--model", help="Override default model")

    args = parser.parse_args()
    if not args.goal and not args.files:
        parser.print_help()
        sys.exit(0)

    active_model = args.model or get_default_model(args.provider)

    goal_text = " ".join(args.goal)
    file_context = read_files_context(args.files) if args.files else ""

    system_prompt = (
        "You are an AI Agent Planner. Your goal is to generate a comprehensive technical implementation plan in Markdown. "
        f"Environment: {get_system_context()}. "
        "Rules:\n"
        "1. DO NOT provide any part of the plan if you still have questions or need clarification.\n"
        "2. If you need more information, ask your questions first. Start these responses with 'QUESTION:'.\n"
        "3. Once you are ready, provide the plan. Start this response with 'PLAN:'.\n"
        "4. Any plan must begin with a '# Implementation Plan: [Goal Name]' title.\n"
        "5. Your entire response should be plain Markdown. DO NOT wrap the response in triple backticks.\n"
        "6. Strategy Selection:\n"
        "   - Documentation Mode: If context is primarily requirements/docs, act as a Solutions Architect. Focus on high-level architecture and data flows.\n"
        "   - Code Mode: If context is source code, act as a Senior Developer. Focus on implementation details and refactoring.\n"
        "7. Iterative Logic: If feedback is provided, acknowledge change requests and update relevant sections while maintaining integrity.\n"
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Goal: {goal_text}\n\nContext:\n{file_context}",
        },
    ]

    print(
        f"{BLUE}🤖 Planning with {BOLD}{active_model}{RESET} ({args.provider})...{RESET}"
    )

    while True:
        print(f"{CYAN}🔍 Thinking...{RESET}", end="\r")
        response = call_ai(messages, args.provider, active_model)
        sys.stdout.write("\033[2K\r")

        if not response:
            print(f"{RED}No response generated.{RESET}")
            break

        response = clean_markdown(response)
        clean_response = response.strip()

        # Handle Questions
        if clean_response.upper().startswith("QUESTION:"):
            display_text = clean_response[9:].strip()
            print(f"\n{YELLOW}🤔 Question:{RESET} {display_text}")
            try:
                ans = input(f"\n{BOLD}Answer ('exit' to quit): {RESET}").strip()
                if ans.lower() in ["exit", "quit"]:
                    break
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": ans})
                continue
            except KeyboardInterrupt:
                break

        # Handle Plan
        if "PLAN:" in clean_response.upper():
            # Find the start of the plan (case insensitive)
            plan_marker = "PLAN:"
            idx = clean_response.upper().find(plan_marker)
            final_plan = clean_markdown(
                clean_response[idx + len(plan_marker) :].strip()
            )

            print(f"\n{GREEN}✅ Proposed Plan:{RESET}\n\n{final_plan}\n")

            print(
                f"{CYAN}🔄 [{BOLD}f{RESET}]eedback to improve, [{BOLD}s{RESET}]ave and exit, or [{BOLD}q{RESET}]uit?{RESET}"
            )
            choice = input("> ").lower().strip()

            if choice == "s":
                save_to_file(final_plan, prefix="plan")
                break
            elif choice == "f":
                feedback = input(f"{BOLD}What should be changed? {RESET}").strip()
                messages.append({"role": "assistant", "content": response})
                messages.append(
                    {
                        "role": "user",
                        "content": f"Improve the plan with this feedback: {feedback}",
                    }
                )
                continue
            else:
                break

        # Fallback for responses that don't follow markers
        final_plan = clean_markdown(clean_response)
        print(f"\n{final_plan}\n")

        print(
            f"{CYAN}🔄 [{BOLD}f{RESET}]eedback to improve, [{BOLD}s{RESET}]ave and exit, or [{BOLD}q{RESET}]uit?{RESET}"
        )
        choice = input("> ").lower().strip()

        if choice == "s":
            save_to_file(final_plan, prefix="plan")
            break
        elif choice == "f":
            feedback = input(f"{BOLD}What should be changed? {RESET}").strip()
            messages.append({"role": "assistant", "content": response})
            messages.append(
                {
                    "role": "user",
                    "content": f"Improve the plan with this feedback: {feedback}",
                }
            )
            continue
        else:
            break


if __name__ == "__main__":
    main()
