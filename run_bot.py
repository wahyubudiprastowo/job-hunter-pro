"""Entrypoint for the bot (CLI / standalone)."""
from apps.worker.runner import run_bot

if __name__ == "__main__":
    run_bot()
