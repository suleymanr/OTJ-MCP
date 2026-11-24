#!/bin/sh
cd "$(dirname "$0")" || exit 1

if command -v python3 >/dev/null 2>&1; then
    exec python3 launch.py "$@"
fi

echo "Python 3.11+ was not found."
echo "Install it from https://www.python.org/downloads/ or run: brew install python"
printf "Press Enter to close..."
read -r _
exit 1
