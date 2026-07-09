# MARU SPORTS v24 모바일 주소 복사/QR/버튼 클릭 패치

이 ZIP은 사용자가 올린 v23 단일 app.py를 기준으로 v24 패치를 직접 적용한 통합본입니다.
기존 수집/분석/허브/구글시트/모바일 추천 기능은 제거하지 않고, PC 상단 모바일 주소 안내와 모바일 버튼 클릭 안정화만 추가했습니다.

## 적용 내용

1. PC 화면 상단에 모바일 주소 크게 표시
2. 모바일 주소 복사 버튼 추가
3. 버튼이 안 눌릴 경우 직접 복사 가능한 텍스트 입력창 추가
4. QR코드 추가
5. 모바일 주소 고정
   - https://maru-sports-analyzer-lphmsfeyb47kgcrq4aevhs.streamlit.app/?mode=mobile
6. 모바일의 `분석보기 / 오프라인 체크 / 허브확인` 버튼을 실제 Streamlit 버튼으로 유지
7. 버튼 렌더 호환성을 위해 `width="stretch"`를 `use_container_width=True` 방식으로 변경

## 업로드 방법

GitHub 저장소 `maru-sports-analyzer`에서 기존 `app.py`를 이 ZIP의 `app.py`로 교체하세요.
`requirements.txt`도 함께 올리면 QR코드 생성용 qrcode 패키지가 설치됩니다.

## 주의

이 앱은 자동구매/자동결제 기능이 없습니다.
모바일 화면은 오프라인 수동 체크 및 허브 저장 확인용입니다.
