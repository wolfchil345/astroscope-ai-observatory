🌐 言語: [English](../en/telescope_simulator.md) | [日本語](../ja/telescope_simulator.md) | [한국어](../ko/telescope_simulator.md) | [ไทย](../th/telescope_simulator.md)

# 望遠鏡・接眼レンズシミュレーター

望遠鏡、接眼レンズ、バローレンズ、レデューサーの組み合わせを概算します。

## 計算項目

- 標準および有効F値
- 有効焦点距離
- 倍率
- 射出瞳径
- 概算実視界
- ドーズ限界
- レイリー限界
- 概算有効倍率範囲

## 接眼レンズ比較

選択した望遠鏡と光学アクセサリーを用いて、内蔵接眼レンズを比較できます。

## 視野シミュレーター

望遠鏡の円形視野と、次の天体の概算角サイズを比較します。

- 月
- アンドロメダ銀河
- プレアデス星団
- オリオン大星雲

角サイズは教育目的の概算です。光害が強い場所では淡い外縁部が見えず、実際より小さく見えることがあります。

## 安全

適切に装着された認証済み対物太陽フィルターなしで、望遠鏡を通して太陽を観察しないでください。

## 制限

実際の性能には、大気シーイング、光学品質、光軸調整、天体の明るさ、視力、機械的安定性も影響します。

## 実装ファイル

- `src/astroscope/telescope.py`
- `src/astroscope/telescope_visuals.py`
- `src/astroscope/telescope_messages.py`
- `tests/test_telescope.py`
- `tests/test_telescope_visuals.py`
