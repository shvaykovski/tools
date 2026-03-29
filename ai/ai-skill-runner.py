#!/usr/bin/env python3

"""
AI Skill Runner
Discovers Claude Code skills and agents, uses them as system prompts with any AI provider.
Supports auto-routing: automatically picks the best skill/agent for the user's request.

Prerequisites:
    - Python 3.x
    - Access to at least one supported AI provider (OpenAI, Anthropic, OpenRouter, Google, or Ollama)
    - Local 'ai_core' package
    - Skills in ~/.claude/skills/*/SKILL.md
    - Agents in ~/.claude/agents/*.md

Environment Variables:
    export OPENAI_API_KEY="your_key"
    export ANTHROPIC_API_KEY="your_key"
    export OPENROUTER_API_KEY="your_key"
    export GOOGLE_AI_API_KEY="your_key"

Usage:
    python3 ai-skill-runner.py --list                          # List available skills/agents
    python3 ai-skill-runner.py --list --agents                 # List agents only
    python3 ai-skill-runner.py "Review this code for bugs"     # Auto-route to best skill/agent
    python3 ai-skill-runner.py code-reviewer "Review this"     # Explicit skill/agent name
    python3 ai-skill-runner.py code-reviewer -i                # Interactive multi-turn session
    echo "code" | python3 ai-skill-runner.py "review this"     # Stdin as context
    python3 ai-skill-runner.py -p anthropic "Explore auth"     # Use specific provider

Flags:
    --list           List all discovered skills and agents
    --skills         Filter listing to skills only
    --agents         Filter listing to agents only
    -i, --interactive  Multi-turn conversation mode
    -p, --provider   AI provider (openai, anthropic, openrouter, google, or ollama)
    -m, --model      Override the default model name for the provider
    -t, --thinking   Thinking budget (integer tokens). Default 0.
    -j, --json       Output result in structured JSON format
    --store          Save the output to a timestamped file
    -a, --agentic    Optimize output for agentic chain (stripped formatting)
    --refs           Include reference/example files from skill directories
"""

import argparse
import glob
import json
import os
import sys
from typing import Dict, List, Optional, Tuple

from ai_core.ai_client import call_ai
from ai_core.colors import BLUE, BOLD, CYAN, GREEN, RED, RESET, YELLOW, format_markdown
from ai_core.config import DEFAULT_PROVIDER, DEFAULT_THINKING_BUDGET, get_default_model
from ai_core.utils import clean_markdown, read_file_smart, save_to_file

SKILLS_DIR: str = os.path.expanduser("~/.claude/skills")
AGENTS_DIR: str = os.path.expanduser("~/.claude/agents")


