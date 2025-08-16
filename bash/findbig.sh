#!/bin/bash
# Usage: ./findbig.sh <path> [min_size]
# Default min_size = 20M

if [ $# -lt 1 ]; then
  echo "Usage: $0 <path> [min_size]"
  echo "Example: $0 ~/Library/Containers 50M"
  exit 1
fi

SEARCH_PATH="$1"
MIN_SIZE="${2:-20M}"   # default to 20M if not provided

sudo find "$SEARCH_PATH" -type f -size +"$MIN_SIZE" -exec stat -f "%z %N" {} + 2>/dev/null \
  | awk '{ size=$1; $1=""; print size, $0 }' \
  | awk '{ split("B KB MB GB TB",unit); s=$1; u=1; while(s>1024 && u<5){s/=1024;u++} printf("%.1f%s %s\n",s,unit[u],substr($0,index($0,$2)))}' \
  | sort -hr

