🌐 언어: [English](../en/astrophotography_planner.md) | [日本語](../ja/astrophotography_planner.md) | [한국어](../ko/astrophotography_planner.md) | [ไทย](../th/astrophotography_planner.md)

# 천체사진 센서 및 모자이크 플래너

망원경과 카메라 조합을 천체 촬영용으로 평가합니다.

## 계산 항목

- 유효 초점거리와 초점비
- 센서 크기
- 픽셀당 이미지 스케일
- 가로, 세로 및 대각선 하늘 시야
- 시상 원반 샘플링
- 도스 한계 샘플링
- 권장 이미지 스케일 범위

## 샘플링 평가

선택한 대기 시상을 기준으로 평가합니다.

- 오버샘플링
- 적절한 샘플링
- 언더샘플링
- 심한 언더샘플링

## 대상 프레이밍

달, 안드로메다 은하, 플레이아데스 성단, 오리온 성운, 장미 성운, 석호 성운을 비교할 수 있습니다.

프레임 점유율, 가로 및 세로 패널 수, 전체 패널 수와 촬영 범위를 계산합니다.

## 회전

센서 회전은 시각화에 반영됩니다. 모자이크 패널 수는 현재 회전 전의 가로 및 세로 시야 크기로 계산합니다.

## 제한

대상 크기는 근사값입니다. 실제 프레이밍은 카메라 각도, 광학 왜곡, 크롭, 가이딩, 디더링, 스태킹과 희미한 외곽 영역에 따라 달라집니다.

## 구현 파일

- `src/astroscope/imaging.py`
- `src/astroscope/imaging_visuals.py`
- `src/astroscope/imaging_messages.py`
- `tests/test_imaging.py`
- `tests/test_imaging_visuals.py`
