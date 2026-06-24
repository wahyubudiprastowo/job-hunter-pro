"""
PATCH 29 - Self-tests for Hybrid Orchestrator.
"""
import sys
from unittest.mock import MagicMock

from packages.core.orchestrator import (
    HybridOrchestrator,
    RoundStats,
    OrchestratorState,
)


def test_case(name, condition, details=""):
    print(f"\n=== TEST: {name} ===")
    if condition:
        print("PASS")
    else:
        print("FAIL")
        if details:
            print(f"   Details: {details}")
    return condition


class MockExtractor:
    def __init__(self, platform_name, apply_results=None):
        self.platform_name = platform_name
        self.apply_results = apply_results or []
        self.search_called = False
        self.cards_collected = 0

    def search(self, filters):
        self.search_called = True

    def collect_job_cards(self, max_cards=50):
        cards = [{"job_id": f"{self.platform_name}-{i}", "title": f"Job {i}"} for i in range(max_cards)]
        self.cards_collected = len(cards)
        return cards


def run_tests():
    passed = 0
    total = 0

    total += 1
    orch = HybridOrchestrator(platforms=["linkedin", "indeed"], applies_per_round=3, max_rounds=5)
    if test_case("Initialization with valid params", orch.platforms == ["linkedin", "indeed"] and orch.applies_per_round == 3 and orch.max_rounds == 5):
        passed += 1

    total += 1
    if test_case("Initial state correct", orch.state.current_round == 0 and orch.state.total_applies == 0 and orch.state.current_platform is None):
        passed += 1

    total += 1
    stats = RoundStats(round_num=1)
    stats.applies_per_platform["linkedin"] = 2
    stats.applies_per_platform["indeed"] = 1
    if test_case("RoundStats tracks per-platform applies", stats.applies_per_platform.get("linkedin") == 2 and stats.applies_per_platform.get("indeed") == 1):
        passed += 1

    total += 1
    state_dict = orch.get_state()
    if test_case("get_state has expected keys", all(k in state_dict for k in ["current_round", "current_platform", "current_phase", "rounds_completed", "total_applies", "platforms"])):
        passed += 1

    total += 1
    orch_empty = HybridOrchestrator(platforms=["linkedin", "indeed"], applies_per_round=1, max_rounds=1, pause_between_platforms=0, pause_between_rounds=0)
    try:
        history = orch_empty.run(
            extractors={},
            platform_configs={},
            platform_filters={},
            apply_one_callback=lambda **kw: None,
        )
        graceful = len(history) == 1
    except Exception:
        graceful = False
    if test_case("Run with empty extractors handles gracefully", graceful):
        passed += 1

    total += 1
    orch_stop = HybridOrchestrator(platforms=["linkedin"], applies_per_round=5, max_rounds=3, pause_between_platforms=0, pause_between_rounds=0)
    mock_extractor = MockExtractor("linkedin")
    stop_called = [False]

    def should_stop():
        result = stop_called[0]
        stop_called[0] = True
        return result

    history = orch_stop.run(
        extractors={"linkedin": mock_extractor},
        platform_configs={"linkedin": {}},
        platform_filters={"linkedin": MagicMock()},
        apply_one_callback=lambda **kw: None,
        should_stop_callback=should_stop,
    )
    if test_case("Stop signal terminates execution", len(history) <= 1):
        passed += 1

    total += 1
    orch_rl = HybridOrchestrator(platforms=["linkedin", "indeed"], applies_per_round=1, max_rounds=1, pause_between_platforms=0, pause_between_rounds=0)

    def rl_check(platform):
        if platform == "linkedin":
            return False, "daily_cap_reached"
        return True, ""

    history = orch_rl.run(
        extractors={"linkedin": MockExtractor("linkedin"), "indeed": MockExtractor("indeed")},
        platform_configs={"linkedin": {}, "indeed": {}},
        platform_filters={"linkedin": MagicMock(), "indeed": MagicMock()},
        apply_one_callback=lambda **kw: None,
        rate_limit_check_callback=rl_check,
    )
    if test_case("Rate limit on one platform doesn't stop others", len(history) == 1 and history[0].early_stopped is True):
        passed += 1

    total += 1
    empty_stats = RoundStats(round_num=99)
    if test_case("RoundStats has sensible defaults", empty_stats.platforms_processed == [] and empty_stats.applies_per_platform == {} and empty_stats.duration_seconds == 0 and empty_stats.early_stopped is False):
        passed += 1

    total += 1
    state = OrchestratorState()
    state.total_applies = 10
    state.rounds_completed = 3
    if test_case("OrchestratorState tracks counters", state.total_applies == 10 and state.rounds_completed == 3):
        passed += 1

    total += 1
    orch_3p = HybridOrchestrator(platforms=["linkedin", "indeed", "glassdoor"], applies_per_round=2, max_rounds=1)
    if test_case("Supports any number of platforms", len(orch_3p.platforms) == 3):
        passed += 1

    print(f"\nRESULTS: {passed}/{total} tests passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(run_tests())
