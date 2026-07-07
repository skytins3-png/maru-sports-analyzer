from __future__ import annotations
import os
import sys
import types
import importlib
import py_compile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.chdir(ROOT)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

class DummyContext:
    def __enter__(self): return self
    def __exit__(self, exc_type, exc, tb): return False

class DummyStreamlit(types.ModuleType):
    def __init__(self):
        super().__init__('streamlit')
        self.secrets = {}
        self.session_state = {}
        self._maru_dataframe_patched = False
    def __getattr__(self, name):
        if name in ('sidebar','columns','tabs'):
            return lambda *a, **k: [DummyContext(), DummyContext(), DummyContext(), DummyContext()]
        if name in ('expander','spinner','container'):
            return lambda *a, **k: DummyContext()
        if name == 'dataframe':
            return lambda *a, **k: None
        if name == 'button':
            return lambda *a, **k: False
        return lambda *a, **k: None

sys.modules['streamlit'] = DummyStreamlit()

required_files = [
    'app.py',
    'sports/sportmonks_client.py',
    'sports/football_fixtures.py',
    'ui/sportmonks_diagnostic_panel.py',
    'sports/__init__.py',
    'ui/__init__.py',
]
for rel in required_files:
    assert (ROOT / rel).exists(), f'MISSING {rel}'

client_text = (ROOT / 'sports/sportmonks_client.py').read_text(encoding='utf-8')
panel_text = (ROOT / 'ui/sportmonks_diagnostic_panel.py').read_text(encoding='utf-8')
app_text = (ROOT / 'app.py').read_text(encoding='utf-8')
assert 'def run_diagnostic_test' in client_text
assert 'def fetch_sportmonks_fixtures' in client_text
assert 'from sports.sportmonks_client import run_diagnostic_test' not in '\n'.join(panel_text.splitlines()[:5])
assert 'render_sportmonks_diagnostic_panel()' in app_text

for py in ROOT.rglob('*.py'):
    if any(part in {'__pycache__'} for part in py.parts):
        continue
    py_compile.compile(str(py), doraise=True)

mods = [
    'sports.sportmonks_client',
    'sports.football_fixtures',
    'ui.sportmonks_diagnostic_panel',
    'sports.toto_dual_engine',
    'sports.toto_adapter',
    'app',
]
for name in mods:
    importlib.import_module(name)

from sports.sportmonks_client import run_diagnostic_test, fetch_sportmonks_fixtures
for key in ['SPORTMONKS_API_TOKEN','SPORTS_API_KEY','SKYTOTO_SPORTS_API_URL']:
    os.environ.pop(key, None)
no_key = run_diagnostic_test()
assert no_key['token_detected'] is False
assert no_key['fixtures_count'] == 0
assert '없음' in no_key['info']['message']

import sports.sportmonks_client as sm
class FakeResp:
    status_code = 200
    text = ''
    def json(self):
        return {'data': [{'id': 11, 'starting_at': '2026-07-08 19:00:00', 'league': {'name':'TEST LEAGUE'}, 'participants': [{'name':'Home FC','meta':{'location':'home'}}, {'name':'Away FC','meta':{'location':'away'}}]}]}

def fake_get(url, timeout=20):
    return FakeResp()
sm.requests.get = fake_get
os.environ['SPORTMONKS_API_TOKEN'] = 'TESTTOKEN123456'
rows, info = fetch_sportmonks_fixtures(date_dash='2026-07-08')
assert info['ok'] is True
assert rows and rows[0]['data_source'] == 'sportmonks'
assert rows[0]['home_team'] == 'Home FC'
assert rows[0]['away_team'] == 'Away FC'
print('SELF_TEST_OK')
