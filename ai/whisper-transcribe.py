#!/usr/bin/env python3

"""
Whisper Transcription Tool (CLI Wrapper)
This script wraps the globally installed 'whisper' command to ensure compatibility
across different Python environments.

Usage:
    ./whisper-transcribe.py <audio_or_video_file> [options]

Examples:
    ./whisper-transcribe.py meeting.mp3 --model base --lang en
    ./whisper-transcribe.py interview.mp4 --model large-v3 --prompt "Interview with a scientist"

Options:
    --model        Whisper model size: tiny, base, small, medium, large, large-v3 (default: small)
    --lang         ISO language code (default: en)
    --temperature  Sampling temperature (0-1, default: 0)
    --prompt       Initial text to guide the model (context, names, terms)
    --device       Device to use (e.g., cuda, cpu, mps)
"""

import argparse
import os
import shutil
import subprocess
import sys


def main():
    if not shutil.which("whisper"):
        print(
            "Error: The 'whisper' command-line tool is not installed or not in your PATH.",
            file=sys.stderr,
        )
        print("Please install it with: pip install -U openai-whisper", file=sys.stderr)
        sys.exit(1)

    parser = argparse.ArgumentParser(description="Whisper Transcription CLI Wrapper")

    parser.add_argument("path", help="Audio or video file path")
    parser.add_argument("--model", default="small", help="Model size (default: small)")
    parser.add_argument("--lang", default="en", help="Language code (default: en)")
    parser.add_argument(
        "--temperature", type=float, default=0, help="Temperature for sampling"
    )
    parser.add_argument("--prompt", default="", help="Initial prompt for the model")
    parser.add_argument("--device", help="Force device (e.g., cuda, mps, cpu)")

    if len(sys.argv) == 1:
        print(__doc__)
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    if not os.path.isfile(args.path):
        print(f"Error: File not found: {args.path}", file=sys.stderr)
        sys.exit(1)

    cmd = [
        "whisper",
        args.path,
        "--model",
        args.model,
        "--language",
        args.lang,
        "--temperature",
        str(args.temperature),
        "--output_dir",
        os.path.dirname(args.path) or ".",
        "--verbose",
        "False",
    ]

    if args.prompt:
        cmd.extend(["--initial_prompt", args.prompt])

    if args.device:
        cmd.extend(["--device", args.device])

    print(f"--- Starting Transcription ---")
    print(f"File:   {args.path}")
    print(f"Model:  {args.model}")
    print(f"Device: {args.device or 'auto'}")

    try:
        subprocess.run(cmd, check=True)

        print(f"\n--- Done ---")
        print(f"Result files saved in: {os.path.dirname(args.path) or './'}")

    except FileNotFoundError:
        print(
            f"\nError: The 'whisper' command was not found in your PATH.",
            file=sys.stderr,
        )
        print(
            "Please ensure you have installed it globally with: pip install -U openai-whisper",
            file=sys.stderr,
        )
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        print(
            f"\nError during transcription process (Exit code: {e.returncode})",
            file=sys.stderr,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
