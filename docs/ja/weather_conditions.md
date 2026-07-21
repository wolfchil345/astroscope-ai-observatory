🌐 言語: [English](../en/weather_conditions.md) | [日本語](../ja/weather_conditions.md) | [한국어](../ko/weather_conditions.md) | [ไทย](../th/weather_conditions.md)

# 天気を考慮した観測条件

このモジュールは時間別天気予報を取得し、天体観測に適した条件かどうかを評価します。

## 予報項目

- 気温
- 相対湿度
- 露点
- 降水確率
- 降水量
- 雲量
- 視程
- 風速
- 最大瞬間風速

## 天気スコア

説明可能なスコアは次の構成です。

- 雲量：40点
- 降水確率：25点
- 視程：15点
- 湿度：10点
- 風速：10点

雨や危険な突風がある場合、最高スコアを制限します。

## 結露リスク

相対湿度と気温・露点の差から結露リスクを推定します。

- 低い
- 中程度
- 高い
- 非常に高い

## 予報の制限

この機能は近日の数値予報を利用します。実際の空の状態を保証せず、天文シーイングや透明度を直接測定するものではありません。

## データ出典

天気データはCC BY 4.0のOpen-Meteoから提供されます。AstroScopeは観測スコア、評価、結露リスクを計算してデータを加工します。

## 実装ファイル

- `src/astroscope/weather.py`
- `src/astroscope/weather_charts.py`
- `src/astroscope/weather_messages.py`
- `tests/test_weather.py`
- `tests/test_weather_charts.py`
