import os
import platform
import subprocess
from datetime import datetime
from .colors import BLUE, YELLOW, GREEN, RED, RESET, BOLD


def get_system_context():
    """Gathers OS, Shell, and CWD info."""
    try:
        os_name = platform.system()
        os_version = (
            platform.mac_ver()[0] if os_name == "Darwin" else platform.release()
        )
        shell = os.path.basename(os.getenv("SHELL", "bash"))
        return (
            f"OS: {os_name} (version {os_version}), Shell: {shell}, CWD: {os.getcwd()}"
        )
    except Exception:
        return "Standard macOS/Linux environment"


def read_file_smart(path, max_chars=15000):
    """Reads file with head & tail truncation for large files."""
    if not os.path.isfile(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()
            if len(content) <= max_chars:
                return content

            # Head 40%, Tail 40%, Truncation message in middle
            head_size = int(max_chars * 0.4)
            tail_size = int(max_chars * 0.4)
            head = content[:head_size]
            tail = content[-tail_size:]
            return f"{head}\n\n... [TRUNCATED {len(content) - max_chars} characters] ...\n\n{tail}"
    except Exception as e:
        print(f"{RED}Error reading {path}: {e}{RESET}")
        return ""


def read_files_context(file_paths):
    """Reads multiple files using the smart reader."""
    if not file_paths:
        return ""
    context = ""
    for path in file_paths:
        content = read_file_smart(path)
        if content:
            context += f"\n--- FILE: {path} ---\n{content}\n"
    return context


def copy_to_clipboard(text: str):
    """Copies text to the clipboard using pbcopy (macOS) or xclip/xsel (Linux)."""
    try:
        if platform.system() == "Darwin":
            subprocess.run(["pbcopy"], input=text.encode(), check=True)
        else:
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


def clean_markdown(text: str) -> str:
    """Removes markdown code block wrappers from the text."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        # Remove the first line (the opening ```lang)
        if len(lines) > 0 and lines[0].startswith("```"):
            lines = lines[1:]
        # Remove the last line (the closing ```)
        if len(lines) > 0 and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def save_to_file(content, prefix="output", default_filename=None, extension="md"):
    """Handles saving content to a file with a filename prompt and automatic extension."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    if not default_filename:
        default_base = f"{prefix}-{timestamp}"
    else:
        # Strip extension if provided in default_filename for the prompt visibility
        default_base = os.path.splitext(default_filename)[0]

    print(f"\n{BLUE}💾 Saving to file...{RESET}")
    user_input = input(
        f" Enter filename (default: {YELLOW}{default_base}{RESET}, extension .{extension} auto-added): "
    ).strip()

    base_name = user_input if user_input else default_base

    # Ensure it ends with the correct extension (case-insensitive check)
    if not base_name.lower().endswith(f".{extension.lower()}"):
        filename = f"{base_name}.{extension}"
    else:
        filename = base_name

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"{GREEN}✨ Successfully saved to: {BOLD}{filename}{RESET}")
        return filename
    except Exception as e:
        print(f"{RED}Error saving file: {e}{RESET}")
    return None
