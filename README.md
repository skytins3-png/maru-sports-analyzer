# MARU SPORTS ANALYZER

축구 경기 자료수집 · 분석 · 추천 참고용 Streamlit 앱입니다.

## 핵심 원칙

- 기존 MARU KRA 구조를 제거하지 않고 확장합니다.
- 자동구매, 자동결제, 베팅 대행 기능은 없습니다.
- Google Apps Script + Google Sheet 허브 저장 구조를 유지합니다.
- GitHub Actions 자동 실행 구조를 유지합니다.
- 모바일 추천 카드 중심으로 표시합니다.
- 느린 API는 후순위 처리하고, 실패 시 캐시를 사용합니다.
- 추천 데이터가 비어 있으면 억지 추천을 만들지 않습니다.

## 1차 목표

- 축구 전용
- 승무패 분석
- 언오버 분석
- 경기 전 변동자료 수집
- 경기 후 결과 저장
- Google Sheet 허브 저장
- Streamlit Cloud 배포
- GitHub Actions 자동 실행

## 앱 실행

```bash
pip install -r requirements.txt
streamlit run app.py
```

## GitHub Secrets 권장값

```text
SPORTS_API_KEY
ODDS_API_KEY
WEATHER_API_KEY
GAS_WEBAPP_URL
GOOGLE_SHEET_ID
USE_SLOW_API
```

## 안전 문구

본 앱은 스포츠 경기 자료수집, 통계 분석, 추천 참고용 도구입니다.  
자동구매, 자동결제, 베팅 대행 기능은 제공하지 않습니다.  
최종 선택과 책임은 사용자 본인에게 있습니다.


## 합본 업데이트: SKYTOTO 듀얼 분석 엔진 흡수

업로드된 기존 토토앱에서 다음 기능만 분리해 `sports/` 모듈로 합쳤습니다.

- `sports/toto_dual_engine.py`: MatchInput, AnalysisResult, hub_analyze, sheet_analyze, compare_results, review_prediction
- `sports/backtest_engine.py`: 백테스트 래퍼
- `sports/toto_adapter.py`: MARU SPORTS 경기/스냅샷을 듀얼 엔진 입력으로 변환
- `ui/dual_engine_panel.py`: Streamlit 실험/백테스트 패널
- `legacy_toto/`: 기존 토토앱 원본 보존

주의: 자동구매/자동결제 기능은 추가하지 않았습니다.
