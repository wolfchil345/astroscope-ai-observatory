🌐 言語: [English](../en/interactive_sky_map.md) | [日本語](../ja/interactive_sky_map.md) | [한국어](../ko/interactive_sky_map.md) | [ไทย](../th/interactive_sky_map.md)

# インタラクティブ現地星図

この星図は、観測者の地平線より上にある天体を表示します。

## 極座標星図の構造

- 中心は天頂を表します
- 外周は地平線を表します
- 方位角が角度方向の位置を決定します
- 天頂距離が中心からの距離を決定します

半径方向の座標は次の式で計算します。

`半径距離 = 90度 - 高度`

## 天体カテゴリー

- カタログ恒星とアンドロメダ銀河
- 太陽、月、惑星

## インタラクション

マーカーにカーソルを合わせると、次の情報を表示します。

- 天体名
- 高度
- 方位角
- 方角
- 可視性

## 実装ファイル

- `src/astroscope/sky_map.py`
- `src/astroscope/sky_map_messages.py`
- `tests/test_sky_map.py`
