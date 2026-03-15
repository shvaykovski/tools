#!/usr/bin/env python3

"""
AI Search Agent
Research assistant that uses local SearXNG for multi-query search and 'trafilatura' for web scraping.

Prerequisites:
    - Python 3.x
    - SearXNG instance running (default: http://localhost:8889)
    - Python package: 'trafilatura' (pip install trafilatura)
    - Access to at least one supported AI provider (OpenAI, Anthropic, OpenRouter, or Ollama)
    - Local 'ai_core' package

Environment Variables:
    export OPENAI_API_KEY="your_key"
    export ANTHROPIC_API_KEY="your_key"
    export OPENROUTER_API_KEY="your_key"
    export SEARXNG_URL="http://localhost:8889" (optional)

Usage (Direct Call):
    python3 ai-agent-researcher.py "Latest features in FastAPI 2026"
    python3 ai-agent-researcher.py --limit 5 --store "Best practices for LLM agents"
    python3 ai-agent-researcher.py --queries 5 "Impact of AI on software engineering"
    python3 ai-agent-researcher.py --provider anthropic "History of the internet"
    python3 ai-agent-researcher.py --json "Benefits of exercise"

Flags:
    --limit          Number of top URLs to scrape and analyze (default: 5)
    --queries        Number of search queries to generate for breadth (default: 3)
    --store          Save the final research report to a timestamped markdown file
    -j, --json       Output result in structured JSON format
    -p, --provider   AI provider (openai, anthropic, openrouter, or ollama)
    -m, --model      Override the default model name for the provider
"""

import json
import urllib.request
import urllib.parse
import argparse
import re
import trafilatura
import sys

from ai_core.colors import YELLOW, BLUE, RED, CYAN, GREEN, RESET, BOLD
from ai_core.ai_client import call_ai
from ai_core.utils import save_to_file, clean_markdown
from ai_core.config import SEARXNG_URL, DEFAULT_PROVIDER, get_default_model


class ResearchAgent:
    def __init__(
        self,
        provider=DEFAULT_PROVIDER,
        model=None,
        limit=5,
        query_count=3,
        json_mode=False,
        agentic_mode=False,
    ):
        self.provider = provider
        self.model = model or get_default_model(provider)
        self.limit = limit
        self.query_count = query_count
        self.searxng_url = SEARXNG_URL
        self.json_mode = json_mode
        self.agentic_mode = agentic_mode

    def log(self, message):
        """Prints message to stderr if json_mode is active, otherwise stdout."""
        if self.json_mode:
            print(message, file=sys.stderr)
        else:
            print(message)

    def generate_queries(self, topic):
        """Pass 1: Use AI to generate diverse search queries."""
        self.log(
            f"{BLUE}🔍 Generating {self.query_count} optimized search queries using {BOLD}{self.model}{RESET}...{RESET}"
        )

        system_prompt = f"Generate {self.query_count} diverse search queries. Return them as a simple list, one per line, no numbering."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": topic},
        ]

        raw_response = call_ai(messages, self.provider, self.model)
        raw_response = clean_markdown(raw_response) if raw_response else ""
        queries = [q.strip("- ").strip() for q in raw_response.split("\n") if q.strip()]

        if not queries:
            queries = [topic]

        self.log(f"   Queries:")
        for q in queries[: self.query_count]:
            self.log(f"     - {YELLOW}{q}{RESET}")

        return queries[: self.query_count]

    def _search_searxng(self, query):
        """Helper to call SearXNG API for a single query."""
        url = f"{self.searxng_url}/search?q={urllib.parse.quote(query)}&format=json"
        try:
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read())
                return data.get("results", [])
        except Exception as e:
            self.log(f"{RED}Search Error for '{query}': {e}{RESET}")
            return []

    def perform_search(self, queries):
        """Pass 2: Execute search queries and deduplicate results."""
        self.log(f"{BLUE}🌐 Searching via SearXNG...{RESET}")
        all_results = []
        seen_urls = set()

        for query in queries:
            self.log(f"   Query: {CYAN}{query}{RESET}")
            results = self._search_searxng(query)
            for r in results:
                url = r.get("url")
                if url and url not in seen_urls:
                    all_results.append(r)
                    seen_urls.add(url)
        return all_results

    def filter_results(self, topic, results):
        """Pass 3: Use AI to pick the most authoritative results."""
        if not results:
            return []

        self.log(f"{BLUE}🎯 Selecting top {self.limit} results...{RESET}")
        snippets = "\n".join(
            [
                f"ID:{i} | {r.get('title')} | {r.get('content')[:150]}"
                for i, r in enumerate(results[:30])
            ]
        )

        system_prompt = f"Choose only the {self.limit} most authoritative result IDs for the topic: '{topic}'. Return ONLY a comma-separated list of IDs."
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": snippets},
        ]

        raw_ids = call_ai(messages, self.provider, self.model)
        raw_ids = clean_markdown(raw_ids) if raw_ids else ""
        ids = re.findall(r"\d+", raw_ids)

        found_urls = []
        for i in ids:
            idx = int(i)
            if 0 <= idx < len(results):
                found_urls.append(results[idx]["url"])

        if not found_urls:
            found_urls = [r["url"] for r in results[: self.limit]]

        return found_urls[: self.limit]

    def scrape_content(self, urls):
        """Pass 4: Scrape URLs and convert to markdown."""
        self.log(f"{BLUE}📄 Scraping content...{RESET}")
        collected_data = []

        for url in urls:
            self.log(f"   Fetching: {CYAN}{url}{RESET}")
            try:
                downloaded = trafilatura.fetch_url(url, no_ssl=True)
                if downloaded:
                    text = trafilatura.extract(downloaded, output_format="markdown")
                    if text:
                        # Limit content per source to stay within context limits
                        collected_data.append(f"SOURCE: {url}\n{text[:8000]}")
            except Exception as e:
                self.log(f"   {RED}Error on {url}: {e}{RESET}")
        return collected_data

    def generate_report(self, topic, content):
        """Pass 5: Generate a final summary report."""
        if not content:
            return ""

        self.log(f"{BLUE}📝 Generating research report...{RESET}")

        system_prompt = (
            "Summarize the research comprehensively, focusing EXCLUSIVELY on information relevant to the topic. "
            "Exclude any fluff, unrelated content, or generic website boilerplate. "
            "Cite source URLs for every key fact. Use Markdown."
        )
        if self.json_mode:
            system_prompt += " IMPORTANT: Do NOT include a 'Sources', 'References', or bibliography section at the end of your response."
        research_context = f"Topic: {topic}\n\nContent:\n" + "\n\n".join(content)

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": research_context},
        ]

        report = call_ai(messages, self.provider, self.model, max_tokens=8192)
        return clean_markdown(report) if report else ""


