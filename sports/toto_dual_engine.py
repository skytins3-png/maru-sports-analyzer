# MARU SPORTS ANALYZER - extracted SKYTOTO dual analysis engine
# 원본 보존 위치: legacy_toto/app.py
# 자동구매/자동결제 없음. 분석 참고용 함수만 분리.

import hashlib
import json
import math
import re
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

APP_VERSION = "MARU_SPORTS_DUAL_ENGINE_V1"
KST = timezone(timedelta(hours=9))
HISTORY_MAX_ROWS = 200_000
SIMILAR_TOP_N = 80

REQUIRED_HISTORY_COLUMNS = [
    "date", "league", "home_team", "away_team", "home_score", "away_score",
    "odds_home", "odds_draw", "odds_away"
]

OPTIONAL_TACTICAL_COLUMNS = [
    "home_main_injuries", "away_main_injuries", "home_suspended", "away_suspended",
    "home_bench_depth", "away_bench_depth", "home_tactic_fit", "away_tactic_fit",
    "home_coach_months", "away_coach_months", "home_rotation_risk", "away_rotation_risk",
    "home_motivation", "away_motivation", "coach_note", "tactic_note", "lineup_note"
]

OUTCOME_LABELS = {
    "HOME": "홈승",
    "DRAW": "무승부",
    "AWAY": "원정승",
}

