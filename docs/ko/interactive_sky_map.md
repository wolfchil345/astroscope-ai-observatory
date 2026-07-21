🌐 언어: [English](../en/interactive_sky_map.md) | [日本語](../ja/interactive_sky_map.md) | [한국어](../ko/interactive_sky_map.md) | [ไทย](../th/interactive_sky_map.md)

# 인터랙티브 현지 하늘 지도

이 하늘 지도는 관측자의 지평선 위에 있는 천체를 표시합니다.

## 극좌표 지도 구조

- 중심은 천정을 나타냅니다
- 바깥 원은 지평선을 나타냅니다
- 방위각은 각도 방향의 위치를 결정합니다
- 천정 거리는 중심으로부터의 거리를 결정합니다

반지름 좌표는 다음과 같이 계산합니다.

`반지름 거리 = 90도 - 고도`

## 천체 카테고리

- 카탈로그 별과 안드로메다 은하
- 태양, 달, 행성

## 상호작용

마커 위에 마우스를 올리면 다음 정보가 표시됩니다.

- 천체 이름
- 고도
- 방위각
- 방향
- 가시성 상태

## 구현 파일

- `src/astroscope/sky_map.py`
- `src/astroscope/sky_map_messages.py`
- `tests/test_sky_map.py`
