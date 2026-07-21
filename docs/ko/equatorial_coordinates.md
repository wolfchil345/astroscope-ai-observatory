🌐 언어: [English](../en/equatorial_coordinates.md) | [日本語](../ja/equatorial_coordinates.md) | [한국어](../ko/equatorial_coordinates.md) | [ไทย](../th/equatorial_coordinates.md)

# 적도 좌표

이 모듈은 ICRS 기준 좌표계의 적경과 적위를 사용하여 천체의 위치를 나타냅니다.

## 적경

적경은 천구의 경도에 해당하는 좌표입니다.

- 24시간은 360도
- 1시간은 15도
- 유효 범위는 0시간 이상 24시간 미만

## 적위

적위는 천구의 위도에 해당하는 좌표입니다.

- 양수는 북쪽 천구를 나타냅니다
- 음수는 남쪽 천구를 나타냅니다
- 유효 범위는 -90도부터 +90도까지입니다

## 좌표 변환

AstroScope는 ICRS 좌표를 다음 형식으로 변환합니다.

- 시분초 형식의 적경
- 도 단위 적경
- 도분초 형식의 적위
- 도 단위 적위
- 은경과 은위
- 직교 단위 방향 벡터

## 구현 파일

- `src/astroscope/coordinates.py`
- `src/astroscope/coordinate_messages.py`
- `tests/test_coordinates.py`
