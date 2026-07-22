🌐 언어: [English](../en/observation_logbook.md) | [日本語](../ja/observation_logbook.md) | [한국어](../ko/observation_logbook.md) | [ไทย](../th/observation_logbook.md)

# 천문 관측 로그북

안시 관측, 천체 촬영 또는 두 방식을 함께 사용한 세션을 기록합니다.

## 세션 정보

관측자, 장소, 시작 및 종료 시간, 좌표, 고도, 시상, 투명도, 운량, 장비와 전체 메모를 저장합니다.

## 대상 관측 기록

각 대상에 대해 다음을 저장합니다.

- 대상 키, 이름, 분류
- 시작 및 종료 시간
- 관측 결과
- 품질 평가
- 대상 고도
- 노출 시간과 프레임 수
- 관측 메모

## 요약

세션 시간, 관측 수, 가중 완료율, 평균 품질, 대상 관측 시간, 프레임 채택률과 채택 적분 노출을 계산합니다.

## 가져오기와 내보내기

- JSON 세션 저장 및 재가져오기
- 대상별 CSV 내보내기
- Markdown 관측 보고서

JSON은 완전한 재사용 세션 형식이며 CSV는 대상 관측 하나당 한 행을 포함합니다.

## 구현 파일

- `src/astroscope/observation_log.py`
- `src/astroscope/observation_report.py`
- `src/astroscope/observation_log_messages.py`
- `tests/test_observation_log.py`
- `tests/test_observation_report.py`
