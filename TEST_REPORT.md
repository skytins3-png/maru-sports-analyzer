# v23-auto-schedule-proto-match TEST REPORT

- time: 2026-07-09 20:52:05 KST
- status: PASS
- total_checks: 79

## 핵심 확인

- app.py 문법 검사: PASS
- eventsday 날짜범위 자동수집 코드: PASS
- 형님 수동 일정표 붙여넣기 없이 자동수집 source_livescore_schedule 생성 구조: PASS
- 프로토 자료 + 자동수집 일정 매칭: PASS
- MATCHED 경기만 구매용 표준 일정/오프라인 체크표 생성: PASS
- 8월/먼 미래 경기 구매용 제외: PASS
- 자동구매/자동결제 없음: PASS

## 반복 테스트
- version_v23: PASS 
- eventsday_api_present: PASS 
- eventsnextleague_not_primary: PASS 
- strict_matched_only: PASS 
- auto_buttons_present: PASS 
- no_auto_buy_code: PASS 
- no_auto_payment_code: PASS 
- function_duplicates: PASS []
- loop_1_matched_count: PASS matched=3
- loop_1_aug_excluded_purchase: PASS purchase_dates=0    2026-07-09
1    2026-07-10
Name: date, dtype: object
- loop_1_strict_standard_only_matched: PASS fixtures=2 purchase=2 msg=구매용 MATCHED 경기 2건 표준화
- loop_1_offline_checklist_created: PASS checklist=2 fixtures=2
- loop_1_board_created: PASS board=2 fixtures=2
- loop_1_no_auto_buy: PASS 
- loop_1_no_auto_payment: PASS 
- loop_2_matched_count: PASS matched=3
- loop_2_aug_excluded_purchase: PASS purchase_dates=0    2026-07-09
1    2026-07-10
Name: date, dtype: object
- loop_2_strict_standard_only_matched: PASS fixtures=2 purchase=2 msg=구매용 MATCHED 경기 2건 표준화
- loop_2_offline_checklist_created: PASS checklist=2 fixtures=2
- loop_2_board_created: PASS board=2 fixtures=2
- loop_2_no_auto_buy: PASS 
- loop_2_no_auto_payment: PASS 
- loop_3_matched_count: PASS matched=3
- loop_3_aug_excluded_purchase: PASS purchase_dates=0    2026-07-09
1    2026-07-10
Name: date, dtype: object
- loop_3_strict_standard_only_matched: PASS fixtures=2 purchase=2 msg=구매용 MATCHED 경기 2건 표준화
- loop_3_offline_checklist_created: PASS checklist=2 fixtures=2
- loop_3_board_created: PASS board=2 fixtures=2
- loop_3_no_auto_buy: PASS 
- loop_3_no_auto_payment: PASS 
- loop_4_matched_count: PASS matched=3
- loop_4_aug_excluded_purchase: PASS purchase_dates=0    2026-07-09
1    2026-07-10
Name: date, dtype: object
- loop_4_strict_standard_only_matched: PASS fixtures=2 purchase=2 msg=구매용 MATCHED 경기 2건 표준화
- loop_4_offline_checklist_created: PASS checklist=2 fixtures=2
- loop_4_board_created: PASS board=2 fixtures=2
- loop_4_no_auto_buy: PASS 
- loop_4_no_auto_payment: PASS 
- loop_5_matched_count: PASS matched=3
- loop_5_aug_excluded_purchase: PASS purchase_dates=0    2026-07-09
1    2026-07-10
Name: date, dtype: object
- loop_5_strict_standard_only_matched: PASS fixtures=2 purchase=2 msg=구매용 MATCHED 경기 2건 표준화
- loop_5_offline_checklist_created: PASS checklist=2 fixtures=2
- loop_5_board_created: PASS board=2 fixtures=2
- loop_5_no_auto_buy: PASS 
- loop_5_no_auto_payment: PASS 
- loop_6_matched_count: PASS matched=3
- loop_6_aug_excluded_purchase: PASS purchase_dates=0    2026-07-09
1    2026-07-10
Name: date, dtype: object
- loop_6_strict_standard_only_matched: PASS fixtures=2 purchase=2 msg=구매용 MATCHED 경기 2건 표준화
- loop_6_offline_checklist_created: PASS checklist=2 fixtures=2
- loop_6_board_created: PASS board=2 fixtures=2
- loop_6_no_auto_buy: PASS 
- loop_6_no_auto_payment: PASS 
- loop_7_matched_count: PASS matched=3
- loop_7_aug_excluded_purchase: PASS purchase_dates=0    2026-07-09
1    2026-07-10
Name: date, dtype: object
- loop_7_strict_standard_only_matched: PASS fixtures=2 purchase=2 msg=구매용 MATCHED 경기 2건 표준화
- loop_7_offline_checklist_created: PASS checklist=2 fixtures=2
- loop_7_board_created: PASS board=2 fixtures=2
- loop_7_no_auto_buy: PASS 
- loop_7_no_auto_payment: PASS 
- loop_8_matched_count: PASS matched=3
- loop_8_aug_excluded_purchase: PASS purchase_dates=0    2026-07-09
1    2026-07-10
Name: date, dtype: object
- loop_8_strict_standard_only_matched: PASS fixtures=2 purchase=2 msg=구매용 MATCHED 경기 2건 표준화
- loop_8_offline_checklist_created: PASS checklist=2 fixtures=2
- loop_8_board_created: PASS board=2 fixtures=2
- loop_8_no_auto_buy: PASS 
- loop_8_no_auto_payment: PASS 
- loop_9_matched_count: PASS matched=3
- loop_9_aug_excluded_purchase: PASS purchase_dates=0    2026-07-09
1    2026-07-10
Name: date, dtype: object
- loop_9_strict_standard_only_matched: PASS fixtures=2 purchase=2 msg=구매용 MATCHED 경기 2건 표준화
- loop_9_offline_checklist_created: PASS checklist=2 fixtures=2
- loop_9_board_created: PASS board=2 fixtures=2
- loop_9_no_auto_buy: PASS 
- loop_9_no_auto_payment: PASS 
- loop_10_matched_count: PASS matched=3
- loop_10_aug_excluded_purchase: PASS purchase_dates=0    2026-07-09
1    2026-07-10
Name: date, dtype: object
- loop_10_strict_standard_only_matched: PASS fixtures=2 purchase=2 msg=구매용 MATCHED 경기 2건 표준화
- loop_10_offline_checklist_created: PASS checklist=2 fixtures=2
- loop_10_board_created: PASS board=2 fixtures=2
- loop_10_no_auto_buy: PASS 
- loop_10_no_auto_payment: PASS 
- auto_collect_and_match_summary: PASS {"time": "2026-07-09 20:52:05 KST", "days": 7, "auto_schedule_rows": 3, "auto_schedule_total": 3, "proto_rows": 3, "matched_rows": 3, "purchase_rows_today_7d": 2, "message": "자동수집 일정과 프로토 자료 매칭 완료"}