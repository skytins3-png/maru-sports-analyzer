import os, sys, json, zipfile, ast, importlib.util, shutil
from pathlib import Path
import pandas as pd

# fake streamlit for backend tests if streamlit is unavailable
import types
if 'streamlit' not in sys.modules:
    st=types.ModuleType('streamlit')
    st.secrets={}
    st.session_state={}
    st.query_params={}
    def _noop(*a, **k): return None
    def _false(*a, **k): return False
    def _empty_df(*a, **k): return None
    for name in ['markdown','caption','subheader','warning','info','success','error','write','json','dataframe','metric','link_button','download_button','set_page_config','title']:
        setattr(st,name,_noop)
    st.button=_false
    st.checkbox=_false
    st.text_area=lambda *a, **k: k.get('value','')
    st.radio=lambda *a, **k: (a[1][0] if len(a)>1 and a[1] else '')
    st.selectbox=lambda *a, **k: (a[1][0] if len(a)>1 and a[1] else '')
    st.multiselect=lambda *a, **k: k.get('default',[])
    st.number_input=lambda *a, **k: k.get('value',0)
    class Ctx:
        def __enter__(self): return self
        def __exit__(self,*a): return False
    st.expander=lambda *a, **k: Ctx()
    st.columns=lambda n,*a,**k: [Ctx() for _ in range(n if isinstance(n,int) else len(n))]
    st.tabs=lambda names: [Ctx() for _ in names]
    sys.modules['streamlit']=st

ROOT=Path(__file__).resolve().parent
os.chdir(ROOT)
# clean runtime data for deterministic test
for d in ['data','logs','payloads']:
    shutil.rmtree(ROOT/d, ignore_errors=True)

spec=importlib.util.spec_from_file_location('app', ROOT/'app.py')
app=importlib.util.module_from_spec(spec)
sys.modules['app']=app
spec.loader.exec_module(app)
app.ensure_dirs()

def assert_true(cond, msg):
    if not cond:
        raise AssertionError(msg)

