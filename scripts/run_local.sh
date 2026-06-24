#!/usr/bin/env bash
# Quick start for Linux/macOS native run.
set -e
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
else
  source .venv/bin/activate
fi
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo "⚠️  Edit .env with your credentials, then re-run."
  exit 1
fi
python run_web.py
