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


def read_files(file_paths):
    """Reads content of specified files to provide as context."""
    if not file_paths:
        return ""
    context = ""
    for path in file_paths:
        if os.path.isfile(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
                    context += f"\n--- FILE: {path} ---\n{content}\n"
            except Exception as e:
                print(f"{RED}Error reading {path}: {e}{RESET}")
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
    """Handles saving content to a timestamped file."""
    if not default_filename:
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        default_filename = f"{prefix}-{timestamp}.{extension}"

    print(f"\n{BLUE}💾 Would you like to save this to a file?{RESET}")
    choice = input(f" [{BOLD}y{RESET}]es / [{BOLD}n{RESET}]o: ").strip().lower()

    if choice == "y":
        filename = input(
            f" Enter filename (default: {YELLOW}{default_filename}{RESET}): "
        ).strip()
        if not filename:
            filename = default_filename

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"{GREEN}✨ Successfully saved to: {BOLD}{filename}{RESET}")
            return filename
        except Exception as e:
            print(f"{RED}Error saving file: {e}{RESET}")
    return None
