#!/usr/bin/env sh
set -eu
cd "$(dirname "$0")"
echo 'Open http://127.0.0.1:8080 in your browser. Press Ctrl+C to stop.'
exec python3 backend/server.py
