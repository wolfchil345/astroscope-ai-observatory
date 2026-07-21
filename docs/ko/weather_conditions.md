🌐 언어: [English](../en/weather_conditions.md) | [日本語](../ja/weather_conditions.md) | [한국어](../ko/weather_conditions.md) | [ไทย](../th/weather_conditions.md)

# 날씨를 반영한 관측 조건

이 모듈은 시간별 날씨 예보를 불러와 천문 관측에 적합한 조건인지 평가합니다.

## 예보 항목

- 기온
- 상대 습도
- 이슬점
- 강수 확률
- 강수량
- 운량
- 가시거리
- 풍속
- 돌풍

## 날씨 점수

설명 가능한 점수 구성은 다음과 같습니다.

- 운량: 40점
- 강수 확률: 25점
- 가시거리: 15점
- 습도: 10점
- 풍속: 10점

비 또는 위험한 돌풍이 있으면 최고 점수가 제한됩니다.

## 이슬 위험

상대 습도와 기온 및 이슬점 차이로 이슬과 응결 위험을 추정합니다.

- 낮음
- 보통
- 높음
- 매우 높음

## 예보 제한

이 기능은 가까운 날짜의 수치예보를 사용합니다. 실제 하늘 상태를 보장하지 않으며 천문 시상이나 대기 투명도를 직접 측정하지 않습니다.

## 데이터 출처

날씨 데이터는 CC BY 4.0의 Open-Meteo에서 제공됩니다. AstroScope는 관측 점수, 평가 및 이슬 위험을 계산하여 데이터를 변환합니다.

## 구현 파일

- `src/astroscope/weather.py`
- `src/astroscope/weather_charts.py`
- `src/astroscope/weather_messages.py`
- `tests/test_weather.py`
- `tests/test_weather_charts.py`
