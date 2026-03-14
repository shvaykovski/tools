import re

# ANSI Color constants
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
