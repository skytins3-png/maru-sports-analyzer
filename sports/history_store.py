from __future__ import annotations
from pathlib import Path
from typing import Dict, Any, Tuple
from datetime import datetime, timezone, timedelta
import pandas as pd

KST = timezone(timedelta(hours=9))
DEFAULT_HISTORY_PATH = Path("cache/history_matches.csv")
REQUIRED_COLUMNS = ["date", "league", "home_team", "away_team", "home_score", "away_score"]
OPTIONAL_COLUMNS = ["status", "source", "match_id"]

def now_kst() -> str:
    return datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST")

def ensure_cache_dir():
    DEFAULT_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)

def normalize_history_df(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    if df is None:
        return pd.DataFrame(), {"ok": False, "message": "DataFrame 없음", "missing": REQUIRED_COLUMNS}
    df = df.copy()
    df.columns = [str(c).strip().lower() for c in df.columns]
    alias = {
        "날짜": "date", "일자": "date", "경기일": "date",
        "리그": "league", "대회": "league",
        "홈팀": "home_team", "home": "home_team",
        "원정팀": "away_team", "away": "away_team",
        "홈점수": "home_score", "home_goals": "home_score",
        "원정점수": "away_score", "away_goals": "away_score",
        "상태": "status", "출처": "source",
    }
    df = df.rename(columns={c: alias.get(c, c) for c in df.columns})
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        return pd.DataFrame(), {"ok": False, "message": "필수 컬럼 누락", "missing": missing}
    for c in REQUIRED_COLUMNS + OPTIONAL_COLUMNS:
        if c not in df.columns:
            df[c] = "finished" if c == "status" else ("csv" if c == "source" else "")
    df = df[REQUIRED_COLUMNS + OPTIONAL_COLUMNS].copy()
    df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
    df["home_score"] = pd.to_numeric(df["home_score"], errors="coerce")
    df["away_score"] = pd.to_numeric(df["away_score"], errors="coerce")
    for c in ["league","home_team","away_team","status","source","match_id"]:
        df[c] = df[c].fillna("").astype(str)
    before = len(df)
    df = df.dropna(subset=["date","home_score","away_score"])
    df = df[(df["home_team"].str.len() > 0) & (df["away_team"].str.len() > 0)]
    df.loc[df["match_id"].str.len() == 0, "match_id"] = (
        df["date"].astype(str)+"|"+df["league"].astype(str)+"|"+df["home_team"].astype(str)+"|"+df["away_team"].astype(str)
    )
    df = df.drop_duplicates(subset=["match_id"], keep="last").sort_values("date")
    return df.reset_index(drop=True), {"ok": True, "message": "정규화 완료", "rows_before": before, "rows_after": len(df), "dropped": before-len(df), "missing": []}

def load_history(path: Path = DEFAULT_HISTORY_PATH) -> pd.DataFrame:
    ensure_cache_dir()
    if not path.exists():
        return pd.DataFrame(columns=REQUIRED_COLUMNS + OPTIONAL_COLUMNS)
    try:
        norm, info = normalize_history_df(pd.read_csv(path))
        if info.get("ok"):
            return norm
    except Exception:
        pass
    return pd.DataFrame(columns=REQUIRED_COLUMNS + OPTIONAL_COLUMNS)

def append_history(new_df: pd.DataFrame, path: Path = DEFAULT_HISTORY_PATH) -> Dict[str, Any]:
    old = load_history(path)
    norm_new, info = normalize_history_df(new_df)
    if not info.get("ok"):
        return info
    combined, info2 = normalize_history_df(pd.concat([old, norm_new], ignore_index=True))
    if not info2.get("ok"):
        return info2
    ensure_cache_dir()
    combined.to_csv(path, index=False, encoding="utf-8-sig")
    return {"ok": True, "message": "추가 저장 완료", "old_rows": len(old), "new_rows": len(norm_new), "total_rows": len(combined), "path": str(path)}

def history_summary(path: Path = DEFAULT_HISTORY_PATH) -> Dict[str, Any]:
    df = load_history(path)
    if df.empty:
        return {"rows": 0, "teams": 0, "leagues": 0, "date_min": "", "date_max": "", "message": "저장된 과거자료 없음"}
    teams = set(df["home_team"].astype(str)) | set(df["away_team"].astype(str))
    return {"rows": len(df), "teams": len(teams), "leagues": int(df["league"].nunique()), "date_min": str(df["date"].min()), "date_max": str(df["date"].max()), "message": "저장된 과거자료 있음"}

def team_recent_stats(history: pd.DataFrame, team: str, n: int = 10) -> Dict[str, Any]:
    if history is None or history.empty or not team:
        return {"team": team, "matches": 0, "message": "자료 없음"}
    games = history[(history["home_team"] == team) | (history["away_team"] == team)].sort_values("date", ascending=False).head(n)
    if games.empty:
        return {"team": team, "matches": 0, "message": "팀 경기 없음"}
    win=draw=loss=gf=ga=over25=0
    for _, r in games.iterrows():
        is_home = r["home_team"] == team
        hs, aw = float(r["home_score"]), float(r["away_score"])
        f = hs if is_home else aw
        a = aw if is_home else hs
        gf += f; ga += a
        if f > a: win += 1
        elif f == a: draw += 1
        else: loss += 1
        if hs + aw >= 3: over25 += 1
    m = len(games)
    return {"team": team, "matches": m, "wins": win, "draws": draw, "losses": loss, "avg_gf": round(gf/m,2), "avg_ga": round(ga/m,2), "over25_rate": round(over25/m*100,1), "form_score": round((win*3+draw)/(m*3)*100,1)}

def analyze_fixture_from_history(fixture: Dict[str, Any], history: pd.DataFrame, n: int = 10) -> Dict[str, Any]:
    home, away = fixture.get("home_team",""), fixture.get("away_team","")
    hs, aas = team_recent_stats(history, home, n), team_recent_stats(history, away, n)
    suff = min(100, round(((hs.get("matches",0)+aas.get("matches",0))/(n*2))*100,1))
    if hs.get("matches",0) == 0 or aas.get("matches",0) == 0:
        return {"title": f"{home} vs {away}", "analysis_possible": False, "data_sufficiency": suff, "risk": "높음", "message": "과거자료 부족"}
    diff = hs["form_score"] - aas["form_score"]
    pick = "무/접전" if abs(diff) < 7 else ("홈 우세" if diff > 0 else "원정 우세")
    risk = "낮음" if suff >= 80 else ("보통" if suff >= 50 else "높음")
    return {"title": f"{home} vs {away}", "analysis_possible": True, "data_sufficiency": suff, "risk": risk, "pick": pick, "message": "저장된 과거자료 기준 분석", "home_stats": hs, "away_stats": aas}
