[English](README.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [ไทย](README.th.md)

# AstroScope AI 천문대 🔭

지능형 관측 계획 시스템과 인터랙티브 플라네타륨입니다.

## 지원 언어

- 영어
- 일본어
- 한국어
- 태국어

## 구현된 기능

- 천체사진 센서 및 모자이크 플래너
- 이미지 스케일 및 시상 샘플링 분석
- 회전 센서 프레임과 모자이크 시각화

- 망원경 및 접안렌즈 시뮬레이터
- 바로우와 포컬 리듀서 계산
- 인터랙티브 각시야 시각화

- 날씨를 반영한 관측 조건
- 시간별 구름, 비, 바람, 가시거리 예보
- 관측 날씨 점수와 이슬 위험 경고

- 밤 전체 관측 타임라인
- 시간순 관측 대상 자동 일정
- 점수 변화 인터랙티브 차트

- 스마트 관측 대상 순위
- 설명 가능한 100점 평가
- 달 각거리와 하늘 어두움 필터

- 인터랙티브 현지 전천 극좌표 지도
- 카탈로그 및 태양계 천체 레이어
- 다국어 호버 정보

- 태양계 천체의 겉보기 위치 계산
- 태양, 달, 8개 행성 탐색기
- 태양 이각과 달 조명 비율

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

- [천체사진 센서 및 모자이크 플래너](docs/ko/astrophotography_planner.md)

- [망원경 및 접안렌즈 시뮬레이터](docs/ko/telescope_simulator.md)

- [날씨를 반영한 관측 조건](docs/ko/weather_conditions.md)

- [야간 타임라인과 관측 일정](docs/ko/night_schedule.md)

- [스마트 관측 플래너](docs/ko/observation_planner.md)

- [인터랙티브 현지 하늘 지도](docs/ko/interactive_sky_map.md)

- [태양계 탐색기](docs/ko/solar_system.md)

- [한국어 문서](docs/ko/index.md)
- [관측 위치와 천문 시간](docs/ko/observer_time.md)
- [적도 좌표](docs/ko/equatorial_coordinates.md)
- [지평 좌표와 가시성](docs/ko/horizontal_visibility.md)
