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

from ai_core.colors import YELLOW, BLUE, RED, GREEN, RESET, BOLD
from ai_core.utils import get_system_context, read_files_context
from ai_core.config import (
    DEFAULT_PROVIDER,
    RESEARCH_PROVIDER,
    RESEARCH_MODEL,
    PLANNER_PROVIDER,
    PLANNER_MODEL,
    get_default_model,
    DEFAULT_THINKING_BUDGET,
)


async def main():
    # Get the directory where this script is located for sibling calls
    base_dir = os.path.dirname(os.path.abspath(__file__))

    parser = argparse.ArgumentParser(description="AI Master Orchestrator")
    parser.add_argument("goal", nargs="+", help="The goal to research and plan")
    parser.add_argument(
        "-f", "--files", nargs="*", help="Local context files (code or docs)"
    )
    parser.add_argument(
        "--no-search", action="store_true", help="Skip the web research phase"
    )
    # Global overrides (legacy / convenience)
    parser.add_argument(
        "-p", "--provider", default=DEFAULT_PROVIDER, help="Global AI Provider"
    )
    parser.add_argument("-m", "--model", help="Global AI Model override")
    parser.add_argument(
        "-t",
        "--thinking",
        type=int,
        default=DEFAULT_THINKING_BUDGET,
        help="Global thinking budget (tokens)",
    )

    # Phase-specific overrides
    parser.add_argument("--rp", "--research-provider", help="Research phase provider")
    parser.add_argument("--rm", "--research-model", help="Research phase model")
    parser.add_argument("--pp", "--plan-provider", help="Planning phase provider")
    parser.add_argument("--pm", "--plan-model", help="Planning phase model")

    args = parser.parse_args()

    # Resolve phase-specific settings
    # Priority: CLI phase flag > CLI global flag > Env var > Default Provider
    r_provider = args.rp or (
        args.provider if args.provider != DEFAULT_PROVIDER else RESEARCH_PROVIDER
    )
    r_model = args.rm or args.model
    if not r_model:
        r_model = (
            RESEARCH_MODEL
            if r_provider == RESEARCH_PROVIDER
            else get_default_model(r_provider)
        )

    p_provider = args.pp or (
        args.provider if args.provider != DEFAULT_PROVIDER else PLANNER_PROVIDER
    )
    p_model = args.pm or args.model
    if not p_model:
        p_model = (
            PLANNER_MODEL
            if p_provider == PLANNER_PROVIDER
            else get_default_model(p_provider)
        )

    goal_text = " ".join(args.goal)
    research_summary = ""

    # --- PHASE 1: RESEARCH ---
    if not args.no_search:
        print(f"\n{BLUE}🛰️  Phase 1: Researching Topic via SearXNG...{RESET}")
        print(
            f"   Using: {BOLD}{r_provider}{RESET}"
            + (f" ({r_model})" if r_model else "")
        )
        try:
            research_script = os.path.join(base_dir, "ai-agent-researcher.py")
            research_cmd = [
                sys.executable,
                research_script,
                goal_text,
                "-p",
                r_provider,
                "--agentic",
                "-t",
                str(args.thinking),
            ]
            if r_model:
                research_cmd += ["-m", r_model]

            # Stream output in real-time so the user sees progress
            proc = subprocess.Popen(
                research_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            full_output = []
            is_reporting = False
            for line in proc.stdout:
                # Once we hit the final report, stop streaming to terminal
                # (but keep capturing for the master context)
                if "FINAL REPORT:" in line:
                    is_reporting = True

                if not is_reporting:
                    sys.stdout.write(line)
                    sys.stdout.flush()

                full_output.append(line)

            proc.wait()
            combined_output = "".join(full_output)

            if "FINAL REPORT:" in combined_output:
                # Capture everything after the FINAL REPORT header
                parts = combined_output.split("FINAL REPORT:")
                research_summary = parts[1].strip()
                print(f"\n{GREEN}✅ Research completed.{RESET}")
            else:
                print(
                    f"\n{YELLOW}⚠️  Research returned no summary. Moving to local context.{RESET}"
                )
        except Exception as e:
            print(f"\n{RED}❌ Research phase failed: {e}{RESET}")

    # --- PHASE 2: MASTER CONTEXT ASSEMBLY ---
    print(f"{BLUE}📂 Phase 2: Assembling Master Context...{RESET}")
    local_context = read_files_context(args.files) if args.files else ""

    master_context = f"""
### MISSION GOAL
{goal_text}

### SYSTEM CONTEXT
{get_system_context()}

### EXTERNAL RESEARCH (WEB DATA)
{research_summary if research_summary else "N/A - Skip Research"}

### LOCAL CONTEXT (FILES)
{local_context if local_context else "No local files provided."}
"""

    # --- PHASE 3: PLANNING HANDOFF ---
    print(f"{BLUE}🧠 Phase 3: Launching Planner Agent...{RESET}")
    print(f"   Using: {BOLD}{p_provider}{RESET}" + (f" ({p_model})" if p_model else ""))
    tmp_file = os.path.join(base_dir, ".master_context.tmp")
    req_file = os.path.join(base_dir, ".research_request.tmp")
    research_iterations = 0
    max_iterations = 3

    try:
        while True:
            with open(tmp_file, "w", encoding="utf-8") as f:
                f.write(master_context)

            planner_script = os.path.join(base_dir, "ai-agent-planner.py")
            planner_cmd = [
                sys.executable,
                planner_script,
                "Refer to the master context file for full mission details",
                "-f",
                tmp_file,
                "-p",
                p_provider,
                "-t",
                str(args.thinking),
            ]
            if p_model:
                planner_cmd += ["-m", p_model]

            # Use subprocess.run with check=False to read the return code
            proc = subprocess.run(planner_cmd)

            if proc.returncode == 2:
                # Planner requested additional research
                if os.path.exists(req_file):
                    with open(req_file, "r", encoding="utf-8") as rf:
                        query = rf.read().strip()
                    os.remove(req_file)

                    if research_iterations < max_iterations:
                        research_iterations += 1
                        print(
                            f"\n{BLUE}🔄 Orchestrator: Dynamic Research Triggered ({research_iterations}/{max_iterations}){RESET}"
                        )
                        print(f"   Query: {YELLOW}{query}{RESET}\n")

                        # Run researcher
                        research_script = os.path.join(
                            base_dir, "ai-agent-researcher.py"
                        )
                        research_cmd = [
                            sys.executable,
                            research_script,
                            query,
                            "-p",
                            r_provider,
                            "--agentic",
                            "-t",
                            str(args.thinking),
                        ]
                        if r_model:
                            research_cmd += ["-m", r_model]

                        research_proc = subprocess.Popen(
                            research_cmd,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,
                            text=True,
                            bufsize=1,
                            universal_newlines=True,
                        )

                        full_output = []
                        is_reporting = False
                        for line in research_proc.stdout:
                            if "FINAL REPORT:" in line:
                                is_reporting = True
                            if not is_reporting:
                                sys.stdout.write(line)
                                sys.stdout.flush()
                            full_output.append(line)

                        research_proc.wait()
                        combined_output = "".join(full_output)

                        if "FINAL REPORT:" in combined_output:
                            parts = combined_output.split("FINAL REPORT:")
                            new_summary = parts[1].strip()
                            master_context += f"\n\n### ADDITIONAL RESEARCH (ITERATION {research_iterations})\n{new_summary}\n"
                            print(
                                f"{GREEN}✅ Dynamic context updated. Reigniting Planner...{RESET}\n"
                            )
                        else:
                            print(
                                f"{YELLOW}⚠️  Dynamic research failed. Reigniting Planner...{RESET}\n"
                            )
                            master_context += f"\n\n### ADDITIONAL RESEARCH FAILED\nSearched for {query} but found nothing.\n"
                        continue  # Loop back to planner
                    else:
                        print(
                            f"\n{RED}🛑 Max research iterations ({max_iterations}) reached.{RESET}"
                        )
                        master_context += f"\n\n### SYSTEM LIMITATION\nWe have reached the maximum allowed automated research runs ({max_iterations}). Based on the information gathered so far, provide the best complete plan you can.\n"
                        continue  # Loop back to planner with warning
                else:
                    print(f"{RED}❌ Expected research query file not found.{RESET}")
                    break
            else:
                # Normal exit or quit
                break

    except Exception as e:
        print(f"{RED}❌ Planning phase failed: {e}{RESET}")
    finally:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)
        if os.path.exists(req_file):
            os.remove(req_file)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{RED}Orchestration aborted.{RESET}")
        sys.exit(0)
