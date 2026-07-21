🌐 言語: [English](../en/solar_system.md) | [日本語](../ja/solar_system.md) | [한국어](../ko/solar_system.md) | [ไทย](../th/solar_system.md)

# 太陽系エクスプローラー

このモジュールは、選択した観測地点と観測時刻における太陽系天体の見かけの位置を計算します。

## 対応天体

- 太陽
- 月
- 水星
- 金星
- 火星
- 木星
- 土星
- 天王星
- 海王星

## 計算する値

- 見かけの赤経と赤緯
- 観測者からの距離
- 高度と方位角
- 方角
- 観測可能性
- 太陽からの角距離
- 月からの角距離
- 月の概算照明率

## 天体暦

Mission 5ではAstropy内蔵天体暦を使用します。外部の天体暦カーネルをダウンロードする必要はありません。

## 月の照明率

月の照明率は、太陽と月の見かけの角距離から概算します。

## 実装ファイル

- `src/astroscope/solar_system.py`
- `src/astroscope/solar_system_messages.py`
- `tests/test_solar_system.py`
