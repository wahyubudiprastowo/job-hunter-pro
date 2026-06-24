"""
Hybrid Parallel Orchestrator (Patch 29 v1).

Implements a round-robin scheduler across platforms using a
single browser and single thread.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional

from loguru import logger


@dataclass
class RoundStats:
    """Stats from one round of hybrid execution."""
    round_num: int
    platforms_processed: List[str] = field(default_factory=list)
    applies_per_platform: Dict[str, int] = field(default_factory=dict)
    skips_per_platform: Dict[str, int] = field(default_factory=dict)
    failures_per_platform: Dict[str, int] = field(default_factory=dict)
    duration_seconds: float = 0
    early_stopped: bool = False
    stop_reason: str = ""


@dataclass
class OrchestratorState:
    """Current state of the orchestrator."""
    current_round: int = 0
    current_platform: Optional[str] = None
    current_phase: str = "idle"
    rounds_completed: int = 0
    total_applies: int = 0
    total_skipped: int = 0
    total_failed: int = 0
    started_at: int = 0
    history: List[RoundStats] = field(default_factory=list)


class HybridOrchestrator:
    """
    Round-robin orchestrator for multi-platform execution.
    """

    def __init__(
        self,
        platforms: List[str],
        applies_per_round: int = 3,
        max_rounds: int = 5,
        pause_between_rounds: float = 60.0,
        pause_between_platforms: float = 30.0,
        stop_on_rate_limit: bool = True,
        progress_callback: Optional[Callable] = None,
    ):
        self.platforms = platforms
        self.applies_per_round = applies_per_round
        self.max_rounds = max_rounds
        self.pause_between_rounds = pause_between_rounds
        self.pause_between_platforms = pause_between_platforms
        self.stop_on_rate_limit = stop_on_rate_limit
        self.progress_callback = progress_callback
        self.state = OrchestratorState(started_at=int(time.time()))

    def run(
        self,
        extractors: Dict[str, object],
        platform_configs: Dict[str, dict],
        platform_filters: Dict[str, object],
        apply_one_callback: Callable,
        rate_limit_check_callback: Optional[Callable] = None,
        should_stop_callback: Optional[Callable] = None,
    ) -> List[RoundStats]:
        logger.info(
            f"Hybrid orchestrator starting: platforms={self.platforms}, "
            f"applies_per_round={self.applies_per_round}, max_rounds={self.max_rounds}"
        )

        platform_pools: Dict[str, list] = {p: [] for p in self.platforms}

        for round_num in range(1, self.max_rounds + 1):
            self.state.current_round = round_num
            round_stats = RoundStats(round_num=round_num)
            round_start = time.time()

            logger.info(f"ROUND {round_num}/{self.max_rounds}")

            for platform_idx, platform_name in enumerate(self.platforms):
                if should_stop_callback and should_stop_callback():
                    round_stats.early_stopped = True
                    round_stats.stop_reason = "user_stop"
                    self.state.history.append(round_stats)
                    return self.state.history

                if self.stop_on_rate_limit and rate_limit_check_callback:
                    can_continue, reason = rate_limit_check_callback(platform_name)
                    if not can_continue:
                        round_stats.early_stopped = True
                        round_stats.stop_reason = f"rate_limit:{platform_name}:{reason}"
                        logger.warning(f"Rate limit hit: {platform_name} - {reason}")
                        continue

                self.state.current_platform = platform_name
                self.state.current_phase = "searching"
                extractor = extractors.get(platform_name)
                if not extractor:
                    logger.warning(f"No extractor for {platform_name} - skipping")
                    continue

                if not platform_pools[platform_name]:
                    filters = platform_filters.get(platform_name)
                    if filters:
                        try:
                            extractor.search(filters)
                            cards = extractor.collect_job_cards(max_cards=self.applies_per_round * 3)
                            platform_pools[platform_name] = cards
                            logger.info(f"Collected {len(cards)} cards for {platform_name}")
                        except Exception as e:
                            logger.exception(f"Search/collect failed for {platform_name}: {e}")
                            continue

                self.state.current_phase = "applying"
                applied_this_platform = 0

                while applied_this_platform < self.applies_per_round:
                    if not platform_pools[platform_name]:
                        break
                    card = platform_pools[platform_name].pop(0)

                    if should_stop_callback and should_stop_callback():
                        round_stats.early_stopped = True
                        round_stats.stop_reason = "user_stop_mid_apply"
                        self.state.history.append(round_stats)
                        return self.state.history

                    try:
                        result = apply_one_callback(
                            extractor=extractor,
                            platform_name=platform_name,
                            card=card,
                            platform_config=platform_configs.get(platform_name, {}),
                        )
                        if result is None:
                            continue

                        from packages.core.models import ApplyStatus

                        if result.status == ApplyStatus.APPLIED:
                            round_stats.applies_per_platform[platform_name] = (
                                round_stats.applies_per_platform.get(platform_name, 0) + 1
                            )
                            self.state.total_applies += 1
                            applied_this_platform += 1
                        elif result.status in (ApplyStatus.SKIPPED, ApplyStatus.EXTERNAL):
                            round_stats.skips_per_platform[platform_name] = (
                                round_stats.skips_per_platform.get(platform_name, 0) + 1
                            )
                            self.state.total_skipped += 1
                        elif result.status == ApplyStatus.FAILED:
                            round_stats.failures_per_platform[platform_name] = (
                                round_stats.failures_per_platform.get(platform_name, 0) + 1
                            )
                            self.state.total_failed += 1
                    except Exception as e:
                        logger.exception(f"Apply failed in {platform_name}: {e}")
                        round_stats.failures_per_platform[platform_name] = (
                            round_stats.failures_per_platform.get(platform_name, 0) + 1
                        )

                round_stats.platforms_processed.append(platform_name)

                if self.progress_callback:
                    try:
                        self.progress_callback(
                            round_num=round_num,
                            platform=platform_name,
                            stats=round_stats,
                        )
                    except Exception as e:
                        logger.debug(f"Progress callback error: {e}")

                if platform_idx < len(self.platforms) - 1:
                    self.state.current_phase = "switching"
                    time.sleep(self.pause_between_platforms)

            round_stats.duration_seconds = round(time.time() - round_start, 1)
            self.state.history.append(round_stats)
            self.state.rounds_completed += 1

            if round_num < self.max_rounds:
                time.sleep(self.pause_between_rounds)

        self.state.current_phase = "idle"
        self.state.current_platform = None
        return self.state.history

    def get_state(self) -> dict:
        """Get current state for monitoring/UI."""
        return {
            "current_round": self.state.current_round,
            "current_platform": self.state.current_platform,
            "current_phase": self.state.current_phase,
            "rounds_completed": self.state.rounds_completed,
            "total_applies": self.state.total_applies,
            "total_skipped": self.state.total_skipped,
            "total_failed": self.state.total_failed,
            "max_rounds": self.max_rounds,
            "platforms": self.platforms,
            "started_at": self.state.started_at,
        }
