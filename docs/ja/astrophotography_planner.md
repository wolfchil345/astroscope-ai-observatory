🌐 言語: [English](../en/astrophotography_planner.md) | [日本語](../ja/astrophotography_planner.md) | [한국어](../ko/astrophotography_planner.md) | [ไทย](../th/astrophotography_planner.md)

# 天体撮影センサー・モザイクプランナー

望遠鏡とカメラの組み合わせを天体撮影向けに評価します。

## 計算項目

- 有効焦点距離とF値
- センサー寸法
- 1画素あたりの画像スケール
- 横、縦、対角の空視野
- シーイング像のサンプリング
- ドーズ限界のサンプリング
- 推奨画像スケール範囲

## サンプリング評価

選択した大気シーイングに対して評価します。

- オーバーサンプリング
- 適切
- アンダーサンプリング
- 大幅なアンダーサンプリング

## 天体フレーミング

月、アンドロメダ銀河、プレアデス星団、オリオン大星雲、ばら星雲、干潟星雲を比較できます。

画面占有率、横・縦方向のパネル数、総パネル数、撮影範囲を計算します。

## 回転

センサー回転は図に反映されます。モザイクパネル数は現在、回転前の横・縦視野寸法から計算します。

## 制限

天体サイズは概算です。実際のフレーミングはカメラ角度、光学歪み、クロップ、ガイド、ディザリング、スタッキング、淡い外縁部の見え方にも左右されます。

## 実装ファイル

- `src/astroscope/imaging.py`
- `src/astroscope/imaging_visuals.py`
- `src/astroscope/imaging_messages.py`
- `tests/test_imaging.py`
- `tests/test_imaging_visuals.py`
