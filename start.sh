#!/bin/bash
set -e

echo "🔍 Installing dependencies for Playwright..."
npx playwright install --with-deps chromium

echo "🚀 Starting the app..."
python app.py
