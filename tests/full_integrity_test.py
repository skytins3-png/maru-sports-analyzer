import sys, ast, types
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

required = [
    "app.py",
    "sports/sportmonks_client.py",
    "sports/history_store.py",
    "sports/fallback_collector.py",
    "sports/football_fixtures.py",
    "ui/history_range_test_panel.py",
    "ui/history_store_panel.py",
    "ui/sportmonks_diagnostic_panel.py",
]
missing = [p for p in required if not (ROOT/p).exists()]
assert not missing, f"필수 파일 누락: {missing}"

for py in ROOT.rglob("*.py"):
    if "legacy_" in str(py):
        continue
    tree = ast.parse(py.read_text(encoding="utf-8"))
    names = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name in ('__init__',):
                continue
            names[node.name] = names.get(node.name, 0) + 1
    dup = {k:v for k,v in names.items() if v > 1}
    assert not dup, f"중복 함수/클래스 발견 {py.relative_to(ROOT)}: {dup}"

app_text = (ROOT/"app.py").read_text(encoding="utf-8")
assert "render_history_range_test_panel()" in app_text
assert "render_history_store_panel(fixtures)" in app_text
assert "render_sportmonks_diagnostic_panel()" in app_text

class Dummy:
    def __enter__(self): return self
    def __exit__(self, *args): return False
    def __getattr__(self, name):
        def f(*args, **kwargs):
            if name == "columns":
                spec = args[0] if args else 1
                n = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
                return [Dummy() for _ in range(n)]
            if name in ("expander", "spinner", "sidebar", "container"):
                return Dummy()
            if name == "selectbox":
                options = args[1] if len(args)>1 else []
                return options[kwargs.get("index", 0)] if options else None
            if name == "toggle":
                return kwargs.get("value", False)
            if name == "button":
                return False
            if name == "file_uploader":
                return None
            return None
        return f

class FakeStreamlit(Dummy):
    def __init__(self):
        self.secrets = {}
        self.session_state = {}
        self.sidebar = Dummy()
    def set_page_config(self, *a, **k): return None
    def columns(self, spec, *a, **k):
        n = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
        return [Dummy() for _ in range(n)]
    def tabs(self, names): return [Dummy() for _ in names]
    def expander(self, *a, **k): return Dummy()
    def container(self, *a, **k): return Dummy()
    def spinner(self, *a, **k): return Dummy()
    def selectbox(self, label, options, index=0, **kwargs): return options[index] if options else None
    def toggle(self, *a, value=False, **k): return value
    def button(self, *a, **k): return False
    def file_uploader(self, *a, **k): return None
    def number_input(self, *a, value=0, **k): return value
    def text_input(self, *a, value="", **k): return value
    def text_area(self, *a, value="", **k): return value
    def dataframe(self, *a, **k): return None
    def json(self, *a, **k): return None
    def metric(self, *a, **k): return None

sys.modules["streamlit"] = FakeStreamlit()

fake_requests = types.ModuleType("requests")
def forbidden_get(*args, **kwargs):
    raise AssertionError("앱 시작 시 외부 API 호출 발생")
fake_requests.get = forbidden_get
sys.modules["requests"] = fake_requests

import app
assert hasattr(app, "main")
app.main()

from sports.history_store import normalize_history_df, append_history, load_history, analyze_fixture_from_history, history_summary
from sports.fallback_collector import collect_history_with_fallback

sample = pd.DataFrame([
    {"date":"2026-07-01","league":"TEST","home_team":"A","away_team":"B","home_score":2,"away_score":1},
    {"date":"2026-07-02","league":"TEST","home_team":"C","away_team":"A","home_score":0,"away_score":1},
    {"date":"2026-07-03","league":"TEST","home_team":"B","away_team":"C","home_score":1,"away_score":1},
    {"date":"2026-07-04","league":"TEST","home_team":"A","away_team":"C","home_score":3,"away_score":0},
])
norm, info = normalize_history_df(sample)
assert info["ok"], info
res = append_history(norm)
assert res["ok"], res
hist = load_history()
assert len(hist) >= 4
analysis = analyze_fixture_from_history({"match_id":"x","home_team":"A","away_team":"B"}, hist)
assert "analysis_possible" in analysis
assert history_summary()["rows"] >= 4
fallback = collect_history_with_fallback(days_back=1)
assert "steps" in fallback
print("FULL_INTEGRITY_TEST_OK")
