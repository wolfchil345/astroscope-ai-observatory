🌐 언어: [English](../en/solar_system.md) | [日本語](../ja/solar_system.md) | [한국어](../ko/solar_system.md) | [ไทย](../th/solar_system.md)

# 태양계 탐색기

이 모듈은 선택한 관측 위치와 시간에서 태양계 천체의 겉보기 위치를 계산합니다.

## 지원 천체

- 태양
- 달
- 수성
- 금성
- 화성
- 목성
- 토성
- 천왕성
- 해왕성

## 계산 값

- 겉보기 적경과 적위
- 관측자로부터의 거리
- 고도와 방위각
- 방위
- 관측 가능성
- 태양과의 각거리
- 달과의 각거리
- 달의 근사 조명 비율

## 천체력

Mission 5에서는 Astropy 내장 천체력을 사용합니다. 외부 천체력 커널을 다운로드할 필요가 없습니다.

## 달의 조명 비율

달의 조명 비율은 태양과 달 사이의 겉보기 각거리로 추정합니다.

## 구현 파일

- `src/astroscope/solar_system.py`
- `src/astroscope/solar_system_messages.py`
- `tests/test_solar_system.py`
