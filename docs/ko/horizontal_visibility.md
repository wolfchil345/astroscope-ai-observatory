🌐 언어: [English](../en/horizontal_visibility.md) | [日本語](../ja/horizontal_visibility.md) | [한국어](../ko/horizontal_visibility.md) | [ไทย](../th/horizontal_visibility.md)

# 지평 좌표와 가시성

이 모듈은 ICRS 적경과 적위를 관측자의 현지 지평 좌표로 변환합니다.

## 고도

고도는 천체가 지평선 위나 아래에 있는 각도를 나타냅니다.

- 지평선: 0도
- 천정: 90도
- 지평선 아래: 음의 고도

## 방위각

방위각은 북쪽에서 동쪽 방향으로 측정합니다.

- 북쪽: 0도
- 동쪽: 90도
- 남쪽: 180도
- 서쪽: 270도

## 가시성 분류

천체는 다음 상태로 분류됩니다.

- 관측 가능
- 지평선 위이지만 저고도
- 지평선 아래

사용자는 최소 관측 고도를 선택할 수 있습니다.

## 대기질량

고도가 5도 이상인 경우에만 간단한 근사 대기질량을 표시합니다.

## 대기 굴절

Mission 4에서는 대기 굴절을 비활성화한 기하학적 지평 좌표를 사용합니다.

## 구현 파일

- `src/astroscope/visibility.py`
- `src/astroscope/visibility_messages.py`
- `tests/test_visibility.py`
