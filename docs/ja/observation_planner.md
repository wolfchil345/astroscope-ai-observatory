🌐 言語: [English](../en/observation_planner.md) | [日本語](../ja/observation_planner.md) | [한국어](../ko/observation_planner.md) | [ไทย](../th/observation_planner.md)

# スマート観測プランナー

このプランナーは、説明可能な100点満点の評価方法で夜空の天体を順位付けします。

## スコア構成

- 高度：45点
- エアマス：20点
- 月からの角距離：20点
- 空の暗さ：15点

## 推奨条件

次の条件を満たす天体を推奨します。

- 設定した最低高度より上にある
- 観測可能と判定される
- 月からの最低角距離を満たす
- 最低総合スコアを満たす

月そのものは、月からの角距離が0度でも減点されません。

## 重要な制限

現在の順位には、雲、大気透明度、シーイング、等級、望遠鏡性能は含まれていません。

## 実装ファイル

- `src/astroscope/planner.py`
- `src/astroscope/planner_messages.py`
- `tests/test_planner.py`
