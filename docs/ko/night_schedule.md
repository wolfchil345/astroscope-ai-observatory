🌐 언어: [English](../en/night_schedule.md) | [日本語](../ja/night_schedule.md) | [한국어](../ko/night_schedule.md) | [ไทย](../th/night_schedule.md)

# 야간 타임라인과 관측 일정

이 모듈은 선택한 밤 동안 관측 대상을 반복적으로 평가합니다.

## 타임라인

사용자는 다음 조건을 선택합니다.

- 시작 시간
- 종료 시간
- 계산 간격
- 최소 고도
- 달과의 최소 각거리
- 최소 추천 점수

종료 시간은 다음 날이 될 수 있습니다.

## 일정 생성

각 시간대에서 최고 순위의 추천 대상을 선택합니다. 같은 대상이 연속으로 선택되면 하나의 관측 블록으로 합칩니다.

## 타임라인 차트

인터랙티브 차트는 각 대상의 점수가 밤 동안 어떻게 변화하는지 보여 줍니다.

## 제한

현재 일정에는 망원경 준비 시간, 이동 시간, 구름, 날씨, 노출 시간이 포함되지 않습니다.

## 구현 파일

- `src/astroscope/schedule.py`
- `src/astroscope/schedule_messages.py`
- `tests/test_schedule.py`
