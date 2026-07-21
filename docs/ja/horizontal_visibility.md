🌐 言語: [English](../en/horizontal_visibility.md) | [日本語](../ja/horizontal_visibility.md) | [한국어](../ko/horizontal_visibility.md) | [ไทย](../th/horizontal_visibility.md)

# 地平座標と可視性

このモジュールは、ICRSの赤経と赤緯を観測地点の地平座標へ変換します。

## 高度

高度は、天体が地平線より上または下にある角度を示します。

- 地平線：0度
- 天頂：90度
- 地平線より下：負の高度

## 方位角

方位角は北から東向きに測定します。

- 北：0度
- 東：90度
- 南：180度
- 西：270度

## 可視性の分類

天体は次の状態に分類されます。

- 観測可能
- 地平線より上だが低高度
- 地平線より下

最低観測高度はユーザーが設定できます。

## エアマス

高度が5度以上の場合のみ、簡易的な近似エアマスを表示します。

## 大気差

Mission 4では、大気差補正を無効にした幾何学的地平座標を使用します。

## 実装ファイル

- `src/astroscope/visibility.py`
- `src/astroscope/visibility_messages.py`
- `tests/test_visibility.py`
