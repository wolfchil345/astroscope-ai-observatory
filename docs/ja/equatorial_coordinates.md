🌐 言語: [English](../en/equatorial_coordinates.md) | [日本語](../ja/equatorial_coordinates.md) | [한국어](../ko/equatorial_coordinates.md) | [ไทย](../th/equatorial_coordinates.md)

# 赤道座標

このモジュールでは、ICRS基準座標系の赤経と赤緯を使用して天体の位置を表します。

## 赤経

赤経は、天球上の経度に相当する座標です。

- 24時間は360度
- 1時間は15度
- 有効範囲は0時間以上24時間未満

## 赤緯

赤緯は、天球上の緯度に相当する座標です。

- 正の値は北天を表す
- 負の値は南天を表す
- 有効範囲は-90度から+90度

## 座標変換

AstroScopeはICRS座標を次の形式へ変換します。

- 時分秒形式の赤経
- 度形式の赤経
- 度分秒形式の赤緯
- 度形式の赤緯
- 銀経と銀緯
- デカルト単位方向ベクトル

## 実装ファイル

- `src/astroscope/coordinates.py`
- `src/astroscope/coordinate_messages.py`
- `tests/test_coordinates.py`
