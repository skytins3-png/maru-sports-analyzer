import subprocess, sys, os, ast, zipfile, json, re
from pathlib import Path
root=Path(__file__).resolve().parent
app=root/'app.py'
results=[]

def add(name, ok, detail=''):
    results.append({'name':name,'ok':bool(ok),'detail':detail})

# 1 syntax
r=subprocess.run([sys.executable,'-m','py_compile',str(app)],capture_output=True,text=True)
add('app.py 문법 검사', r.returncode==0, r.stderr[-500:])
# 2 duplicate function names
mod=ast.parse(app.read_text(encoding='utf-8'))
funcs=[n.name for n in ast.walk(mod) if isinstance(n, ast.FunctionDef)]
dups=sorted({x for x in funcs if funcs.count(x)>1})
add('함수 중복 검사', not dups, ','.join(dups))
# 3 required tokens
s=app.read_text(encoding='utf-8')
required=['render_mobile_clickable_controls','_toggle_button','render_mobile_offline_ticket_panel','render_mobile_hub_panel','_toggle_button("🔍 분석보기"','st.checkbox(item','v21-clickable-offline-ticket-mobile','자동구매/자동결제 없음']
missing=[x for x in required if x not in s]
add('필수 모바일 클릭 코드 존재', not missing, 'missing='+repr(missing))
# 4 no auto buy/payment positive flags in app (except text warnings and field names)
auto_bad=[m.group(0) for m in re.finditer(r'auto_(?:buy|payment)"?\s*[:=]\s*"?(?:YES|Y|ON|TRUE|1)', s, re.I)]
add('자동구매/자동결제 활성값 없음', not auto_bad, repr(auto_bad))
# 5 clickable test repeated 10x
for i in range(10):
    r=subprocess.run([sys.executable, str(root/'v21_click_test.py')],cwd=str(root),capture_output=True,text=True,timeout=120)
    add(f'가상 데이터+버튼 클릭 테스트 {i+1}/10', r.returncode==0, (r.stdout[-500:] if r.returncode==0 else r.stderr[-1000:]))
# 6 zip duplicate check after package (done separately by packer)
all_ok=all(x['ok'] for x in results)
report={'all_ok':all_ok,'results':results}
print(json.dumps(report, ensure_ascii=False, indent=2))
Path(root/'TEST_REPORT_JSON.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
# markdown
lines=['# v21 TEST REPORT','','- version: v21-clickable-offline-ticket-mobile','- purpose: 실제 눌리는 모바일 버튼 + 오프라인 수동구매 체크 + 허브 확인','']
for r in results:
    lines.append(f"- [{'PASS' if r['ok'] else 'FAIL'}] {r['name']}: {r['detail'][:300]}")
lines += ['','## 검증 범위','- app.py 문법 검사','- 함수 중복 검사','- 모바일 클릭 버튼 코드 존재 검사','- 자동구매/자동결제 활성값 없음 검사','- 6경기 × 10개 승부식 = 60건 분석 생성 확인','- 전체 경기판 6건 생성 확인','- 분석 이유 6건 생성 확인','- 오프라인 체크표 6건 생성 확인','- 분석보기/오프라인 체크/허브확인 버튼 토글 확인','- 오프라인 체크박스 8개 렌더 확인','', '## 한계','- 이 테스트는 컨테이너 안에서 fake Streamlit으로 버튼 클릭 로직을 검증한 것입니다. Streamlit Cloud 실제 배포 후 휴대폰 화면 확인은 ZIP 업로드 뒤 마지막으로 확인해야 합니다.']
Path(root/'TEST_REPORT.md').write_text('\n'.join(lines), encoding='utf-8')
sys.exit(0 if all_ok else 1)
