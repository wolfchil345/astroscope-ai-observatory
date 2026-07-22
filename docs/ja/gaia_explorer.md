🌐 言語: [English](../en/gaia_explorer.md) | [日本語](../ja/gaia_explorer.md) | [한국어](../ko/gaia_explorer.md) | [ไทย](../th/gaia_explorer.md)

# Gaia DR3恒星カタログ探索

ICRS空座標を中心として、公開Gaia DR3カタログの円錐検索を行います。

## 検索条件

- 赤経と赤緯
- 検索半径
- 最大取得行数
- G等級上限
- 任意の年周視差S/Nフィルター
- 通信タイムアウト

## 可視化

### 局所星図

検索中心からの座標差を表示します。マーカーサイズはG等級、色は取得可能な場合BP−RPに基づきます。

### 色等級図

BP−RPと推定絶対G等級を表示します。明るい天体が上になるように等級軸を反転します。

### 固有運動ベクトル

赤経方向と赤緯方向の固有運動をベクトルとして表示します。

## 距離に関する注意

単純距離は正の年周視差を直接逆数化した教育目的の概算です。科学的に頑健な距離推定ではありません。

## エクスポート

検索結果をCSVで保存でき、生成されたADQLクエリも確認できます。

## 帰属

カタログデータ: ESA/Gaia/DPAC。

## 実装ファイル

- `src/astroscope/gaia_catalog.py`
- `src/astroscope/gaia_export.py`
- `src/astroscope/gaia_visuals.py`
- `src/astroscope/gaia_dashboard.py`
- `src/astroscope/gaia_messages.py`
- `tests/test_gaia_catalog.py`
- `tests/test_gaia_visuals.py`
