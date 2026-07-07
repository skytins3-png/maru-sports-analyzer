import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class DummyContext:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def __call__(self, *args, **kwargs):
        return self

    def __getattr__(self, name):
        def f(*args, **kwargs):
            if name == "columns":
                spec = args[0] if args else 1
                n = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
                return [DummyContext() for _ in range(n)]
            if name == "tabs":
                return [DummyContext() for _ in (args[0] if args else [])]
            if name in ("expander", "container", "spinner", "form"):
                return DummyContext()
            if name == "selectbox":
                options = args[1] if len(args) > 1 else []
                return options[kwargs.get("index", 0)] if options else None
            if name == "toggle":
                return kwargs.get("value", False)
            if name == "button":
                return False
            if name == "form_submit_button":
                return False
            if name == "number_input":
                return kwargs.get("value", 0)
            if name == "text_input":
                return kwargs.get("value", "")
            if name == "text_area":
                return kwargs.get("value", "")
            if name == "slider":
                return kwargs.get("value", 0)
            return None
        return f


class FakeStreamlit(DummyContext):
    def __init__(self):
        self.secrets = {}
        self.session_state = {}
        self.sidebar = DummyContext()

    def columns(self, spec, *args, **kwargs):
        n = len(spec) if isinstance(spec, (list, tuple)) else int(spec)
        return [DummyContext() for _ in range(n)]

    def tabs(self, names):
        return [DummyContext() for _ in names]

    def expander(self, *args, **kwargs):
        return DummyContext()

    def container(self, *args, **kwargs):
        return DummyContext()

    def spinner(self, *args, **kwargs):
        return DummyContext()

    def form(self, *args, **kwargs):
        return DummyContext()

    def selectbox(self, label, options, index=0, **kwargs):
        return options[index] if options else None

    def toggle(self, *args, value=False, **kwargs):
        return value

    def button(self, *args, **kwargs):
        return False

    def form_submit_button(self, *args, **kwargs):
        return False

    def number_input(self, *args, value=0, **kwargs):
        return value

    def text_input(self, *args, value="", **kwargs):
        return value

    def text_area(self, *args, value="", **kwargs):
        return value

    def slider(self, *args, value=0, **kwargs):
        return value

    def dataframe(self, *args, **kwargs):
        return None

    def json(self, *args, **kwargs):
        return None

    def set_page_config(self, *args, **kwargs):
        return None


# Streamlit 없이도 app import/main 흐름을 검사하기 위한 가짜 Streamlit
sys.modules["streamlit"] = FakeStreamlit()

# 앱 시작 시 외부 API가 호출되면 실패 처리
fake_requests = types.ModuleType("requests")

def forbidden_get(*args, **kwargs):
    raise AssertionError("앱 시작 시 requests.get 외부 API 호출이 발생함")

fake_requests.get = forbidden_get
sys.modules["requests"] = fake_requests

import app

assert hasattr(app, "main")
app.main()

from sports.sportmonks_client import test_history_range, test_history_ranges, run_diagnostic_test
from sports.football_fixtures import load_sample_fixtures

rows = load_sample_fixtures()
assert rows and rows[0].get("data_source") == "sample_safe_boot"
assert callable(test_history_range)
assert callable(test_history_ranges)
assert callable(run_diagnostic_test)

print("STRICT_STARTUP_NO_API_OK")
