from __future__ import annotations

from typing import Any, Dict
import pandas as pd

from .toto_dual_engine import (
    generate_synthetic_history,
    run_backtest,
    scenario_test_pack,
    detect_odds_risk,
    normalize_history_df,
)


def run_quick_backtest(row_count: int = 500, sample_n: int = 80, scenario: str = "mixed") -> Dict[str, Any]:
    history = generate_synthetic_history(row_count=row_count, scenario=scenario)
    return run_backtest(history, sample_n=sample_n)