results=[]
# 1 compile checked by caller
results.append({'name':'import app','status':'PASS','version':app.APP_VERSION})
# function duplicate check
src=(ROOT/'app.py').read_text(encoding='utf-8')
tree=ast.parse(src)
funcs=[n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
dups=sorted(set([f for f in funcs if funcs.count(f)>1]))
assert_true(not dups, f'duplicate functions {dups}')
results.append({'name':'function duplicate','status':'PASS','dups':dups})
# Sample proto/livescore including 8월 future non-matched source
proto_text='''proto_game_no,date,kickoff_kst,league,home_team,away_team,market_type,line_value,proto_pick,proto_odds
5702,2026-07-10,20:00,국제,한국M,일본M,승무패,,패,1.15
5788,2026-07-10,22:00,국제,미국,벨기에,핸디캡,+1.0,승,1.48
5820,2026-07-10,23:00,MLB,LA다저스,콜로라도,언더오버,10.5,오버,1.82
9999,2026-08-16,15:00,EPL,아스널,코번트리,승무패,,홈승,1.44
'''
live_text='''date,kickoff_kst,sport,league,home_team,away_team,status,source
2026-07-10,20:00,축구,국제,한국M,일본M,SCHEDULED,livescore_manual
2026-07-10,22:00,축구,국제,미국,벨기에,SCHEDULED,livescore_manual
2026-07-10,23:00,야구,MLB,LA Dodgers,Colorado Rockies,SCHEDULED,livescore_manual
2026-08-16,15:00,축구,EPL,Arsenal,Coventry,SCHEDULED,livescore_manual
'''
proto=app.prepare_proto_ticket_df(app.parse_proto_or_livescore_text(proto_text))
live=app.prepare_livescore_schedule_df(app.parse_proto_or_livescore_text(live_text))
app.write_csv(app.SOURCE_FILES['source_proto_ticket'], proto)
app.write_csv(app.SOURCE_FILES['source_livescore_schedule'], live)
matched=app.match_proto_with_livescore()
assert_true(len(matched)==4, f'matched rows expected 4 got {len(matched)}')
assert_true((matched['proto_livescore_status']=='MATCHED').sum()==4, matched.to_dict('records'))
results.append({'name':'proto+livescore match engine','status':'PASS','matched':len(matched)})
std,msg=app.standardize_fixtures()
# today is 2026-07-09 in this runtime. only 2026-07-10 rows should pass 7-day window, 8월 excluded.
assert_true(len(std)==3, f'std rows should exclude 8월 future, got {len(std)} rows: {std.to_dict("records")} msg={msg}')
assert_true('2026-08-16' not in set(std['date'].astype(str)), '8월 row leaked to purchase standard fixtures')
assert_true(set(std['proto_livescore_status'])=={'MATCHED'}, 'non matched leaked')
results.append({'name':'standardize matched only + 8월 exclude','status':'PASS','rows':len(std),'msg':msg})
# add minimal history and run analysis
hist_rows=[]
for home,away in [('한국M','일본M'),('미국','벨기에'),('LA다저스','콜로라도')]:
    for i in range(10):
        hist_rows.append({'match_id':f'h_{home}_{away}_{i}','date':f'2026-06-{i+1:02d}','league':'테스트','home_team':home,'away_team':away,'home_score':2+(i%2),'away_score':1,'status':'FT','source':'test'})
app.write_csv(app.STANDARD_FILES['standard_history_matches'], pd.DataFrame(hist_rows))
# generate history source too to avoid empty standardize_history overwriting? Direct call standardize_and_analyze calls standardize_history from source_football_data.
app.write_csv(app.SOURCE_FILES['source_football_data'], pd.DataFrame(hist_rows))
analysis,mobile,meta=app.run_standardize_and_analyze()
assert_true(len(app.read_csv(app.STANDARD_FILES['standard_upcoming_fixtures']))==3, 'standard fixture count after analysis not 3')
assert_true(len(app.read_csv(app.OUTPUT_FILES['offline_checklist']))==3, 'offline checklist should be matched 3 games only')
assert_true(len(app.read_csv(app.OUTPUT_FILES['fixture_prediction_results']))==3, 'fixture board should be matched 3 games only')
chk=app.read_csv(app.OUTPUT_FILES['offline_checklist'])
for c in ['proto_game_no','livescore_match_status','match_score','auto_buy','auto_payment']:
    assert_true(c in chk.columns, f'missing checklist col {c}')
assert_true(set(chk['auto_buy'].astype(str))=={'NO'} and set(chk['auto_payment'].astype(str))=={'NO'}, 'auto flags fail')
assert_true(set(chk['livescore_match_status'].astype(str))=={'MATCHED'}, 'checklist non matched leaked')
results.append({'name':'analysis outputs matched-only offline checklist','status':'PASS','analysis_rows':len(analysis),'mobile_rows':len(mobile),'checklist_rows':len(chk)})
# run full pipeline should not break
report=app.run_full_pipeline(auto_fixtures=False, auto_history=False, send_hub=False)
assert_true(len(app.read_csv(app.OUTPUT_FILES['offline_checklist']))==3, 'full pipeline changed checklist count')
results.append({'name':'full pipeline no external matched-only','status':'PASS','report':report})
# source scan rules
forbidden=['자동구매 실행','자동결제 실행','구매하기','결제하기']
found=[x for x in forbidden if x in src]
assert_true(not found, f'forbidden strings found: {found}')
for needed in ['match_proto_with_livescore','source_proto_ticket','source_livescore_schedule','matched_proto_livescore','proto_livescore_status']:
    assert_true(needed in src, f'needed string missing {needed}')
results.append({'name':'source guard strings','status':'PASS'})
print(json.dumps({'status':'PASS','results':results}, ensure_ascii=False, indent=2))