def parse_frontmatter(file_path: str) -> Tuple[Dict[str, object], str]:
    """Parse YAML frontmatter and markdown body from a file.

    Args:
        file_path: Absolute path to the markdown file.

    Returns:
        Tuple of (metadata dict, body string).
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content: str = f.read()
    except Exception:
        return {}, ""

    if not content.startswith("---"):
        return {}, content.strip()

    # Find closing ---
    end_idx: int = content.find("---", 3)
    if end_idx == -1:
        return {}, content.strip()

    yaml_block: str = content[3:end_idx].strip()
    body: str = content[end_idx + 3 :].strip()

    metadata: Dict[str, object] = {}
    for line in yaml_block.splitlines():
        line = line.partition("#")[0].strip()  # Strip comments
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # Handle list syntax: [item1, item2] or - item1
        if value.startswith("[") and value.endswith("]"):
            value = [
                v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()
            ]
        elif value.startswith("'") or value.startswith('"'):
            value = value.strip("'\"")
        metadata[key] = value

    return metadata, body


def discover_skills() -> List[Dict[str, object]]:
    """Discover skills from ~/.claude/skills/*/SKILL.md.

    Returns:
        List of skill dicts with name, type, description, body, source_path, etc.
    """
    items: List[Dict[str, object]] = []
    pattern: str = os.path.join(SKILLS_DIR, "*", "SKILL.md")

    for path in sorted(glob.glob(pattern)):
        meta, body = parse_frontmatter(path)
        name: str = meta.get("name", "")
        if not name:
            # Derive name from directory
            name = os.path.basename(os.path.dirname(path))
        if not name:
            continue

        skill_dir: str = os.path.dirname(path)
        refs_dir: str = os.path.join(skill_dir, "references")
        examples_dir: str = os.path.join(skill_dir, "examples")
        scripts_dir: str = os.path.join(skill_dir, "scripts")

        items.append(
            {
                "name": name,
                "type": "skill",
                "description": meta.get("description", ""),
                "body": body,
                "source_path": path,
                "tools": meta.get("tools", []),
                "references_dir": refs_dir if os.path.isdir(refs_dir) else None,
                "examples_dir": examples_dir if os.path.isdir(examples_dir) else None,
                "scripts_dir": scripts_dir if os.path.isdir(scripts_dir) else None,
            }
        )

    return items


def discover_agents() -> List[Dict[str, object]]:
    """Discover agents from ~/.claude/agents/*.md.

    Returns:
        List of agent dicts with name, type, description, body, source_path, etc.
    """
    items: List[Dict[str, object]] = []
    pattern: str = os.path.join(AGENTS_DIR, "*.md")

    for path in sorted(glob.glob(pattern)):
        meta, body = parse_frontmatter(path)
        name: str = meta.get("name", "")
        if not name:
            # Derive name from filename
            name = os.path.splitext(os.path.basename(path))[0]
        if not name:
            continue

        items.append(
            {
                "name": name,
                "type": "agent",
                "description": meta.get("description", ""),
                "body": body,
                "source_path": path,
                "tools": meta.get("tools", []),
                "model": meta.get("model"),
                "color": meta.get("color"),
                "references_dir": None,
                "examples_dir": None,
                "scripts_dir": None,
            }
        )

    return items


class SkillRunner:
    """Discovers and runs Claude Code skills/agents via any AI provider."""

    def __init__(
        self,
        provider: str = DEFAULT_PROVIDER,
        model: Optional[str] = None,
        json_mode: bool = False,
        thinking_budget: int = 0,
        include_refs: bool = False,
        agentic_mode: bool = False,
    ):
        self.provider: str = provider
        self.model: str = model or get_default_model(provider)
        self.json_mode: bool = json_mode
        self.thinking_budget: int = thinking_budget
        self.include_refs: bool = include_refs
        self.agentic_mode: bool = agentic_mode
        self.execution_enabled: bool = True

    def log(self, message: str, color: Optional[str] = None) -> None:
        """Print to stderr in json mode, stdout otherwise."""
        if color:
            message = f"{color}{message}{RESET}"
        if self.json_mode:
            print(message, file=sys.stderr)
        else:
            print(message)

    def discover(self) -> List[Dict[str, object]]:
        """Discover all available skills and agents.

        Returns:
            Combined list of skill and agent dicts.
        """
        items: List[Dict[str, object]] = discover_skills() + discover_agents()
        return items

    def list_items(
        self, items: List[Dict[str, object]], filter_type: Optional[str] = None
    ) -> None:
        """Pretty-print discovered skills and agents.

        Args:
            items: List of skill/agent dicts.
            filter_type: Optional filter — "skill" or "agent".
        """
        filtered: List[Dict[str, object]] = items
        if filter_type:
            filtered = [it for it in items if it["type"] == filter_type]

        if not filtered:
            self.log(f"{YELLOW}No items found.{RESET}")
            return

        self.log(f"\n{BOLD}{BLUE}Available Skills & Agents{RESET}\n")
        self.log(f"  {'Type':<8} {'Name':<25} {'Description'}")
        self.log(f"  {'─' * 8} {'─' * 25} {'─' * 50}")

        for item in filtered:
            type_str: str = item["type"]
            color: str = CYAN if type_str == "skill" else YELLOW
            desc: str = item.get("description", "")
            # Truncate long descriptions
            if len(desc) > 80:
                desc = desc[:77] + "..."
            self.log(
                f"  {color}{type_str:<8}{RESET} {BOLD}{item['name']:<25}{RESET} {desc}"
            )

        self.log(f"\n  {len(filtered)} item(s) found.\n")

    def resolve(
        self, name: str, items: List[Dict[str, object]]
    ) -> Optional[Dict[str, object]]:
        """Resolve a name to a specific skill or agent.

        Supports qualified syntax: 'agent:name' or 'skill:name'.

        Args:
            name: Skill/agent name, optionally qualified with type prefix.
            items: List of all discovered items.

        Returns:
            Matched item dict, or None if not found.
        """
        # Handle type-qualified names: "agent:code-reviewer" or "skill:my-skill"
        type_filter: Optional[str] = None
        search_name: str = name
        if ":" in name:
            prefix, _, search_name = name.partition(":")
            if prefix in ("agent", "skill"):
                type_filter = prefix

        matches: List[Dict[str, object]] = []
        for item in items:
            if type_filter and item["type"] != type_filter:
                continue
            if item["name"] == search_name:
                matches.append(item)

        if len(matches) == 1:
            return matches[0]
        elif len(matches) == 0:
            self.log(
                f"{RED}No skill or agent named '{name}' found. "
                f"Run with --list to see available options.{RESET}"
            )
            return None
        else:
            self.log(f"{YELLOW}Ambiguous name '{name}'. Multiple matches:{RESET}")
            for m in matches:
                self.log(f"  - {m['type']}:{m['name']} ({m['source_path']})")
            self.log(
                f"\nUse 'agent:{search_name}' or 'skill:{search_name}' to disambiguate."
            )
            return None

    def auto_route(
        self, user_prompt: str, items: List[Dict[str, object]]
    ) -> Optional[Dict[str, object]]:
        """Use AI to pick the best skill/agent for the user's request.

        Args:
            user_prompt: The user's request text.
            items: List of all discovered items.

        Returns:
            Best matching item, or None if no good match.
        """
        if not items:
            return None

        self.log(
            f"{BLUE}🔀 Auto-routing to best skill/agent using {BOLD}{self.model}{RESET}...{RESET}"
        )

        catalog: str = "\n".join(
            f"- {it['name']} ({it['type']}): {it.get('description', '')[:200]}"
            for it in items
        )

        system_prompt: str = (
            "Pick the single best skill or agent for the user's request from the list below. "
            "Return ONLY the exact name, nothing else. If none fit well, return 'none'."
        )
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Available:\n{catalog}\n\nRequest: {user_prompt}",
            },
        ]

        chosen_raw: str = call_ai(
            messages,
            self.provider,
            self.model,
            max_tokens=100,
            thinking_budget=0,
        )
        chosen: str = (
            clean_markdown(chosen_raw).strip().lower() if chosen_raw else "none"
        )

        if chosen == "none" or not chosen:
            self.log(
                f"   {YELLOW}No matching skill/agent found. Using generic mode.{RESET}"
            )
            return None

        # Match against known names
        for item in items:
            if item["name"].lower() == chosen:
                self.log(
                    f"   {GREEN}Selected: {BOLD}{item['name']}{RESET} ({item['type']}){RESET}"
                )
                return item

        # Fuzzy match: check if chosen is contained in any name
        for item in items:
            if chosen in item["name"].lower() or item["name"].lower() in chosen:
                self.log(
                    f"   {GREEN}Selected: {BOLD}{item['name']}{RESET} ({item['type']}){RESET}"
                )
                return item

        self.log(
            f"   {YELLOW}AI suggested '{chosen}' but no match found. Using generic mode.{RESET}"
        )
        return None

    def execute_command(self, lang: str, code: str, script_dir: Optional[str]) -> str:
        """Execute a block of code (bash, python, node) safely.

        Args:
            lang: Programming language / shell (bash, python, node).
            code: The code to run.
            script_dir: Optional directory with project scripts.

        Returns:
            Combined stdout/stderr output.
        """
        import subprocess
        import tempfile

        if lang in ("python", "py"):
            ext = ".py"
            cmd_prefix = ["python3"]
        elif lang in ("node", "js", "javascript"):
            ext = ".js"
            cmd_prefix = ["node"]
        else:
            ext = ".sh"
            cmd_prefix = ["bash"]

        with tempfile.NamedTemporaryFile(suffix=ext, mode="w", delete=True) as f:
            f.write(code)
            f.flush()

            # Set environment to include script dir in PATH or Python/Node search paths
            env = os.environ.copy()
            if script_dir:
                if lang in ("python", "py"):
                    env["PYTHONPATH"] = (
                        f"{script_dir}:{env.get('PYTHONPATH', '')}"
                    ).strip(":")
                elif lang in ("node", "js", "javascript"):
                    env["NODE_PATH"] = (
                        f"{script_dir}:{env.get('NODE_PATH', '')}"
                    ).strip(":")
                env["PATH"] = f"{script_dir}:{env.get('PATH', '')}"

            try:
                result = subprocess.run(
                    cmd_prefix + [f.name],
                    capture_output=True,
                    text=True,
                    env=env,
                    timeout=30,
                    cwd=os.getcwd(),
                )
                output = result.stdout + result.stderr
                return output if output else "[Process exited with code 0, no output]"
            except subprocess.TimeoutExpired:
                return "[Error: Command timed out after 30 seconds]"
            except Exception as e:
                return f"[Error: {str(e)}]"

    def build_system_prompt(self, item: Dict[str, object]) -> str:
        """Build the system prompt from a skill/agent body, including references and scripts.

        Args:
            item: Skill/agent dict.

        Returns:
            Complete system prompt string.
        """
        prompt: str = ""

        if item:
            item_type: str = item.get("type", "item")
            item_name: str = item.get("name", "generic")
            prompt += f"# Role: {item_name.upper()} ({item_type})\n\n"
            prompt += item.get("body", "")

            # Load scripts discovery
            scripts_dir: Optional[str] = item.get("scripts_dir")
            if scripts_dir and os.path.isdir(scripts_dir):
                scripts = [
                    f
                    for f in os.listdir(scripts_dir)
                    if os.path.isfile(os.path.join(scripts_dir, f))
                ]
                if scripts:
                    prompt += (
                        f"\n\n## Available Scripts (Directory: `{scripts_dir}`):\n"
                    )
                    for script in sorted(scripts):
                        prompt += f"- `{script}`\n"
                    prompt += (
                        f"\nNOTE: You can execute these scripts or any bash/python/node code using markdown blocks. "
                        f"If you need to run one of the listed scripts, use its absolute path: `{scripts_dir}/<script_name>`. "
                        "Wrap your code in ```bash, ```python, or ```node blocks. "
                        "The results will be provided back to you automatically."
                    )

            if self.include_refs:
                # Load references and examples
                for dir_key, header in [
                    ("references_dir", "Reference"),
                    ("examples_dir", "Example"),
                ]:
                    ref_dir: Optional[str] = item.get(dir_key)
                    if ref_dir and os.path.isdir(ref_dir):
                        for ref_file in sorted(glob.glob(os.path.join(ref_dir, "*"))):
                            # Only include common text/code extensions
                            if not any(
                                ref_file.lower().endswith(ext)
                                for ext in [".md", ".py", ".js", ".txt", ".json"]
                            ):
                                continue
                            ref_name: str = os.path.basename(ref_file)
                            ref_content: str = read_file_smart(
                                ref_file, max_chars=10000
                            )
                            prompt += f"\n\n### {header}: {ref_name}\n{ref_content}"

        return prompt

    def run_single(
        self,
        item: Optional[Dict[str, object]],
        user_prompt: str,
        stdin_context: str = "",
    ) -> str:
        """Execute a single-shot call with the skill/agent as system prompt.

        Args:
            item: Skill/agent dict (None for generic mode).
            user_prompt: The user's request.
            stdin_context: Optional piped stdin content.

        Returns:
            AI response text.
        """
        messages: List[Dict[str, str]] = []

        if item:
            system_prompt: str = self.build_system_prompt(item)
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

        # Build user message
        user_content: str = ""
        if stdin_context:
            user_content += f"Context:\n```\n{stdin_context}\n```\n\n"
        user_content += user_prompt

        messages.append({"role": "user", "content": user_content})

        item_name: str = item["name"] if item else "generic"
        scripts_dir: Optional[str] = item.get("scripts_dir") if item else None

        self.log(
            f"🚀 Running {BOLD}{item_name}{RESET} with {BOLD}{self.model}{RESET} "
            f"({self.provider})..."
        )

        loop_count = 0
        while loop_count < 5:  # Max 5 loops
            loop_count += 1
            response: str = call_ai(
                messages,
                self.provider,
                self.model,
                max_tokens=4096,
                thinking_budget=self.thinking_budget,
            )

            if not response:
                return ""

            # Execution check
            import re

            code_match = re.search(
                r"```(bash|python|py|node|js)\n(.*?)```", response, re.DOTALL
            )

            if code_match:
                lang = code_match.group(1)
                code = code_match.group(2).strip()

                self.log(f"   ⚙️  Executing {BOLD}{lang}{RESET} code...", BLUE)
                output = self.execute_command(lang, code, scripts_dir)
                self.log(
                    f"   ✅ Execution finished. Output: {len(output)} chars.", BLUE
                )

                messages.append({"role": "assistant", "content": response})
                messages.append({"role": "user", "content": f"OBSERVATION:\n{output}"})
                continue
            else:
                return clean_markdown(response)

        return "[Error: Maximum execution loop count reached (5)]"

    def run_interactive(
        self,
        item: Optional[Dict[str, object]],
        stdin_context: str = "",
    ) -> str:
        """Run an interactive multi-turn session with the skill/agent.

        Args:
            item: Skill/agent dict (None for generic mode).
            stdin_context: Optional piped stdin content.

        Returns:
            Full conversation text for optional saving.
        """
        messages: List[Dict[str, str]] = []

        if item:
            system_prompt: str = self.build_system_prompt(item)
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

        if stdin_context:
            messages.append(
                {"role": "user", "content": f"Context:\n```\n{stdin_context}\n```"}
            )
            messages.append(
                {
                    "role": "assistant",
                    "content": "I've received the context. How can I help?",
                }
            )

        item_name: str = item["name"] if item else "generic"
        self.log(
            f"\n{BLUE}💬 Interactive session with {BOLD}{item_name}{RESET} "
            f"({self.model} / {self.provider}){RESET}"
        )
        self.log("   Type 'exit' or 'quit' to end. Ctrl+C to abort.\n")

        conversation_log: str = ""

        while True:
            try:
                user_input: str = input(f"{GREEN}{BOLD}> {RESET}").strip()
                if user_input.lower() in ("exit", "quit"):
                    break
                if not user_input:
                    continue

                messages.append({"role": "user", "content": user_input})
                conversation_log += f"\n**User:** {user_input}\n"

                scripts_dir = item.get("scripts_dir") if item else None

                while True:
                    response: str = call_ai(
                        messages,
                        self.provider,
                        self.model,
                        max_tokens=4096,
                        thinking_budget=self.thinking_budget,
                    )

                    if not response:
                        self.log(f"No response received.", RED)
                        messages.pop()
                        break

                    # Execution check
                    import re

                    code_match = re.search(
                        r"```(bash|python|py|node|js)\n(.*?)```", response, re.DOTALL
                    )

                    if code_match:
                        lang = code_match.group(1)
                        code = code_match.group(2).strip()

                        # Print the thinking/response so far (clearing markdown if not JSON)
                        print(f"\n{format_markdown(response)}\n")

                        self.log(f"   ⚙️  Executing {BOLD}{lang}{RESET} code...", BLUE)
                        output = self.execute_command(lang, code, scripts_dir)
                        self.log(
                            f"   ✅ Execution finished. Output: {len(output)} chars.",
                            BLUE,
                        )

                        messages.append({"role": "assistant", "content": response})
                        messages.append(
                            {"role": "user", "content": f"OBSERVATION:\n{output}"}
                        )
                        # Continue loop to let AI see observation
                        continue
                    else:
                        response = clean_markdown(response)
                        messages.append({"role": "assistant", "content": response})
                        conversation_log += f"\n**Assistant:** {response}\n"
                        print(f"\n{format_markdown(response)}\n")
                        break

            except (KeyboardInterrupt, EOFError):
                print()
                break

        return conversation_log


def main() -> None:
    parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="AI Skill Runner — Run Claude Code skills and agents via any AI provider"
    )
    parser.add_argument(
        "args", nargs="*", help="[skill/agent name] [prompt...] or just [prompt...]"
    )
    parser.add_argument(
        "--list", action="store_true", help="List available skills/agents"
    )
    parser.add_argument(
        "--skills", action="store_true", help="Filter listing to skills only"
    )
    parser.add_argument(
        "--agents", action="store_true", help="Filter listing to agents only"
    )
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Multi-turn conversation mode"
    )
    parser.add_argument(
        "-p",
        "--provider",
        choices=["openai", "anthropic", "openrouter", "ollama", "google"],
        default=DEFAULT_PROVIDER,
    )
    parser.add_argument("-m", "--model", help="Override AI model")
    parser.add_argument(
        "-t",
        "--thinking",
        type=int,
        default=DEFAULT_THINKING_BUDGET,
        help="Thinking budget (tokens)",
    )
    parser.add_argument(
        "-j", "--json", action="store_true", help="Output result in JSON format"
    )
    parser.add_argument("--store", action="store_true", help="Save output to file")
    parser.add_argument(
        "-a", "--agentic", action="store_true", help="Optimize output for agentic chain"
    )
    parser.add_argument(
        "--refs", action="store_true", help="Include reference/example files in context"
    )

    parsed: argparse.Namespace = parser.parse_args()

    runner: SkillRunner = SkillRunner(
        provider=parsed.provider,
        model=parsed.model,
        json_mode=parsed.json,
        thinking_budget=parsed.thinking,
        include_refs=parsed.refs,
        agentic_mode=parsed.agentic,
    )

    # Discover all items
    all_items: List[Dict[str, object]] = runner.discover()

    # Handle --list mode
    if parsed.list:
        filter_type: Optional[str] = None
        if parsed.skills:
            filter_type = "skill"
        elif parsed.agents:
            filter_type = "agent"
        runner.list_items(all_items, filter_type)
        return

    # Read stdin if available
    stdin_context: str = ""
    if not sys.stdin.isatty():
        stdin_context = sys.stdin.read().strip()

    # Parse positional args: first arg might be a skill/agent name, rest is prompt
    positional_args: List[str] = parsed.args or []
    item: Optional[Dict[str, object]] = None
    user_prompt: str = ""

    if positional_args:
        # Check if first arg is a skill name
        full_arg_text = " ".join(positional_args)
        candidate_name: str = positional_args[0]

        # Qualifiers definitely mean item
        is_qualified: bool = ":" in candidate_name and candidate_name.split(":")[0] in (
            "agent",
            "skill",
        )
        all_names = [it["name"] for it in all_items]

        if is_qualified or (candidate_name in all_names and len(positional_args) > 1):
            # First arg is a skill name
            item = runner.resolve(candidate_name, all_items)
            if item is None:
                sys.exit(1)
            user_prompt = " ".join(positional_args[1:])
        elif (
            candidate_name in all_names
            and len(positional_args) == 1
            and not parsed.interactive
        ):
            # Just skill name provided
            item = runner.resolve(candidate_name, all_items)
            user_prompt = ""
        else:
            # All args are the prompt — auto-route
            user_prompt = full_arg_text
    else:
        # No positional args
        if not parsed.interactive and not stdin_context:
            parser.print_help()
            sys.exit(0)

    # Auto-route if no explicit item selected
    if item is None and (user_prompt or stdin_context):
        route_text: str = user_prompt or stdin_context[:500]
        if all_items:
            item = runner.auto_route(route_text, all_items)
        # item can still be None — that means generic mode

    # Interactive mode
    if parsed.interactive:
        conversation: str = runner.run_interactive(item, stdin_context)
        if parsed.store and conversation:
            item_name: str = item["name"] if item else "generic"
            save_to_file(conversation, prefix=f"session-{item_name}")
        return

    # Single-shot mode — need a prompt
    if not user_prompt and not stdin_context:
        runner.log(
            f"{RED}No prompt provided. Pass a prompt or use -i for interactive mode.{RESET}"
        )
        sys.exit(1)

    if not user_prompt and stdin_context:
        user_prompt = "Process the provided context."

    response: str = runner.run_single(item, user_prompt, stdin_context)

    if response:
        if parsed.json:
            result: Dict[str, object] = {
                "result": response,
                "skill": item["name"] if item else None,
                "type": item["type"] if item else None,
            }
            print(json.dumps(result, indent=4))
        elif parsed.agentic:
            print(f"\nRESULT:\n{response}\n")
        else:
            print(f"\n{format_markdown(response)}\n")

        if parsed.store:
            if parsed.json:
                save_to_file(
                    json.dumps(result, indent=4),
                    prefix="skill-run",
                    extension="json",
                )
            else:
                item_name: str = item["name"] if item else "generic"
                save_to_file(response, prefix=f"skill-{item_name}")
    else:
        runner.log(f"{RED}No response generated.{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
