[English](README.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [ไทย](README.th.md)

# AstroScope AI 천문대 🔭

지능형 관측 계획 시스템과 인터랙티브 플라네타륨입니다.

## 지원 언어

- 영어
- 일본어
- 한국어
- 태국어

## 구현된 기능

- 4개 언어 Streamlit 인터페이스
- 관측 위치의 위도, 경도 및 고도
- 시간대 변환
- UTC 날짜와 시간
- 율리우스일과 수정 율리우스일
- 지방 겉보기 항성시
- ICRS 적경과 적위
- 은하 좌표 변환
- 직교 천구 방향 벡터
- 현지 고도와 방위각
- 지평선 및 관측 가능성 분류
- 방향과 근사 대기질량

## 설치

`python -m pip install -e ".[dev]"`를 실행합니다.

## 실행

`make run`을 실행합니다.

## 테스트

`make checks`를 실행합니다.

## 문서

- [한국어 문서](docs/ko/index.md)
- [관측 위치와 천문 시간](docs/ko/observer_time.md)
- [적도 좌표](docs/ko/equatorial_coordinates.md)
- [지평 좌표와 가시성](docs/ko/horizontal_visibility.md)
