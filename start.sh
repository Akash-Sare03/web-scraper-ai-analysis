#!/usr/bin/env bash
set -e

echo "🔍 Installing Playwright Chromium + dependencies..."
python -m playwright install --with-deps chromium

echo "🚀 Starting Web Data Extractor..."
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --threads 4
