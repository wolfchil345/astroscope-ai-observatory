🌐 언어: [English](../en/gaia_explorer.md) | [日本語](../ja/gaia_explorer.md) | [한국어](../ko/gaia_explorer.md) | [ไทย](../th/gaia_explorer.md)

# Gaia DR3 항성 카탈로그 탐색기

ICRS 하늘 좌표를 중심으로 공개 Gaia DR3 카탈로그의 원뿔 검색을 실행합니다.

## 검색 조건

- 적경과 적위
- 검색 반경
- 최대 반환 행 수
- G등급 제한
- 선택적 시차 S/N 필터
- 네트워크 제한 시간

## 시각화

### 국부 하늘 지도

검색 중심으로부터의 좌표 차이를 표시합니다. 마커 크기는 G등급, 색은 가능한 경우 BP−RP를 사용합니다.

### 색–등급도

BP−RP와 추정 절대 G등급을 표시합니다. 밝은 값이 위에 나타나도록 등급 축을 반전합니다.

### 고유운동 벡터

적경과 적위 방향 고유운동을 벡터로 표시합니다.

## 거리 주의사항

단순 거리는 양의 시차를 직접 역산한 교육용 추정값이며 과학적으로 강건한 거리 추론이 아닙니다.

## 내보내기

검색 결과를 CSV로 저장하고 생성된 ADQL 쿼리를 확인할 수 있습니다.

## 출처

카탈로그 데이터: ESA/Gaia/DPAC.

## 구현 파일

- `src/astroscope/gaia_catalog.py`
- `src/astroscope/gaia_export.py`
- `src/astroscope/gaia_visuals.py`
- `src/astroscope/gaia_dashboard.py`
- `src/astroscope/gaia_messages.py`
- `tests/test_gaia_catalog.py`
- `tests/test_gaia_visuals.py`
