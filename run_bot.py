"""Entrypoint for the bot (CLI / standalone)."""
from __future__ import annotations

import argparse

from apps.worker.runner import run_bot


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Job-Hunter Pro bot.")
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to config file.",
    )
    parser.add_argument(
        "--discovery",
        action="store_true",
        help="Scrape and save discovered jobs without applying.",
    )
    parser.add_argument(
        "--use-config-discovery",
        action="store_true",
        help="Respect discovery.enabled from config.yaml.",
    )
    args = parser.parse_args()

    force_discovery = None if args.use_config_discovery else bool(args.discovery)
    run_bot(args.config, force_discovery=force_discovery)


if __name__ == "__main__":
    main()
