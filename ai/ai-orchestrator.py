#!/usr/bin/env python3

"""
AI Master Orchestrator
Chains the Research Agent and Planner Agent into a unified agentic flow.

Usage:
    python3 ai-orchestrator.py "Build a RAG system with ChromaDB" -f spec.md
    python3 ai-orchestrator.py "How to deploy to fly.io" --no-search

Logic:
    1. Runs Researcher: Scrapes web docs and creates a summary.
    2. Context Assembly: Merges search summary with local code/docs (Head & Tail).
    3. Triggers Planner: Starts the interactive loop to build and refine the plan.
"""

import sys
import os
import subprocess
import argparse
import asyncio

# ANSI Colors for consistency with ai-helper.py
#
YELLOW, BLUE, RED, CYAN, GREEN, RESET, BOLD = (
    "\033[1;33m",
    "\033[1;34m",
    "\033[1;31m",
    "\033[0;36m",
    "\033[0;32m",
    "\033[0m",
    "\033[1m",
)


def read_file_smart(fpath, max_chars=15000):
    """Smart reader: Extracts the beginning and end of large files to save context."""
    if not os.path.exists(fpath):
        return ""
    try:
        with open(fpath, "r", encoding="utf-8") as f:
            content = f.read()
        if len(content) <= max_chars:
            return content
        # Take 40% from head and 40% from tail
        head = int(max_chars * 0.4)
        tail = int(max_chars * 0.4)
        return f"{content[:head]}\n\n[... TRUNCATED {len(content)-max_chars} CHARS ...]\n\n{content[-tail:]}"
    except Exception as e:
        return f"[Error reading {fpath}: {e}]"


async def main():
    parser = argparse.ArgumentParser(description="AI Master Orchestrator")
    parser.add_argument("goal", nargs="+", help="The goal to research and plan")
    parser.add_argument(
        "-f", "--files", nargs="*", help="Local context files (code or docs)"
    )
    parser.add_argument(
        "--no-search", action="store_true", help="Skip the web research phase"
    )
    parser.add_argument("-p", "--provider", default="openai", help="AI Provider")
    parser.add_argument("-m", "--model", help="Override default model")
    args = parser.parse_args()

    goal_text = " ".join(args.goal)
    research_summary = ""

    # --- PHASE 1: RESEARCH ---
    if not args.no_search:
        print(f"\n{BLUE}🛰️  Phase 1: Researching Topic...{RESET}")
        try:
            # Run the researcher script as a subprocess
            # We assume it's named ai-agent-researcher.py in the same folder
            research_cmd = [
                sys.executable,
                "ai-agent-researcher.py",
                goal_text,
                "-p",
                args.provider,
            ]
            if args.model:
                research_cmd += ["-m", args.model]

            proc = subprocess.run(research_cmd, capture_output=True, text=True)

            if "FINAL RESEARCH REPORT:" in proc.stdout:
                research_summary = proc.stdout.split("FINAL RESEARCH REPORT:")[
                    1
                ].strip()
                print(f"{GREEN}✅ Research completed with external sources.{RESET}")
            else:
                print(
                    f"{YELLOW}⚠️  Research returned no summary. Moving to local context.{RESET}"
                )
        except Exception as e:
            print(f"{RED}❌ Research phase failed: {e}{RESET}")

    # --- PHASE 2: MASTER CONTEXT ASSEMBLY ---
    print(f"{BLUE}📂 Phase 2: Assembling Master Context...{RESET}")
    local_context = ""
    if args.files:
        for f in args.files:
            content = read_file_smart(f)
            local_context += f"\n--- SOURCE FILE: {f} ---\n{content}\n"

    master_context = f"""
### MISSION GOAL
{goal_text}

### EXTERNAL RESEARCH (WEB DATA)
{research_summary if research_summary else "N/A - Skip Research"}

### LOCAL CONTEXT (FILES)
{local_context if local_context else "No local files provided."}
"""

    # --- PHASE 3: PLANNING HANDOFF ---
    print(f"{BLUE}🧠 Phase 3: Launching Planner Agent...{RESET}")
    tmp_file = ".master_context.tmp"
    try:
        with open(tmp_file, "w") as f:
            f.write(master_context)

        # We invoke the planner agent, passing the master context as a file
        planner_cmd = f"python3 ai-agent-planner.py 'Refer to the master context file for full mission details' -f {tmp_file} -p {args.provider}"
        if args.model:
            planner_cmd += f" -m {args.model}"

        # Use os.system to maintain the interactive input/output for the loop
        os.system(planner_cmd)

    finally:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{RED}Orchestration aborted.{RESET}")
        sys.exit(0)
