🌐 언어: [English](../en/observation_planner.md) | [日本語](../ja/observation_planner.md) | [한국어](../ko/observation_planner.md) | [ไทย](../th/observation_planner.md)

# 스마트 관측 플래너

이 플래너는 설명 가능한 100점 기준으로 밤하늘 관측 대상을 순위화합니다.

## 점수 구성

- 고도: 45점
- 대기질량: 20점
- 달과의 각거리: 20점
- 하늘의 어두움: 15점

## 추천 조건

다음 조건을 만족하는 대상을 추천합니다.

- 선택한 최소 고도보다 높음
- 관측 가능 상태
- 달과의 최소 각거리 충족
- 최소 총점 충족

달 자체는 달과의 각거리가 0도여도 감점되지 않습니다.

## 중요한 제한

현재 순위에는 구름, 대기 투명도, 시상, 등급, 망원경 성능이 포함되지 않습니다.

## 구현 파일

- `src/astroscope/planner.py`
- `src/astroscope/planner_messages.py`
- `tests/test_planner.py`
