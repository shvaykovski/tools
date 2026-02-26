#!/bin/bash

# Meeting Audio Preparation Tool
# This script optimizes audio files for transcription (mono, 16kHz, silence removed).

show_usage() {
    cat <<EOF
Meeting Audio Preparation Tool
This script optimizes audio files for transcription (mono, 16kHz, silence removed).

Usage:
    ./prepare_meeting.sh <input_path> [output_path]

Examples:
    ./prepare_meeting.sh recording.m4a
    ./prepare_meeting.sh raw_audio.wav cleaned.mp3

Requirements: ffmpeg must be installed.
EOF
}

if [ "$#" -lt 1 ]; then
    show_usage
    exit 1
fi

if ! command -v ffmpeg &> /dev/null; then
    echo "Error: ffmpeg is not installed. Please install it to use this script."
    exit 1
fi

INPUT_PATH="$1"
OUTPUT_PATH="${2:-processed_$(basename "$INPUT_PATH")}"

ffmpeg -i "$INPUT_PATH" \
    -ac 1 \
    -ar 16000 \
    -af "silenceremove=start_periods=1:start_silence=0.3:start_threshold=-35dB:detection=peak" \
    "$OUTPUT_PATH"