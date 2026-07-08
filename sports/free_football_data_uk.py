import os
from io import StringIO
from typing import Dict, Iterable, List, Tuple

import pandas as pd
import requests


LEAGUE_NAMES: Dict[str, str] = {
    "E0": "잉글랜드 프리미어리그",
    "E1": "잉글랜드 챔피언십",
    "D1": "독일 분데스리가",
    "SP1": "스페인 라리가",
    "I1": "이탈리아 세리에A",
    "F1": "프랑스 리그1",
}


def _normalize_date(raw_date: str) -> str:
    raw = str(raw_date).strip()
    if not raw or raw.lower() == "nan":
        return ""

    if "/" in raw:
        parts = raw.split("/")
        if len(parts) == 3:
            day, month, year = parts
            if len(year) == 2:
                year = f"20{year}"
            return f"{year.zfill(4)}-{month.zfill(2)}-{day.zfill(2)}"

    return raw


def _safe_int_score(value):
    if value is None:
        return ""
    text = str(value).strip()
    if not text or text.lower() == "nan":
        return ""
    try:
        return str(int(float(text)))
    except Exception:
        return ""


def _season_candidates(season_code: str):
    clean = str(season_code).strip().replace("/", "")
    candidates = []

    if clean:
        candidates.append(clean)

    if len(clean) == 4 and clean.isdigit():
        reversed_pair = clean[2:] + clean[:2]
        if reversed_pair not in candidates:
            candidates.append(reversed_pair)

    for fallback in ["2526", "2425"]:
        if fallback not in candidates:
            candidates.append(fallback)

    return candidates


def _url_candidates(season: str, league_code: str):
    return [
        f"https://www.football-data.co.uk/mmz4281/{season}/{league_code}.csv",
        f"https://www.football-data.co.uk/mmz4371/{season}/{league_code}.csv",
    ]


def fetch_football_data_uk_history(
    season_code: str = "2526",
    league_codes: Iterable[str] = ("E0", "D1", "SP1"),
    timeout: int = 10,
) -> Tuple[pd.DataFrame, List[dict]]:
    """
    Football-Data.co.uk 시즌 CSV에서 실제 완료 경기만 표준 과거자료로 변환.
    앱 시작 시 자동호출 금지. 버튼을 눌렀을 때만 호출.
    """
    rows = []
    logs = []

    clean_input = str(season_code).strip().replace("/", "")
    if not clean_input.isdigit() or len(clean_input) != 4:
        return pd.DataFrame(), [{
            "source": "football-data.co.uk",
            "ok": False,
            "message": "시즌 코드는 2526처럼 4자리 숫자여야 합니다. 예: 2025/26 = 2526",
        }]

    for season in _season_candidates(clean_input):
        for code in league_codes:
            code = str(code).strip().upper()
            league_name = LEAGUE_NAMES.get(code, code)
            found_for_league = False

            for url in _url_candidates(season, code):
                log = {
                    "source": "football-data.co.uk",
                    "season": season,
                    "league_code": code,
                    "league": league_name,
                    "url": url,
                    "ok": False,
                    "http_status": "",
                    "rows": 0,
                    "message": "",
                }

                try:
                    response = requests.get(
                        url,
                        timeout=timeout,
                        headers={"User-Agent": "MARU-Sports-Analyzer/1.0"},
                    )
                    log["http_status"] = str(response.status_code)

                    if response.status_code != 200:
                        log["message"] = f"HTTP {response.status_code}"
                        logs.append(log)
                        continue

                    csv_text = response.content.decode("utf-8", errors="ignore")
                    df_raw = pd.read_csv(StringIO(csv_text))

                    required_cols = ["Date", "HomeTeam", "AwayTeam", "FTHG", "FTAG"]
                    missing = [c for c in required_cols if c not in df_raw.columns]
                    if missing:
                        log["message"] = f"필수 컬럼 누락: {missing}"
                        logs.append(log)
                        continue

                    df_raw = df_raw.dropna(subset=required_cols)

                    added = 0
                    for _, row in df_raw.iterrows():
                        date = _normalize_date(row.get("Date", ""))
                        home = str(row.get("HomeTeam", "")).strip()
                        away = str(row.get("AwayTeam", "")).strip()
                        hs = _safe_int_score(row.get("FTHG"))
                        aw = _safe_int_score(row.get("FTAG"))

                        if not date or not home or not away or hs == "" or aw == "":
                            continue

                        rows.append({
                            "date": date,
                            "kickoff_kst": "",
                            "league": league_name,
                            "home_team": home,
                            "away_team": away,
                            "home_score": hs,
                            "away_score": aw,
                            "status": "FT",
                            "source": f"football_data_uk_{season}_{code}",
                            "match_id": f"fd_uk_{season}_{code}_{date}_{home}_{away}",
                        })
                        added += 1

                    log["ok"] = True
                    log["rows"] = added
                    log["message"] = f"{added}건 변환"
                    logs.append(log)
                    found_for_league = True
                    break

                except Exception as exc:
                    log["message"] = str(exc)
                    logs.append(log)

            if found_for_league:
                continue

    df = pd.DataFrame(rows)
    if df.empty:
        return df, logs

    for col in df.columns:
        df[col] = df[col].astype(str)

    df = df.drop_duplicates(subset=["match_id"], keep="last")
    return df, logs


def merge_history_csv(path: str, df_new: pd.DataFrame):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)

    if df_new is None or df_new.empty:
        old_count = len(pd.read_csv(path)) if os.path.exists(path) else 0
        return 0, old_count

    df_new = df_new.copy()
    for col in df_new.columns:
        df_new[col] = df_new[col].astype(str)

    before_count = 0
    if os.path.exists(path):
        df_old = pd.read_csv(path)
        before_count = len(df_old)
        for col in df_old.columns:
            if df_old[col].dtype == "object":
                df_old[col] = df_old[col].astype(str)
        df_total = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df_total = df_new

    if "match_id" in df_total.columns:
        df_total = df_total.drop_duplicates(subset=["match_id"], keep="last")
    else:
        df_total = df_total.drop_duplicates(subset=["date", "home_team", "away_team"], keep="last")

    df_total.to_csv(path, index=False)
    after_count = len(df_total)
    return max(after_count - before_count, 0), after_count


def _read_csv(path: str) -> pd.DataFrame:
    if not os.path.exists(path):
        return pd.DataFrame()

    df = pd.read_csv(path)
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].astype(str)
    return df


def load_history_rows(path: str = "cache/history_matches.csv"):
    df = _read_csv(path)
    if df.empty:
        return []

    rows = []
    for row in df.to_dict(orient="records"):
        status = str(row.get("status", "")).lower()
        hs = str(row.get("home_score", "")).strip()
        aw = str(row.get("away_score", "")).strip()

        if status not in {"ft", "finished", "완료", "ended", "done"}:
            continue
        if hs in {"", "nan", "None"} or aw in {"", "nan", "None"}:
            continue

        rows.append(row)

    return rows


def load_upcoming_rows(path: str = "cache/upcoming_fixtures.csv"):
    df = _read_csv(path)
    if df.empty:
        return []

    rows = []
    for row in df.to_dict(orient="records"):
        status = str(row.get("status", "")).lower()
        hs = str(row.get("home_score", "")).strip()
        aw = str(row.get("away_score", "")).strip()

        if status in {"ft", "finished", "완료", "ended", "done"}:
            continue
        if hs not in {"", "nan", "None"} or aw not in {"", "nan", "None"}:
            continue

        rows.append(row)

    return rows