def stable_result_id(result: Any) -> str:
    """같은 경기/같은 입력이 반복 rerun될 때 로그 중복 폭증을 막는 안전 ID."""
    base = {
        "source": getattr(result, "source", ""),
        "match_key": getattr(result, "match_key", ""),
        "predicted_outcome": getattr(result, "predicted_outcome", ""),
        "predicted_score": getattr(result, "predicted_score", ""),
        "confidence": getattr(result, "confidence", 0),
        "risk_score": getattr(result, "risk_score", 0),
    }
    raw = json.dumps(base, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def now_kst_str() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        if value is None:
            return default
        if isinstance(value, str):
            value = value.strip().replace(",", "")
            if value == "" or value.lower() in {"nan", "none", "null", "-"}:
                return default
        result = float(value)
        if math.isnan(result) or math.isinf(result):
            return default
        return result
    except Exception:
        return default


def safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(round(safe_float(value, float(default))))
    except Exception:
        return default


def clean_team_name(name: Any) -> str:
    text = str(name or "").strip()
    text = re.sub(r"\s+", " ", text)
    return text


def normalize_outcome(value: Any) -> str:
    text = str(value or "").strip().upper()
    mapping = {
        "H": "HOME", "HOME": "HOME", "홈": "HOME", "홈승": "HOME", "1": "HOME",
        "D": "DRAW", "DRAW": "DRAW", "무": "DRAW", "무승부": "DRAW", "X": "DRAW", "0": "DRAW",
        "A": "AWAY", "AWAY": "AWAY", "원정": "AWAY", "원정승": "AWAY", "2": "AWAY",
    }
    return mapping.get(text, text if text in {"HOME", "DRAW", "AWAY"} else "UNKNOWN")


def actual_outcome(home_score: Any, away_score: Any) -> str:
    hs = safe_int(home_score)
    aw = safe_int(away_score)
    if hs > aw:
        return "HOME"
    if hs < aw:
        return "AWAY"
    return "DRAW"


def odds_to_probs(oh: float, od: float, oa: float) -> Dict[str, float]:
    inv_h = 1.0 / oh if oh > 1.0 else 0.0
    inv_d = 1.0 / od if od > 1.0 else 0.0
    inv_a = 1.0 / oa if oa > 1.0 else 0.0
    total = inv_h + inv_d + inv_a
    if total <= 0:
        return {"HOME": 0.34, "DRAW": 0.32, "AWAY": 0.34}
    return {"HOME": inv_h / total, "DRAW": inv_d / total, "AWAY": inv_a / total}


def softmax_dict(scores: Dict[str, float]) -> Dict[str, float]:
    keys = list(scores.keys())
    vals = np.array([safe_float(scores[k]) for k in keys], dtype=float)
    vals = vals - vals.max()
    exp_vals = np.exp(vals)
    denom = exp_vals.sum()
    if denom <= 0:
        return {k: 1.0 / len(keys) for k in keys}
    return {k: float(v / denom) for k, v in zip(keys, exp_vals)}


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


class MatchInput:
    """
    Python 3.14 Streamlit Cloud dataclass 초기화 문제를 피하기 위한 안전 클래스.
    기존 속성명은 그대로 유지한다.
    """
    def __init__(
        self,
        league: str = "",
        home_team: str = "",
        away_team: str = "",
        match_minute: int = 0,
        home_live_score: int = 0,
        away_live_score: int = 0,
        odds_home: float = 0.0,
        odds_draw: float = 0.0,
        odds_away: float = 0.0,
        home_form_score: float = 50.0,
        away_form_score: float = 50.0,
        home_attack: float = 50.0,
        away_attack: float = 50.0,
        home_defense_risk: float = 50.0,
        away_defense_risk: float = 50.0,
        home_main_injuries: int = 0,
        away_main_injuries: int = 0,
        home_suspended: int = 0,
        away_suspended: int = 0,
        home_bench_depth: float = 50.0,
        away_bench_depth: float = 50.0,
        home_tactic_fit: float = 50.0,
        away_tactic_fit: float = 50.0,
        home_coach_months: int = 0,
        away_coach_months: int = 0,
        home_rotation_risk: float = 50.0,
        away_rotation_risk: float = 50.0,
        home_motivation: float = 50.0,
        away_motivation: float = 50.0,
        coach_note: str = "",
        tactic_note: str = "",
        lineup_note: str = "",
        market_note: str = "",
        **extra,
    ):
        self.league = league
        self.home_team = home_team
        self.away_team = away_team
        self.match_minute = match_minute
        self.home_live_score = home_live_score
        self.away_live_score = away_live_score
        self.odds_home = odds_home
        self.odds_draw = odds_draw
        self.odds_away = odds_away
        self.home_form_score = home_form_score
        self.away_form_score = away_form_score
        self.home_attack = home_attack
        self.away_attack = away_attack
        self.home_defense_risk = home_defense_risk
        self.away_defense_risk = away_defense_risk
        self.home_main_injuries = home_main_injuries
        self.away_main_injuries = away_main_injuries
        self.home_suspended = home_suspended
        self.away_suspended = away_suspended
        self.home_bench_depth = home_bench_depth
        self.away_bench_depth = away_bench_depth
        self.home_tactic_fit = home_tactic_fit
        self.away_tactic_fit = away_tactic_fit
        self.home_coach_months = home_coach_months
        self.away_coach_months = away_coach_months
        self.home_rotation_risk = home_rotation_risk
        self.away_rotation_risk = away_rotation_risk
        self.home_motivation = home_motivation
        self.away_motivation = away_motivation
        self.coach_note = coach_note
        self.tactic_note = tactic_note
        self.lineup_note = lineup_note
        self.market_note = market_note
        for k, v in extra.items():
            setattr(self, k, v)

    @property
    def match_key(self) -> str:
        raw = f"{self.league}|{self.home_team}|{self.away_team}"
        return re.sub(r"\s+", " ", raw).strip().lower()



class AnalysisResult:
    """
    Python 3.14 Streamlit Cloud dataclass 초기화 문제를 피하기 위한 안전 클래스.
    """
    def __init__(
        self,
        source: str = "",
        match_key: str = "",
        league: str = "",
        home_team: str = "",
        away_team: str = "",
        predicted_outcome: str = "",
        predicted_label: str = "",
        predicted_score: str = "",
        confidence: float = 0.0,
        risk: str = "",
        risk_score: float = 0.0,
        home_prob: float = 0.0,
        draw_prob: float = 0.0,
        away_prob: float = 0.0,
        reasons=None,
        danger_cases=None,
        top_cases=None,
        top_scorelines=None,
        created_at: str = "",
        **extra,
    ):
        self.source = source
        self.match_key = match_key
        self.league = league
        self.home_team = home_team
        self.away_team = away_team
        self.predicted_outcome = predicted_outcome
        self.predicted_label = predicted_label
        self.predicted_score = predicted_score
        self.confidence = confidence
        self.risk = risk
        self.risk_score = risk_score
        self.home_prob = home_prob
        self.draw_prob = draw_prob
        self.away_prob = away_prob
        self.reasons = reasons or []
        self.danger_cases = danger_cases or []
        self.top_cases = top_cases or []
        self.top_scorelines = top_scorelines or []
        self.created_at = created_at
        for k, v in extra.items():
            setattr(self, k, v)


def sample_history() -> pd.DataFrame:
    # 실제 앱에서는 CSV/구글시트에서 수천~수만 경기 과거자료를 넣는 구조.
    rows: List[Dict[str, Any]] = []
    teams = [
        "독일", "파라과이", "전북", "대구", "울산", "서울", "부산", "수원",
        "아르헨티나", "칠레", "프랑스", "덴마크", "브라질", "일본", "한국", "멕시코"
    ]
    leagues = ["월드컵", "K리그", "국제친선", "클럽컵"]
    rng = np.random.default_rng(314)
    for i in range(420):
        home = teams[i % len(teams)]
        away = teams[(i * 5 + 3) % len(teams)]
        if home == away:
            away = teams[(i * 7 + 1) % len(teams)]
        strength_h = 1.1 + ((i % 7) - 3) * 0.08
        strength_a = 1.0 + (((i * 2) % 7) - 3) * 0.07
        lam_h = clamp(1.25 * strength_h + 0.12, 0.2, 3.8)
        lam_a = clamp(1.05 * strength_a, 0.2, 3.5)
        hs = int(rng.poisson(lam_h))
        aw = int(rng.poisson(lam_a))
        hs = min(hs, 5)
        aw = min(aw, 5)
        probs = odds_to_probs(1.8 + (i % 6) * 0.18, 3.0 + (i % 5) * 0.22, 2.2 + (i % 7) * 0.26)
        rows.append({
            "date": f"2025-{(i % 12) + 1:02d}-{(i % 27) + 1:02d}",
            "league": leagues[i % len(leagues)],
            "home_team": home,
            "away_team": away,
            "home_score": hs,
            "away_score": aw,
            "odds_home": round(1 / max(probs["HOME"], 0.05), 2),
            "odds_draw": round(1 / max(probs["DRAW"], 0.05), 2),
            "odds_away": round(1 / max(probs["AWAY"], 0.05), 2),
            "predicted_outcome": actual_outcome(hs, aw) if i % 4 else ["HOME", "DRAW", "AWAY"][i % 3],
            "home_main_injuries": int(i % 4),
            "away_main_injuries": int((i * 2) % 4),
            "home_suspended": int(i % 2),
            "away_suspended": int((i + 1) % 2),
            "home_bench_depth": int(45 + (i % 45)),
            "away_bench_depth": int(42 + ((i * 3) % 45)),
            "home_tactic_fit": int(45 + ((i * 5) % 50)),
            "away_tactic_fit": int(40 + ((i * 7) % 50)),
            "home_coach_months": int(1 + (i % 60)),
            "away_coach_months": int(1 + ((i * 2) % 60)),
            "home_rotation_risk": int(15 + ((i * 4) % 70)),
            "away_rotation_risk": int(20 + ((i * 6) % 70)),
            "home_motivation": int(45 + ((i * 8) % 50)),
            "away_motivation": int(42 + ((i * 9) % 50)),
            "coach_note": "샘플 감독 성향",
            "tactic_note": "샘플 전술 패턴",
            "lineup_note": "샘플 라인업",
            "prediction_source": "sample_sheet",
            "review_note": "샘플 과거자료",
        })
    return pd.DataFrame(rows)


def normalize_history_df(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return sample_history()
    data = df.copy()
    # 대량 과거자료는 쓰되, 모바일/Streamlit 버퍼링 방지를 위해 최근 N건까지만 안전 사용
    if len(data) > HISTORY_MAX_ROWS:
        data = data.tail(HISTORY_MAX_ROWS).copy()
    rename_map = {}
    aliases = {
        "date": ["date", "날짜", "경기일", "match_date"],
        "league": ["league", "리그", "competition"],
        "home_team": ["home_team", "홈팀", "home", "home_name"],
        "away_team": ["away_team", "원정팀", "away", "away_name"],
        "home_score": ["home_score", "홈점수", "홈스코어", "score_home"],
        "away_score": ["away_score", "원정점수", "원정스코어", "score_away"],
        "odds_home": ["odds_home", "홈배당", "home_odds", "승"],
        "odds_draw": ["odds_draw", "무배당", "draw_odds", "무"],
        "odds_away": ["odds_away", "원정배당", "away_odds", "패"],
        "predicted_outcome": ["predicted_outcome", "예상", "예측", "prediction"],
        "home_main_injuries": ["home_main_injuries", "홈주전부상", "홈부상", "home_injuries"],
        "away_main_injuries": ["away_main_injuries", "원정주전부상", "원정부상", "away_injuries"],
        "home_suspended": ["home_suspended", "홈징계", "홈결장", "home_suspended"],
        "away_suspended": ["away_suspended", "원정징계", "원정결장", "away_suspended"],
        "home_bench_depth": ["home_bench_depth", "홈대기선수", "홈벤치", "home_bench"],
        "away_bench_depth": ["away_bench_depth", "원정대기선수", "원정벤치", "away_bench"],
        "home_tactic_fit": ["home_tactic_fit", "홈전술적합", "home_tactic_fit"],
        "away_tactic_fit": ["away_tactic_fit", "원정전술적합", "away_tactic_fit"],
        "home_coach_months": ["home_coach_months", "홈감독취임개월", "home_coach_months"],
        "away_coach_months": ["away_coach_months", "원정감독취임개월", "away_coach_months"],
        "home_rotation_risk": ["home_rotation_risk", "홈로테이션위험", "home_rotation_risk"],
        "away_rotation_risk": ["away_rotation_risk", "원정로테이션위험", "away_rotation_risk"],
        "home_motivation": ["home_motivation", "홈동기부여", "home_motivation"],
        "away_motivation": ["away_motivation", "원정동기부여", "away_motivation"],
        "coach_note": ["coach_note", "감독메모", "감독성향", "coach_style"],
        "tactic_note": ["tactic_note", "전술메모", "전략메모", "tactic_strategy"],
        "lineup_note": ["lineup_note", "라인업메모", "선수명단", "lineup_note"],
    }
    lower_cols = {str(c).strip().lower(): c for c in data.columns}
    for target, keys in aliases.items():
        for key in keys:
            lk = key.lower()
            if lk in lower_cols:
                rename_map[lower_cols[lk]] = target
                break
    data = data.rename(columns=rename_map)
    for col in REQUIRED_HISTORY_COLUMNS:
        if col not in data.columns:
            if col in {"home_score", "away_score"}:
                data[col] = 0
            elif col.startswith("odds_"):
                data[col] = 0.0
            else:
                data[col] = ""
    data["home_team"] = data["home_team"].apply(clean_team_name)
    data["away_team"] = data["away_team"].apply(clean_team_name)
    data["league"] = data["league"].fillna("").astype(str)
    for col in ["home_score", "away_score"]:
        data[col] = data[col].apply(safe_int)
    for col in ["odds_home", "odds_draw", "odds_away"]:
        data[col] = data[col].apply(safe_float)
    for col in OPTIONAL_TACTICAL_COLUMNS:
        if col not in data.columns:
            data[col] = "" if col.endswith("_note") else 0
    for col in [c for c in OPTIONAL_TACTICAL_COLUMNS if not c.endswith("_note")]:
        data[col] = data[col].apply(safe_float)
    for col in ["coach_note", "tactic_note", "lineup_note"]:
        data[col] = data[col].fillna("").astype(str)
    data["actual_outcome"] = data.apply(lambda r: actual_outcome(r["home_score"], r["away_score"]), axis=1)
    if "predicted_outcome" in data.columns:
        data["predicted_outcome"] = data["predicted_outcome"].apply(normalize_outcome)
    else:
        data["predicted_outcome"] = "UNKNOWN"
    data = data[(data["home_team"] != "") & (data["away_team"] != "")].reset_index(drop=True)
    return data


def load_history_from_csv_upload(uploaded_file: Any) -> Optional[pd.DataFrame]:
    if uploaded_file is None:
        return None
    try:
        try:
            uploaded_file.seek(0)
        except Exception:
            pass
        return pd.read_csv(uploaded_file)
    except Exception:
        try:
            try:
                uploaded_file.seek(0)
            except Exception:
                pass
            return pd.read_excel(uploaded_file)
        except Exception:
            return None


def load_history_from_url(url: str) -> Optional[pd.DataFrame]:
    url = str(url or "").strip()
    if not url:
        return None
    try:
        return pd.read_csv(url)
    except Exception:
        return None


def team_recent_form(history: pd.DataFrame, team: str, limit: int = 10) -> Dict[str, float]:
    team = clean_team_name(team)
    if history.empty or not team:
        return {"played": 0, "win_rate": 0.33, "draw_rate": 0.33, "loss_rate": 0.34, "gf": 1.1, "ga": 1.1}
    mask = (history["home_team"] == team) | (history["away_team"] == team)
    rows = history[mask].tail(limit)
    if rows.empty:
        return {"played": 0, "win_rate": 0.33, "draw_rate": 0.33, "loss_rate": 0.34, "gf": 1.1, "ga": 1.1}
    wins = draws = losses = gf = ga = 0
    for _, r in rows.iterrows():
        is_home = r["home_team"] == team
        goals_for = safe_int(r["home_score"] if is_home else r["away_score"])
        goals_against = safe_int(r["away_score"] if is_home else r["home_score"])
        gf += goals_for
        ga += goals_against
        if goals_for > goals_against:
            wins += 1
        elif goals_for == goals_against:
            draws += 1
        else:
            losses += 1
    n = max(len(rows), 1)
    return {
        "played": n,
        "win_rate": wins / n,
        "draw_rate": draws / n,
        "loss_rate": losses / n,
        "gf": gf / n,
        "ga": ga / n,
    }


def poisson_prob(lam: float, k: int) -> float:
    lam = clamp(lam, 0.05, 5.0)
    return math.exp(-lam) * (lam ** k) / math.factorial(k)


def scoreline_distribution(home_lambda: float, away_lambda: float, max_goals: int = 5) -> List[Dict[str, Any]]:
    cases: List[Dict[str, Any]] = []
    for hs in range(max_goals + 1):
        for aw in range(max_goals + 1):
            p = poisson_prob(home_lambda, hs) * poisson_prob(away_lambda, aw)
            cases.append({"score": f"{hs}:{aw}", "home_score": hs, "away_score": aw, "prob": p})
    total = sum(c["prob"] for c in cases) or 1.0
    for c in cases:
        c["prob"] = c["prob"] / total
        c["outcome"] = actual_outcome(c["home_score"], c["away_score"])
    cases.sort(key=lambda x: x["prob"], reverse=True)
    return cases


def outcome_from_probs(probs: Dict[str, float]) -> str:
    return max(probs, key=lambda k: probs[k])


def confidence_from_probs(probs: Dict[str, float], risk_score: float) -> float:
    sorted_probs = sorted(probs.values(), reverse=True)
    gap = sorted_probs[0] - sorted_probs[1] if len(sorted_probs) > 1 else sorted_probs[0]
    raw = 50 + gap * 70 - risk_score * 0.2
    return round(clamp(raw, 35, 92), 1)


def risk_label(score: float) -> str:
    if score >= 72:
        return "높음"
    if score >= 45:
        return "중간"
    return "낮음"


def make_danger_cases(inp: MatchInput, probs: Dict[str, float], scorelines: List[Dict[str, Any]], history_hint: str = "") -> Tuple[float, List[str]]:
    danger: List[str] = []
    score = 0.0
    if inp.match_minute >= 25 and inp.home_live_score == inp.away_live_score:
        score += 18
        danger.append("전반 중반 이후 동점/무득점이면 무승부 위험 증가")
    if inp.odds_home > 1 and inp.odds_home < 1.35:
        score += 14
        danger.append("저배당 인기팀은 수익 대비 무승부 변수 주의")
    if max(probs.values()) < 0.48:
        score += 16
        danger.append("세 결과 확률 차이가 작아 방향성이 약함")
    if probs.get("DRAW", 0) >= 0.30:
        score += 12
        danger.append("무승부 확률이 30% 이상으로 계산됨")
    top_draw = sum(c["prob"] for c in scorelines[:12] if c["outcome"] == "DRAW")
    if top_draw >= 0.28:
        score += 8
        danger.append("상위 예상 점수군에 무승부 스코어가 많이 포함됨")
    if abs(inp.home_form_score - inp.away_form_score) <= 8:
        score += 7
        danger.append("최근 폼 차이가 크지 않음")
    if inp.home_main_injuries + inp.home_suspended >= 3:
        score += 14
        danger.append("홈팀 주전 부상/징계 결장 누적 위험")
    if inp.away_main_injuries + inp.away_suspended >= 3:
        score += 14
        danger.append("원정팀 주전 부상/징계 결장 누적 위험")
    if inp.home_bench_depth < 45 or inp.away_bench_depth < 45:
        score += 8
        danger.append("대기선수/벤치 뎁스 부족으로 후반 변수 위험")
    if inp.home_coach_months <= 3 or inp.away_coach_months <= 3:
        score += 8
        danger.append("감독 취임 초기라 전술 안정성 변동 위험")
    if max(inp.home_rotation_risk, inp.away_rotation_risk) >= 70:
        score += 10
        danger.append("로테이션/선발 변화 위험이 큼")
    if history_hint:
        danger.append(history_hint)
    if not danger:
        danger.append("특별한 고위험 신호는 약함")
    return clamp(score, 0, 100), danger[:6]


def build_top_cases(probs: Dict[str, float], scorelines: List[Dict[str, Any]], danger_cases: List[str]) -> List[Dict[str, Any]]:
    cases = []
    cases.append({"case": "승패 3경우", "home": round(probs["HOME"] * 100, 1), "draw": round(probs["DRAW"] * 100, 1), "away": round(probs["AWAY"] * 100, 1)})
    cases.append({"case": "무승부 위험", "value": "있음" if probs["DRAW"] >= 0.27 else "보통", "reason": danger_cases[0] if danger_cases else ""})
    for idx, sc in enumerate(scorelines[:5], 1):
        cases.append({"case": f"예상점수 {idx}", "score": sc["score"], "prob": round(sc["prob"] * 100, 1), "outcome": OUTCOME_LABELS.get(sc["outcome"], sc["outcome"])})
    return cases


def hub_analyze(inp: MatchInput, history: pd.DataFrame) -> AnalysisResult:
    odds_probs = odds_to_probs(inp.odds_home, inp.odds_draw, inp.odds_away)
    home_form = clamp(inp.home_form_score, 0, 100) / 100
    away_form = clamp(inp.away_form_score, 0, 100) / 100
    attack_gap = (inp.home_attack - inp.away_attack) / 100
    defense_gap = (inp.away_defense_risk - inp.home_defense_risk) / 100
    lineup_gap = ((inp.away_main_injuries + inp.away_suspended) - (inp.home_main_injuries + inp.home_suspended)) * 0.07
    bench_gap = (inp.home_bench_depth - inp.away_bench_depth) / 180
    tactic_gap = (inp.home_tactic_fit - inp.away_tactic_fit) / 160
    coach_gap = clamp(inp.home_coach_months, 0, 48) / 300 - clamp(inp.away_coach_months, 0, 48) / 300
    rotation_gap = (inp.away_rotation_risk - inp.home_rotation_risk) / 220
    motivation_gap = (inp.home_motivation - inp.away_motivation) / 180
    tactical_total_gap = lineup_gap + bench_gap + tactic_gap + coach_gap + rotation_gap + motivation_gap
    live_gap = (inp.home_live_score - inp.away_live_score) * 0.18
    minute_draw_pressure = 0.12 if inp.match_minute >= 25 and inp.home_live_score == inp.away_live_score else 0.0
    scores = {
        "HOME": math.log(max(odds_probs["HOME"], 0.02)) + 0.55 * home_form - 0.25 * away_form + attack_gap + defense_gap + tactical_total_gap + live_gap,
        "DRAW": math.log(max(odds_probs["DRAW"], 0.02)) + minute_draw_pressure - abs(home_form - away_form) * 0.25 - abs(tactical_total_gap) * 0.10,
        "AWAY": math.log(max(odds_probs["AWAY"], 0.02)) + 0.55 * away_form - 0.25 * home_form - attack_gap - defense_gap - tactical_total_gap - live_gap,
    }
    probs = softmax_dict(scores)
    home_lambda = clamp(1.15 + inp.home_attack / 80 - inp.away_defense_risk / 120 + inp.home_live_score * 0.28 + tactical_total_gap * 0.55, 0.2, 4.2)
    away_lambda = clamp(0.95 + inp.away_attack / 90 - inp.home_defense_risk / 120 + inp.away_live_score * 0.28 - tactical_total_gap * 0.55, 0.2, 4.0)
    if inp.match_minute > 0:
        remaining_factor = clamp((95 - inp.match_minute) / 95, 0.15, 1.0)
        home_lambda = inp.home_live_score + home_lambda * remaining_factor
        away_lambda = inp.away_live_score + away_lambda * remaining_factor
    scorelines = scoreline_distribution(home_lambda, away_lambda)
    risk_score, danger_cases = make_danger_cases(inp, probs, scorelines)
    pred = outcome_from_probs(probs)
    confidence = confidence_from_probs(probs, risk_score)
    reasons = [
        "허브 엔진: 현재 입력값, 배당, 시간, 스코어, 폼, 공격/수비 위험을 즉시 반영",
        f"배당 환산 확률 홈/무/원정: {odds_probs['HOME']:.2f}/{odds_probs['DRAW']:.2f}/{odds_probs['AWAY']:.2f}",
        f"현재 스코어 {inp.home_live_score}:{inp.away_live_score}, 경기 시간 {inp.match_minute}분 반영",
        f"주전부상/징계 홈 {inp.home_main_injuries + inp.home_suspended}명, 원정 {inp.away_main_injuries + inp.away_suspended}명 반영",
        f"대기선수 뎁스 홈 {inp.home_bench_depth:.0f}, 원정 {inp.away_bench_depth:.0f} / 전술적합 홈 {inp.home_tactic_fit:.0f}, 원정 {inp.away_tactic_fit:.0f}",
        f"감독 취임개월 홈 {inp.home_coach_months}개월, 원정 {inp.away_coach_months}개월 / 로테이션 위험 홈 {inp.home_rotation_risk:.0f}, 원정 {inp.away_rotation_risk:.0f}",
    ]
    for note_label, note_text in [("감독 성향", inp.coach_note), ("전술/전략", inp.tactic_note), ("라인업/대기선수", inp.lineup_note)]:
        if str(note_text).strip():
            reasons.append(f"{note_label} 메모 반영: {str(note_text).strip()[:100]}")
    if inp.market_note.strip():
        reasons.append(f"시장 메모 반영: {inp.market_note.strip()[:80]}")
    top_score = scorelines[0]["score"]
    return AnalysisResult(
        source="허브",
        match_key=inp.match_key,
        league=inp.league,
        home_team=inp.home_team,
        away_team=inp.away_team,
        predicted_outcome=pred,
        predicted_label=OUTCOME_LABELS.get(pred, pred),
        predicted_score=top_score,
        confidence=confidence,
        risk=risk_label(risk_score),
        risk_score=round(risk_score, 1),
        home_prob=round(probs["HOME"] * 100, 1),
        draw_prob=round(probs["DRAW"] * 100, 1),
        away_prob=round(probs["AWAY"] * 100, 1),
        reasons=reasons,
        danger_cases=danger_cases,
        top_cases=build_top_cases(probs, scorelines, danger_cases),
        top_scorelines=[{"score": c["score"], "prob": round(c["prob"] * 100, 1), "outcome": OUTCOME_LABELS.get(c["outcome"], c["outcome"])} for c in scorelines[:10]],
        created_at=now_kst_str(),
    )


def similarity_score(row: pd.Series, inp: MatchInput) -> float:
    score = 0.0
    if str(row.get("league", "")).strip() == inp.league.strip():
        score += 18
    if row.get("home_team") == inp.home_team:
        score += 22
    if row.get("away_team") == inp.away_team:
        score += 22
    if row.get("home_team") == inp.away_team or row.get("away_team") == inp.home_team:
        score += 12
    row_probs = odds_to_probs(safe_float(row.get("odds_home")), safe_float(row.get("odds_draw")), safe_float(row.get("odds_away")))
    cur_probs = odds_to_probs(inp.odds_home, inp.odds_draw, inp.odds_away)
    odds_dist = sum(abs(row_probs[k] - cur_probs[k]) for k in ["HOME", "DRAW", "AWAY"])
    score += max(0, 28 - odds_dist * 80)
    # 선수 부상, 징계, 벤치, 감독, 전술 패턴이 비슷한 과거경기일수록 가중치 증가
    tactical_pairs = [
        ("home_main_injuries", inp.home_main_injuries, 2.0), ("away_main_injuries", inp.away_main_injuries, 2.0),
        ("home_suspended", inp.home_suspended, 1.5), ("away_suspended", inp.away_suspended, 1.5),
        ("home_bench_depth", inp.home_bench_depth, 0.08), ("away_bench_depth", inp.away_bench_depth, 0.08),
        ("home_tactic_fit", inp.home_tactic_fit, 0.10), ("away_tactic_fit", inp.away_tactic_fit, 0.10),
        ("home_rotation_risk", inp.home_rotation_risk, 0.08), ("away_rotation_risk", inp.away_rotation_risk, 0.08),
        ("home_motivation", inp.home_motivation, 0.08), ("away_motivation", inp.away_motivation, 0.08),
    ]
    for col, cur_val, weight in tactical_pairs:
        if col in row:
            diff = abs(safe_float(row.get(col)) - safe_float(cur_val))
            score += max(0, 5 - diff * weight)
    row_total = safe_int(row.get("home_score")) + safe_int(row.get("away_score"))
    if row_total <= 2:
        score += 4
    return max(score, 0.1)


def sheet_analyze(inp: MatchInput, history: pd.DataFrame) -> AnalysisResult:
    hist = normalize_history_df(history)
    if hist.empty:
        hist = sample_history()
    hist = hist.copy()
    hist["similarity"] = hist.apply(lambda r: similarity_score(r, inp), axis=1)
    top_n = hist.sort_values("similarity", ascending=False).head(SIMILAR_TOP_N).copy()
    if top_n.empty:
        top_n = sample_history().head(SIMILAR_TOP_N)
        top_n["similarity"] = 1.0
    weights = top_n["similarity"].astype(float).clip(lower=0.1)
    outcome_scores = {"HOME": 0.0, "DRAW": 0.0, "AWAY": 0.0}
    for (_, row), w in zip(top_n.iterrows(), weights):
        outcome_scores[row["actual_outcome"]] += float(w)
    total = sum(outcome_scores.values()) or 1.0
    hist_probs = {k: v / total for k, v in outcome_scores.items()}
    odds_probs = odds_to_probs(inp.odds_home, inp.odds_draw, inp.odds_away)
    # 구글시트 엔진은 과거자료 중심. 배당은 보조만 반영.
    probs = {
        "HOME": hist_probs["HOME"] * 0.72 + odds_probs["HOME"] * 0.28,
        "DRAW": hist_probs["DRAW"] * 0.72 + odds_probs["DRAW"] * 0.28,
        "AWAY": hist_probs["AWAY"] * 0.72 + odds_probs["AWAY"] * 0.28,
    }
    p_total = sum(probs.values()) or 1.0
    probs = {k: v / p_total for k, v in probs.items()}
    avg_h = float(np.average(top_n["home_score"].astype(float), weights=weights)) if len(top_n) else 1.1
    avg_a = float(np.average(top_n["away_score"].astype(float), weights=weights)) if len(top_n) else 1.1
    home_recent = team_recent_form(hist, inp.home_team)
    away_recent = team_recent_form(hist, inp.away_team)
    home_lambda = clamp(avg_h * 0.55 + home_recent["gf"] * 0.35 + inp.home_live_score * 0.25, 0.15, 4.5)
    away_lambda = clamp(avg_a * 0.55 + away_recent["gf"] * 0.35 + inp.away_live_score * 0.25, 0.15, 4.5)
    scorelines = scoreline_distribution(home_lambda, away_lambda)
    similar_draw_rate = hist_probs["DRAW"]
    history_hint = ""
    if similar_draw_rate >= 0.34:
        history_hint = "과거 유사경기에서 무승부 비중이 높음"
    risk_score, danger_cases = make_danger_cases(inp, probs, scorelines, history_hint)
    if len(top_n) < 30:
        risk_score = clamp(risk_score + 12, 0, 100)
        danger_cases.append("과거 유사 표본이 적어 신뢰도 하락")
    pred = outcome_from_probs(probs)
    confidence = confidence_from_probs(probs, risk_score)
    avg_home_inj = float(np.average(top_n["home_main_injuries"].astype(float), weights=weights)) if "home_main_injuries" in top_n else 0.0
    avg_away_inj = float(np.average(top_n["away_main_injuries"].astype(float), weights=weights)) if "away_main_injuries" in top_n else 0.0
    avg_home_tactic = float(np.average(top_n["home_tactic_fit"].astype(float), weights=weights)) if "home_tactic_fit" in top_n else 0.0
    avg_away_tactic = float(np.average(top_n["away_tactic_fit"].astype(float), weights=weights)) if "away_tactic_fit" in top_n else 0.0
    reasons = [
        f"구글시트/과거자료 엔진: 유사 경기 {len(top_n)}건을 가중치로 분석",
        f"유사경기 결과 비율 홈/무/원정: {hist_probs['HOME']:.2f}/{hist_probs['DRAW']:.2f}/{hist_probs['AWAY']:.2f}",
        f"홈팀 최근 {int(home_recent['played'])}경기 평균득점 {home_recent['gf']:.2f}, 평균실점 {home_recent['ga']:.2f}",
        f"원정팀 최근 {int(away_recent['played'])}경기 평균득점 {away_recent['gf']:.2f}, 평균실점 {away_recent['ga']:.2f}",
        f"유사경기 평균 주전부상 홈 {avg_home_inj:.1f}, 원정 {avg_away_inj:.1f} / 전술적합 홈 {avg_home_tactic:.1f}, 원정 {avg_away_tactic:.1f}",
    ]
    top_cases = build_top_cases(probs, scorelines, danger_cases)
    for idx, (_, r) in enumerate(top_n.head(5).iterrows(), 1):
        top_cases.append({
            "case": f"유사과거 {idx}",
            "match": f"{r.get('home_team')} {r.get('home_score')}:{r.get('away_score')} {r.get('away_team')}",
            "similarity": round(safe_float(r.get("similarity")), 1),
            "outcome": OUTCOME_LABELS.get(r.get("actual_outcome"), r.get("actual_outcome")),
            "injury": f"홈{safe_int(r.get('home_main_injuries'))}/원정{safe_int(r.get('away_main_injuries'))}",
            "tactic": f"홈{safe_int(r.get('home_tactic_fit'))}/원정{safe_int(r.get('away_tactic_fit'))}",
        })
    return AnalysisResult(
        source="구글시트",
        match_key=inp.match_key,
        league=inp.league,
        home_team=inp.home_team,
        away_team=inp.away_team,
        predicted_outcome=pred,
        predicted_label=OUTCOME_LABELS.get(pred, pred),
        predicted_score=scorelines[0]["score"],
        confidence=confidence,
        risk=risk_label(risk_score),
        risk_score=round(risk_score, 1),
        home_prob=round(probs["HOME"] * 100, 1),
        draw_prob=round(probs["DRAW"] * 100, 1),
        away_prob=round(probs["AWAY"] * 100, 1),
        reasons=reasons,
        danger_cases=danger_cases[:6],
        top_cases=top_cases[:12],
        top_scorelines=[{"score": c["score"], "prob": round(c["prob"] * 100, 1), "outcome": OUTCOME_LABELS.get(c["outcome"], c["outcome"])} for c in scorelines[:10]],
        created_at=now_kst_str(),
    )


def compare_results(hub: AnalysisResult, sheet: AnalysisResult) -> Dict[str, Any]:
    same = hub.predicted_outcome == sheet.predicted_outcome
    exact_score = hub.predicted_score == sheet.predicted_score
    opposite = {hub.predicted_outcome, sheet.predicted_outcome} == {"HOME", "AWAY"}
    avg_conf = (hub.confidence + sheet.confidence) / 2
    max_risk = max(hub.risk_score, sheet.risk_score)
    if same and exact_score and avg_conf >= 68 and max_risk < 55:
        final = "강추천 후보"
        icon = "✅"
    elif same and avg_conf >= 60:
        final = "추천 후보"
        icon = "🟢"
    elif opposite:
        final = "제외 후보"
        icon = "⛔"
    else:
        final = "위험 경기"
        icon = "⚠️"
    notes = []
    if same:
        notes.append("허브와 구글시트 방향 일치")
    else:
        notes.append("허브와 구글시트 방향 불일치")
    if exact_score:
        notes.append("예상 점수까지 일치")
    if max_risk >= 70:
        notes.append("위험도가 높아 관망 필요")
    if hub.risk_score >= 60 or sheet.risk_score >= 60:
        notes.append("한쪽 엔진에서 강한 위험 신호 감지")
    return {"final": final, "icon": icon, "same": same, "exact_score": exact_score, "opposite": opposite, "avg_conf": round(avg_conf, 1), "max_risk": round(max_risk, 1), "notes": notes}


def review_prediction(result: AnalysisResult, actual_home: int, actual_away: int) -> Dict[str, Any]:
    actual = actual_outcome(actual_home, actual_away)
    success = actual == result.predicted_outcome
    causes: List[str] = []
    if success:
        causes.append("예측 승패 방향 적중")
        if result.predicted_score == f"{actual_home}:{actual_away}":
            causes.append("예상 점수까지 정확히 적중")
        elif result.predicted_score.split(":")[0] == str(actual_home) or result.predicted_score.split(":")[-1] == str(actual_away):
            causes.append("예상 점수 일부 흐름 적중")
    else:
        causes.append("예측 승패 방향 실패")
        if actual == "DRAW":
            causes.append("무승부 변수를 낮게 보았을 가능성")
        if result.risk_score >= 60:
            causes.append("분석 당시 위험 신호가 있었으므로 다음에는 제외/보류 가중치 필요")
        if result.predicted_outcome in {"HOME", "AWAY"} and actual in {"HOME", "AWAY"}:
            causes.append("승부 방향이 반대로 나와 팀 전력/배당 흐름 재검토 필요")
    return {
        "source": result.source,
        "match_key": result.match_key,
        "predicted": result.predicted_label,
        "predicted_score": result.predicted_score,
        "actual": OUTCOME_LABELS.get(actual, actual),
        "actual_score": f"{actual_home}:{actual_away}",
        "success": success,
        "causes": causes,
        "reviewed_at": now_kst_str(),
    }

def generate_synthetic_history(row_count: int = 50000, seed: int = 20260630, scenario: str = "mixed") -> pd.DataFrame:
    """실제 외부자료가 없어도 대량 과거자료/배당 위험/무승부 함정 상황을 재현하는 실험용 데이터 생성."""
    row_count = int(clamp(safe_float(row_count, 50000), 10, 250000))
    rng = np.random.default_rng(int(seed))
    leagues = np.array(["월드컵", "K리그", "EPL", "라리가", "세리에", "분데스", "국제친선", "조작위험리그"])
    teams = np.array(["독일", "파라과이", "전북", "대구", "울산", "서울", "부산", "수원", "브라질", "일본", "한국", "멕시코", "프랑스", "덴마크", "아르헨티나", "칠레", "강팀A", "약팀B", "홈강팀", "원정약팀", "수비팀", "역배팀"])
    idx = np.arange(row_count)
    home_idx = idx % len(teams)
    away_idx = (idx * 7 + 3) % len(teams)
    same = home_idx == away_idx
    away_idx[same] = (away_idx[same] + 1) % len(teams)
    home_team = teams[home_idx]
    away_team = teams[away_idx]
    league = leagues[idx % len(leagues)]
    home_strength = rng.normal(1.10, 0.34, row_count)
    away_strength = rng.normal(1.00, 0.34, row_count)
    low_odds_trap = (idx % 17 == 0) | ((scenario == "low_odds_trap") & (idx % 3 == 0))
    draw_trap = (idx % 19 == 0) | ((scenario == "draw_trap") & (idx % 4 == 0))
    odds_manip = (idx % 23 == 0) | ((scenario == "odds_manipulation") & (idx % 5 == 0))
    away_upset = (idx % 29 == 0) | ((scenario == "away_upset") & (idx % 6 == 0))
    home_inj = rng.integers(0, 5, row_count)
    away_inj = rng.integers(0, 5, row_count)
    home_susp = rng.integers(0, 3, row_count)
    away_susp = rng.integers(0, 3, row_count)
    home_bench = rng.integers(35, 96, row_count)
    away_bench = rng.integers(35, 96, row_count)
    home_tactic = rng.integers(35, 96, row_count)
    away_tactic = rng.integers(35, 96, row_count)
    home_coach = rng.integers(0, 72, row_count)
    away_coach = rng.integers(0, 72, row_count)
    home_rot = rng.integers(0, 95, row_count)
    away_rot = rng.integers(0, 95, row_count)
    home_mot = rng.integers(30, 100, row_count)
    away_mot = rng.integers(30, 100, row_count)
    lam_h = 1.25 * home_strength + 0.22
    lam_a = 1.05 * away_strength
    lam_h += (home_tactic - away_tactic) / 180.0 + (home_mot - away_mot) / 220.0
    lam_a += (away_tactic - home_tactic) / 200.0 + (away_mot - home_mot) / 240.0
    lam_h -= (home_inj * 0.10 + home_susp * 0.12 + home_rot / 600.0)
    lam_a -= (away_inj * 0.10 + away_susp * 0.12 + away_rot / 600.0)
    lam_h = np.clip(lam_h, 0.15, 4.2)
    lam_a = np.clip(lam_a, 0.15, 4.0)
    lam_h[draw_trap] = np.clip(lam_h[draw_trap] * 0.58, 0.15, 2.0)
    lam_a[draw_trap] = np.clip(lam_a[draw_trap] * 0.88, 0.15, 2.2)
    lam_h[away_upset] = np.clip(lam_h[away_upset] * 0.45, 0.12, 1.8)
    lam_a[away_upset] = np.clip(lam_a[away_upset] * 1.55, 0.3, 4.2)
    home_score = np.minimum(rng.poisson(lam_h), 6)
    away_score = np.minimum(rng.poisson(lam_a), 6)
    draw_indices = np.where(draw_trap)[0]
    if len(draw_indices):
        draw_scores = rng.integers(0, 2, len(draw_indices))
        home_score[draw_indices] = draw_scores
        away_score[draw_indices] = draw_scores
    base_home_prob = np.clip(0.44 + (home_strength - away_strength) * 0.12, 0.12, 0.78)
    base_away_prob = np.clip(0.30 + (away_strength - home_strength) * 0.10, 0.08, 0.65)
    base_draw_prob = np.clip(1 - base_home_prob - base_away_prob, 0.12, 0.36)
    total = base_home_prob + base_draw_prob + base_away_prob
    ph = base_home_prob / total
    pd_ = base_draw_prob / total
    pa = base_away_prob / total
    ph[low_odds_trap] = np.clip(ph[low_odds_trap] + 0.22, 0.55, 0.86)
    pd_[low_odds_trap] = np.clip(pd_[low_odds_trap] - 0.08, 0.08, 0.28)
    pa[low_odds_trap] = np.clip(pa[low_odds_trap] - 0.08, 0.05, 0.22)
    ph[odds_manip] = np.clip(ph[odds_manip] + 0.15, 0.50, 0.85)
    pd_[odds_manip] = np.clip(pd_[odds_manip] + 0.08, 0.15, 0.38)
    pa[odds_manip] = np.clip(1 - ph[odds_manip] - pd_[odds_manip], 0.05, 0.30)
    total = ph + pd_ + pa
    ph, pd_, pa = ph / total, pd_ / total, pa / total
    odds_home = np.round(1.06 / np.clip(ph, 0.03, 0.95), 2)
    odds_draw = np.round(1.06 / np.clip(pd_, 0.03, 0.95), 2)
    odds_away = np.round(1.06 / np.clip(pa, 0.03, 0.95), 2)
    actual = np.where(home_score > away_score, "HOME", np.where(home_score < away_score, "AWAY", "DRAW"))
    market_pick = np.where((odds_home < odds_draw) & (odds_home < odds_away), "HOME", np.where(odds_away < odds_draw, "AWAY", "DRAW"))
    predicted = np.where(idx % 5 == 0, market_pick, actual)
    danger_tag = np.where(odds_manip, "배당이상", np.where(low_odds_trap, "저배당함정", np.where(draw_trap, "무승부함정", np.where(away_upset, "역배위험", "일반"))))
    return pd.DataFrame({
        "date": pd.date_range("2021-01-01", periods=row_count, freq="h").strftime("%Y-%m-%d"),
        "league": league, "home_team": home_team, "away_team": away_team,
        "home_score": home_score, "away_score": away_score,
        "odds_home": odds_home, "odds_draw": odds_draw, "odds_away": odds_away,
        "predicted_outcome": predicted,
        "home_main_injuries": home_inj, "away_main_injuries": away_inj,
        "home_suspended": home_susp, "away_suspended": away_susp,
        "home_bench_depth": home_bench, "away_bench_depth": away_bench,
        "home_tactic_fit": home_tactic, "away_tactic_fit": away_tactic,
        "home_coach_months": home_coach, "away_coach_months": away_coach,
        "home_rotation_risk": home_rot, "away_rotation_risk": away_rot,
        "home_motivation": home_mot, "away_motivation": away_mot,
        "coach_note": danger_tag, "tactic_note": danger_tag, "lineup_note": danger_tag,
        "scenario_tag": danger_tag,
    })


def make_input_from_history_row(row: pd.Series) -> MatchInput:
    return MatchInput(
        league=str(row.get("league", "테스트")), home_team=clean_team_name(row.get("home_team", "홈")), away_team=clean_team_name(row.get("away_team", "원정")),
        match_minute=safe_int(row.get("match_minute", 0)), home_live_score=0, away_live_score=0,
        odds_home=safe_float(row.get("odds_home", 0)), odds_draw=safe_float(row.get("odds_draw", 0)), odds_away=safe_float(row.get("odds_away", 0)),
        home_form_score=safe_float(row.get("home_form_score", 55)), away_form_score=safe_float(row.get("away_form_score", 50)),
        home_attack=safe_float(row.get("home_attack", 55)), away_attack=safe_float(row.get("away_attack", 50)),
        home_defense_risk=safe_float(row.get("home_defense_risk", 45)), away_defense_risk=safe_float(row.get("away_defense_risk", 50)),
        home_main_injuries=safe_int(row.get("home_main_injuries", 0)), away_main_injuries=safe_int(row.get("away_main_injuries", 0)),
        home_suspended=safe_int(row.get("home_suspended", 0)), away_suspended=safe_int(row.get("away_suspended", 0)),
        home_bench_depth=safe_float(row.get("home_bench_depth", 55)), away_bench_depth=safe_float(row.get("away_bench_depth", 55)),
        home_tactic_fit=safe_float(row.get("home_tactic_fit", 55)), away_tactic_fit=safe_float(row.get("away_tactic_fit", 55)),
        home_coach_months=safe_int(row.get("home_coach_months", 12)), away_coach_months=safe_int(row.get("away_coach_months", 12)),
        home_rotation_risk=safe_float(row.get("home_rotation_risk", 35)), away_rotation_risk=safe_float(row.get("away_rotation_risk", 35)),
        home_motivation=safe_float(row.get("home_motivation", 55)), away_motivation=safe_float(row.get("away_motivation", 55)),
        coach_note=str(row.get("coach_note", "")), tactic_note=str(row.get("tactic_note", "")), lineup_note=str(row.get("lineup_note", "")), market_note=str(row.get("scenario_tag", "")),
    )


def detect_odds_risk(row: pd.Series) -> List[str]:
    risks: List[str] = []
    oh, od, oa = safe_float(row.get("odds_home")), safe_float(row.get("odds_draw")), safe_float(row.get("odds_away"))
    actual = actual_outcome(row.get("home_score"), row.get("away_score"))
    if oh > 1 and oh <= 1.35 and actual != "HOME": risks.append("저배당 홈강팀 실패 패턴")
    if od > 1 and od <= 3.20 and actual == "DRAW": risks.append("무승부 배당 하락형 패턴")
    if oa > 1 and oa <= 4.50 and actual == "AWAY" and oh <= 1.70: risks.append("약팀/원정 역배 위험 패턴")
    tag = str(row.get("scenario_tag", "")).strip()
    if tag in {"배당이상", "저배당함정", "무승부함정", "역배위험"}: risks.append(tag)
    return sorted(set(risks))


def run_backtest(history: pd.DataFrame, sample_n: int = 300, seed: int = 777) -> Dict[str, Any]:
    hist = normalize_history_df(history)
    if hist.empty: return {"ok": False, "message": "과거자료 없음"}
    sample_n = int(clamp(safe_float(sample_n, 300), 5, 3000))
    test_df = hist.sample(n=min(sample_n, len(hist)), random_state=int(seed)) if len(hist) > sample_n else hist.copy()
    rows: List[Dict[str, Any]] = []
    hub_ok = sheet_ok = both_same = both_same_ok = both_diff = both_diff_ok = risk_fail_hits = 0
    for _, row in test_df.iterrows():
        inp = make_input_from_history_row(row)
        hub = hub_analyze(inp, hist)
        sheet = sheet_analyze(inp, hist)
        actual = actual_outcome(row.get("home_score"), row.get("away_score"))
        h_ok = hub.predicted_outcome == actual
        s_ok = sheet.predicted_outcome == actual
        same = hub.predicted_outcome == sheet.predicted_outcome
        hub_ok += int(h_ok); sheet_ok += int(s_ok); both_same += int(same); both_diff += int(not same)
        both_same_ok += int(same and h_ok and s_ok); both_diff_ok += int((not same) and (h_ok or s_ok))
        odds_risks = detect_odds_risk(row)
        risk_fail_hits += int(bool(odds_risks) and (not h_ok or not s_ok))
        rows.append({"경기": f"{inp.home_team} vs {inp.away_team}", "실제": OUTCOME_LABELS.get(actual, actual), "허브": hub.predicted_label, "허브성공": "성공" if h_ok else "실패", "시트": sheet.predicted_label, "시트성공": "성공" if s_ok else "실패", "일치": "일치" if same else "불일치", "위험패턴": ", ".join(odds_risks) if odds_risks else ""})
    n = max(len(test_df), 1)
    return {"ok": True, "tested": len(test_df), "hub_accuracy": round(hub_ok/n*100,2), "sheet_accuracy": round(sheet_ok/n*100,2), "same_count": both_same, "same_accuracy": round(both_same_ok/both_same*100,2) if both_same else 0, "diff_count": both_diff, "diff_any_accuracy": round(both_diff_ok/both_diff*100,2) if both_diff else 0, "risk_fail_hits": risk_fail_hits, "rows": rows}


def scenario_test_pack() -> pd.DataFrame:
    cases = [
        {"scenario_tag":"저배당함정","home_team":"홈강팀","away_team":"원정약팀","odds_home":1.24,"odds_draw":5.20,"odds_away":10.5,"home_score":1,"away_score":1,"home_main_injuries":2,"home_suspended":1,"home_rotation_risk":70,"away_motivation":80},
        {"scenario_tag":"무승부함정","home_team":"수비팀","away_team":"수비팀2","odds_home":1.65,"odds_draw":3.05,"odds_away":5.8,"home_score":0,"away_score":0,"home_tactic_fit":45,"away_tactic_fit":65},
        {"scenario_tag":"역배위험","home_team":"인기팀","away_team":"역배팀","odds_home":1.55,"odds_draw":3.90,"odds_away":4.20,"home_score":0,"away_score":2,"home_main_injuries":3,"away_motivation":90},
        {"scenario_tag":"감독교체","home_team":"새감독팀","away_team":"안정팀","odds_home":2.05,"odds_draw":3.20,"odds_away":3.40,"home_score":2,"away_score":1,"home_coach_months":1,"home_motivation":88},
    ]
    base=[]
    for i,c in enumerate(cases):
        r={"date":f"2026-06-{i+1:02d}","league":"실험리그","home_main_injuries":0,"away_main_injuries":0,"home_suspended":0,"away_suspended":0,"home_bench_depth":55,"away_bench_depth":55,"home_tactic_fit":55,"away_tactic_fit":55,"home_coach_months":12,"away_coach_months":12,"home_rotation_risk":30,"away_rotation_risk":30,"home_motivation":55,"away_motivation":55,"odds_home":2.0,"odds_draw":3.3,"odds_away":3.5,"predicted_outcome":"UNKNOWN","coach_note":"","tactic_note":"","lineup_note":""}
        r.update(c); base.append(r)
    return pd.DataFrame(base)


def result_to_dict(result: AnalysisResult) -> Dict[str, Any]:
    return dict(getattr(result, '__dict__', {}))


def dual_analyze(inp: MatchInput, history: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    hist = normalize_history_df(history if history is not None else sample_history())
    hub = hub_analyze(inp, hist)
    sheet = sheet_analyze(inp, hist)
    compare = compare_results(hub, sheet)
    return {
        "hub": result_to_dict(hub),
        "sheet": result_to_dict(sheet),
        "compare": compare,
    }