def main():
    parser = argparse.ArgumentParser(description="AI Research Agent")
    parser.add_argument("topic", nargs="+")
    parser.add_argument("--limit", type=int, default=5, help="Number of URLs to scrape")
    parser.add_argument(
        "--queries", type=int, default=3, help="Search queries to generate"
    )
    parser.add_argument("--store", action="store_true")
    parser.add_argument(
        "-a", "--agentic", action="store_true", help="Optimize output for agentic chain"
    )
    parser.add_argument(
        "-j", "--json", action="store_true", help="Output result in JSON format"
    )
    parser.add_argument("-p", "--provider", default=DEFAULT_PROVIDER)
    parser.add_argument("-m", "--model", help="Override AI Model")
    args = parser.parse_args()

    topic = " ".join(args.topic)

    agent = ResearchAgent(
        provider=args.provider,
        model=args.model,
        limit=args.limit,
        query_count=args.queries,
        json_mode=args.json,
        agentic_mode=args.agentic,
    )

    queries = agent.generate_queries(topic)
    all_results = agent.perform_search(queries)

    if not all_results:
        agent.log(f"{RED}No results found or failed to reach SearXNG.{RESET}")
        return

    top_urls = agent.filter_results(topic, all_results)
    scraped_content = agent.scrape_content(top_urls)
    report = agent.generate_report(topic, scraped_content)

    if report:
        if args.json:
            result_json = {"result": report, "sources": top_urls}
            print(json.dumps(result_json, indent=4))
        elif args.agentic:
            # For agentic mode, we print the report with a marker but without extra decoration
            # The orchestrator will capture this.
            print(f"\nFINAL REPORT:\n{report}\n")
        else:
            print(f"\n{GREEN}{BOLD}FINAL REPORT:{RESET}\n\n{report}\n")

        if args.store:
            if args.json:
                save_content = json.dumps(result_json, indent=4)
                save_to_file(save_content, prefix="research", extension="json")
            else:
                save_to_file(report, prefix="research")
    else:
        agent.log(f"{RED}Failed to generate report.{RESET}")


if __name__ == "__main__":
    main()
