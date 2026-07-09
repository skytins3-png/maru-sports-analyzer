import sys, types, importlib.util, os, tempfile, json

class SessionState(dict): pass
class FakeContext:
    def __init__(self, st): self.st=st
    def __enter__(self): return self.st
    def __exit__(self,*a): return False
class FakeStreamlit(types.ModuleType):
    def __init__(self):
        super().__init__('streamlit'); self.session_state=SessionState(); self.secrets={}; self.clicked_keys=set(); self.calls=[]
    def button(self,label, key=None, type='secondary', width=None, **kw): self.calls.append(('button',label,key)); return key in self.clicked_keys
    def checkbox(self,label, key=None, **kw): self.calls.append(('checkbox',label,key)); return False
    def columns(self,n,*a,**kw):
        if isinstance(n,(list,tuple)): n=len(n)
        return [FakeContext(self) for _ in range(n)]
    def expander(self,*a,**kw): return FakeContext(self)
    def tabs(self,names): return [FakeContext(self) for _ in names]
    def radio(self,*a,**kw): return (a[1][0] if len(a)>1 and a[1] else None)
    def selectbox(self,*a,**kw): return (a[1][0] if len(a)>1 and a[1] else None)
    def multiselect(self,*a,**kw): return kw.get('default', [])
    def number_input(self,*a,**kw): return kw.get('value', 0)
    def file_uploader(self,*a,**kw): return None
    def dataframe(self,*a,**kw): self.calls.append(('dataframe',))
    def json(self,*a,**kw): self.calls.append(('json',))
    def markdown(self,*a,**kw): self.calls.append(('markdown', str(a[0])[:80] if a else ''))
    def write(self,*a,**kw): self.calls.append(('write', str(a[0])[:80] if a else ''))
    def caption(self,*a,**kw): self.calls.append(('caption', str(a[0])[:80] if a else ''))
    def warning(self,*a,**kw): self.calls.append(('warning',str(a[0])[:80] if a else ''))
    def info(self,*a,**kw): self.calls.append(('info',str(a[0])[:80] if a else ''))
    def success(self,*a,**kw): self.calls.append(('success',str(a[0])[:80] if a else ''))
    def error(self,*a,**kw): self.calls.append(('error',str(a[0])[:80] if a else ''))
    def subheader(self,*a,**kw): pass
    def title(self,*a,**kw): pass
    def metric(self,*a,**kw): pass
    def download_button(self,*a,**kw): return False
    def link_button(self,*a,**kw): self.calls.append(('link_button', a[0] if a else ''))
    def set_page_config(self,*a,**kw): pass

fake=FakeStreamlit(); sys.modules['streamlit']=fake
spec=importlib.util.spec_from_file_location('app','app.py')
app=importlib.util.module_from_spec(spec); spec.loader.exec_module(app)

td=tempfile.mkdtemp(prefix='v21_app_test_'); os.chdir(td); app.ensure_dirs()
ok,msg,details=app.virtual_backend_test(); assert ok, (msg, details)
# Build six realistic sample fixtures and enough history, then run the real pipeline functions.
fixtures=app.pd.DataFrame([
 {'match_id':'s001','date':'2026-07-10','kickoff_kst':'19:00','league':'English Premier League','home_team':'Arsenal','away_team':'Coventry City','status':'SCHEDULED','source':'test'},
 {'match_id':'s002','date':'2026-07-10','kickoff_kst':'21:00','league':'English Premier League','home_team':'Wolverhampton Wanderers','away_team':'Blackburn Rovers','status':'SCHEDULED','source':'test'},
 {'match_id':'s003','date':'2026-07-11','kickoff_kst':'20:30','league':'German Bundesliga','home_team':'Bayern Munich','away_team':'Stuttgart','status':'SCHEDULED','source':'test'},
 {'match_id':'s004','date':'2026-07-11','kickoff_kst':'22:00','league':'Spanish La Liga','home_team':'Barcelona','away_team':'Athletic Bilbao','status':'SCHEDULED','source':'test'},
 {'match_id':'s005','date':'2026-08-16','kickoff_kst':'23:00','league':'Italian Serie A','home_team':'Udinese','away_team':'Como','status':'SCHEDULED','source':'test'},
 {'match_id':'s006','date':'2026-08-16','kickoff_kst':'23:30','league':'French Ligue 1','home_team':'Angers','away_team':'Lille','status':'SCHEDULED','source':'test'},
])
hist=[]
for _,f in fixtures.iterrows():
    for i in range(12):
        hist.append({'match_id':f'h{f.match_id}_{i}','date':f'2026-06-{i+1:02d}','league':f.league,'home_team':f.home_team,'away_team':f.away_team,'home_score':2 if i%2 else 1,'away_score':1 if i%3 else 2,'status':'FT','source':'test'})
        hist.append({'match_id':f'a{f.match_id}_{i}','date':f'2026-05-{i+1:02d}','league':f.league,'home_team':'Other','away_team':f.away_team,'home_score':1,'away_score':1 if i%2 else 2,'status':'FT','source':'test'})
history=app.pd.DataFrame(hist)
app.write_csv(app.SOURCE_FILES['source_livescore_fixtures'], fixtures)
app.write_csv(app.SOURCE_FILES['source_football_data'], history)
analysis,mobile,meta=app.run_standardize_and_analyze()
assert len(analysis) == 60, len(analysis)
assert len(mobile) == 60, len(mobile)
board=app.read_csv(app.OUTPUT_FILES['fixture_prediction_results']); exp=app.read_csv(app.OUTPUT_FILES['prediction_explain']); chk=app.read_csv(app.OUTPUT_FILES['offline_checklist'])
assert len(board) == 6, len(board); assert len(exp)==6; assert len(chk)==6
assert set(chk['auto_buy'].astype(str).unique()) == {'NO'}
assert set(chk['auto_payment'].astype(str).unique()) == {'NO'}
payload=app.build_hub_payload('v21_test'); ok_payload, problems, summary=app.validate_hub_payload(payload); assert ok_payload, problems
# Button click/toggle test.
mdf=analysis[analysis['match_id'].astype(str)==analysis.iloc[0]['match_id']]; first=mdf.iloc[0].to_dict()
base=app.safe_key('v21test', first['match_id'], app.ko_team(first['home_team']), app.ko_team(first['away_team']))
fake.clicked_keys={f'btn_analysis_{base}', f'btn_ticket_{base}', f'btn_hub_{base}'}
app.render_mobile_clickable_controls(mdf, {'match_id':first['match_id'],'date':first['date'],'kickoff_kst':first['kickoff_kst']}, 'v21test', 'match')
assert fake.session_state.get(f'analysis_{base}') is True
assert fake.session_state.get(f'ticket_{base}') is True
assert fake.session_state.get(f'hub_{base}') is True
assert any(c[0]=='checkbox' for c in fake.calls), 'offline checklist checkboxes not rendered'
assert any(c[0]=='button' and '분석보기' in c[1] for c in fake.calls), 'analysis button missing'
assert any(c[0]=='button' and '오프라인 체크' in c[1] for c in fake.calls), 'offline button missing'
assert any(c[0]=='button' and '허브확인' in c[1] for c in fake.calls), 'hub button missing'
print(json.dumps({'ok':True,'virtual_backend':details,'analysis_rows':len(analysis),'mobile_rows':len(mobile),'board_rows':len(board),'explain_rows':len(exp),'checklist_rows':len(chk),'payload_summary':summary,'button_count':len([c for c in fake.calls if c[0]=='button']),'checkbox_count':len([c for c in fake.calls if c[0]=='checkbox'])}, ensure_ascii=False, indent=2))
