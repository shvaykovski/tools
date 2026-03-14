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
from ai_core.utils import get_system_context, read_files, save_to_file
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
    file_context = read_files(args.files) if args.files else ""

    system_prompt = (
        "You are an AI Agent Planner. Your goal is to generate a comprehensive technical implementation plan in Markdown. "
        f"Context: {get_system_context()}. "
        "Rules:\n"
        "1. DO NOT provide any part of the plan if you still have questions or need clarification.\n"
        "2. If you need more information, ask your questions first. Start these responses with 'QUESTION:'.\n"
        "3. Once (and ONLY once) you have all necessary info, provide the full final plan. Start this response with 'PLAN:'.\n"
        "4. Any plan must begin with a '# Implementation Plan: [Goal Name]' title.\n"
        "5. Keep responses focused: EITHER ask questions OR provide the plan. Never both in one response."
    )

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"Goal: {goal_text}\n\nFiles Context:\n{file_context}",
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

        clean_response = response.strip()
        
        # Check for QUESTION
        if clean_response.upper().startswith("QUESTION:") or "QUESTION:" in clean_response.split('\n')[-1].upper():
            # If it's a long response but the last line is a question, or it starts with it
            display_text = clean_response
            if clean_response.upper().startswith("QUESTION:"):
                display_text = clean_response[9:].strip()
            
            print(f"\n{YELLOW}🤔 Question:{RESET} {display_text}")
            try:
                ans = input(f"\n{BOLD}Answer ('exit' to quit): {RESET}").strip()
                if ans.lower() in ["exit", "quit"]:
                    break
                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": ans})
                continue # Go back to Thinking...
            except KeyboardInterrupt:
                break
        
        # Check for PLAN
        if clean_response.upper().startswith("PLAN:"):
            final_plan = clean_response[5:].strip()
            print(f"\n{GREEN}✅ Final Plan Generated:{RESET}\n\n{final_plan}\n")
            save_to_file(final_plan, prefix="plan")
            break
            
        # Default behavior: treat as final plan but print as is
        print(f"\n{response}\n")
        save_to_file(response, prefix="plan")
        break


if __name__ == "__main__":
    main()
