# MARU SPORTS v24 MOBILE COPY/QR/CLICK FIX

기준 파일: 사용자가 업로드한 `maru-sports-proto-fixture-hub-v23-auto-schedule-proto-match(1).zip`

## 반영 내용
- v23 전체 파일 구조 유지
- app.py 버전: v24-mobile-copy-qr-click-fix
- PC 상단에 모바일 주소 크게 표시
- 모바일 주소 복사 버튼 추가
- 버튼 실패 대비 직접 복사용 텍스트 박스 추가
- QR코드 표시 추가
- 모바일 분석보기 / 오프라인 체크 / 허브확인 실제 Streamlit 버튼 유지
- 모바일 버튼 `width="stretch"` 제거, `use_container_width=True`로 안정화

## 모바일 주소
https://maru-sports-analyzer-lphmsfeyb47kgcrq4aevhs.streamlit.app/?mode=mobile

## 테스트 결과
- app.py py_compile PASS
- run_v22_tests.py PASS
- v24 UI 정적 검사 PASS
- 기존 자동구매/자동결제 없음 유지

## 배포
ZIP의 모든 파일을 GitHub 저장소 루트에 올려 기존 파일을 교체하세요.
