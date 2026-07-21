[English](README.md) | [日本語](README.ja.md) | [한국어](README.ko.md) | [ไทย](README.th.md)

# AstroScope AI 天文台 🔭

インテリジェント観測計画システムとインタラクティブ・プラネタリウムです。

## 対応言語

- 英語
- 日本語
- 韓国語
- タイ語

## 実装済み機能

- 4言語対応Streamlitインターフェース
- 観測地点の緯度、経度、標高
- タイムゾーン変換
- UTC日時
- ユリウス日と修正ユリウス日
- 地方視恒星時
- ICRS赤経・赤緯
- 銀河座標への変換
- 天球方向のデカルトベクトル

## インストール

`python -m pip install -e ".[dev]"`を実行します。

## 起動

`make run`を実行します。

## テスト

`make checks`を実行します。

## ドキュメント

- [日本語ドキュメント](docs/ja/index.md)
- [観測地点と天文時刻](docs/ja/observer_time.md)
- [赤道座標](docs/ja/equatorial_coordinates.md)
