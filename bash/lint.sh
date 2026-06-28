#!/bin/bash
set -e

echo "Sorting and grouping imports..."
ruff check --select I --fix .

echo "Linting and fixing errors..."
ruff check --fix .

echo "Formatting files..."
ruff format .

echo "Codebase successfully cleaned and formatted! 🎉"
