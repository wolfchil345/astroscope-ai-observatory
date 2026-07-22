🌐 언어: [English](../en/telescope_simulator.md) | [日本語](../ja/telescope_simulator.md) | [한국어](../ko/telescope_simulator.md) | [ไทย](../th/telescope_simulator.md)

# 망원경 및 접안렌즈 시뮬레이터

망원경, 접안렌즈, 바로우 렌즈, 포컬 리듀서 조합을 계산합니다.

## 계산 항목

- 기본 및 유효 초점비
- 유효 초점거리
- 배율
- 사출동공
- 근사 실제 시야
- 도스 한계
- 레일리 한계
- 근사 유효 배율 범위

## 접안렌즈 비교

선택한 망원경과 광학 액세서리를 사용하여 내장 접안렌즈를 비교할 수 있습니다.

## 시야 시각화

망원경의 원형 시야와 다음 대상의 근사 각크기를 비교합니다.

- 달
- 안드로메다 은하
- 플레이아데스 성단
- 오리온 성운

각크기는 교육 목적의 근사값입니다. 광공해가 심하면 희미한 외곽 부분이 보이지 않아 대상이 더 작게 보일 수 있습니다.

## 안전

올바르게 장착된 인증 전면 태양 필터 없이 망원경으로 태양을 관측하지 마세요.

## 제한

실제 성능에는 대기 시상, 광학 품질, 광축 정렬, 대상 밝기, 관측자의 시력, 기계적 안정성도 영향을 줍니다.

## 구현 파일

- `src/astroscope/telescope.py`
- `src/astroscope/telescope_visuals.py`
- `src/astroscope/telescope_messages.py`
- `tests/test_telescope.py`
- `tests/test_telescope_visuals.py`
