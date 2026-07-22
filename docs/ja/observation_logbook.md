🌐 言語: [English](../en/observation_logbook.md) | [日本語](../ja/observation_logbook.md) | [한국어](../ko/observation_logbook.md) | [ไทย](../th/observation_logbook.md)

# 天体観測ログブック

眼視観測、天体撮影、または両方を含む観測セッションを記録します。

## セッション情報

観測者、場所、開始・終了時刻、座標、標高、シーイング、透明度、雲量、使用機材、全体メモを保存します。

## 天体観測記録

各天体について次の情報を保存します。

- 天体キー、名称、分類
- 開始・終了時刻
- 観測結果
- 品質評価
- 天体高度
- 露光時間とフレーム数
- 観測メモ

## 集計

セッション時間、観測天体数、加重完了率、平均品質、観測合計時間、フレーム採用率、採用積算露光時間を計算します。

## インポートとエクスポート

- JSONセッションの保存と再読み込み
- 天体ごとのCSV出力
- Markdown観測レポート

JSONは再利用可能な完全セッション形式です。CSVは天体観測ごとに1行を出力します。

## 実装ファイル

- `src/astroscope/observation_log.py`
- `src/astroscope/observation_report.py`
- `src/astroscope/observation_log_messages.py`
- `tests/test_observation_log.py`
- `tests/test_observation_report.py`
