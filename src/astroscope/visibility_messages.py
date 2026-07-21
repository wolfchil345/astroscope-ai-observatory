"""Four-language interface text for target visibility."""

from typing import Final

VISIBILITY_TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "visibility_section": {
        "en": "Local sky position and visibility",
        "ja": "現地の天球位置と可視性",
        "ko": "현지 하늘 위치와 가시성",
        "th": "ตำแหน่งบนท้องฟ้าท้องถิ่นและการมองเห็น",
    },
    "visibility_explanation": {
        "en": (
            "Combine the selected observer, time, right ascension, "
            "and declination to calculate altitude and azimuth."
        ),
        "ja": ("選択した観測地点、時刻、赤経、赤緯を組み合わせ、高度と方位角を計算します。"),
        "ko": ("선택한 관측 위치, 시간, 적경, 적위를 결합하여 고도와 방위각을 계산합니다."),
        "th": ("รวมตำแหน่งผู้สังเกตการณ์ เวลา ไรต์แอสเซนชัน และเดคลิเนชันเพื่อคำนวณมุมเงยและมุมทิศ"),
    },
    "minimum_altitude": {
        "en": "Minimum observing altitude",
        "ja": "最低観測高度",
        "ko": "최소 관측 고도",
        "th": "มุมเงยต่ำสุดสำหรับการสังเกตการณ์",
    },
    "minimum_altitude_help": {
        "en": (
            "Targets below this altitude are classified as low. "
            "A common starting value is 20 degrees."
        ),
        "ja": ("この高度より低い天体は低高度と判定されます。初期値は20度です。"),
        "ko": ("이 고도보다 낮은 천체는 저고도로 분류됩니다. 기본값은 20도입니다."),
        "th": ("วัตถุที่ต่ำกว่ามุมนี้จะถูกจัดว่าอยู่ในระดับต่ำ ค่าเริ่มต้นคือ 20 องศา"),
    },
    "calculate_visibility": {
        "en": "Calculate local sky position",
        "ja": "現地の天球位置を計算",
        "ko": "현지 하늘 위치 계산",
        "th": "คำนวณตำแหน่งบนท้องฟ้าท้องถิ่น",
    },
    "horizontal_results": {
        "en": "Horizontal-coordinate results",
        "ja": "地平座標の計算結果",
        "ko": "지평 좌표 계산 결과",
        "th": "ผลการคำนวณพิกัดขอบฟ้า",
    },
    "altitude": {
        "en": "Altitude",
        "ja": "高度",
        "ko": "고도",
        "th": "มุมเงย",
    },
    "azimuth": {
        "en": "Azimuth",
        "ja": "方位角",
        "ko": "방위각",
        "th": "มุมทิศ",
    },
    "zenith_distance": {
        "en": "Zenith distance",
        "ja": "天頂距離",
        "ko": "천정 거리",
        "th": "ระยะจากจุดเหนือศีรษะ",
    },
    "airmass": {
        "en": "Approximate airmass",
        "ja": "近似エアマス",
        "ko": "근사 대기질량",
        "th": "มวลอากาศโดยประมาณ",
    },
    "cardinal_direction": {
        "en": "Direction",
        "ja": "方角",
        "ko": "방향",
        "th": "ทิศทาง",
    },
    "above_horizon": {
        "en": "Above the horizon",
        "ja": "地平線より上",
        "ko": "지평선 위",
        "th": "อยู่เหนือขอบฟ้า",
    },
    "value_yes": {
        "en": "Yes",
        "ja": "はい",
        "ko": "예",
        "th": "ใช่",
    },
    "value_no": {
        "en": "No",
        "ja": "いいえ",
        "ko": "아니요",
        "th": "ไม่",
    },
    "not_available": {
        "en": "Not available",
        "ja": "利用不可",
        "ko": "사용 불가",
        "th": "ไม่พร้อมใช้งาน",
    },
    "observation_status": {
        "en": "Observation status",
        "ja": "観測状態",
        "ko": "관측 상태",
        "th": "สถานะการสังเกตการณ์",
    },
    "status_observable": {
        "en": "Observable above the selected altitude",
        "ja": "設定した最低高度より上にあり、観測可能です",
        "ko": "선택한 최소 고도보다 높아 관측 가능합니다",
        "th": "สามารถสังเกตได้เหนือมุมเงยที่กำหนด",
    },
    "status_low_altitude": {
        "en": "Above the horizon, but at low altitude",
        "ja": "地平線より上ですが、低高度です",
        "ko": "지평선 위에 있지만 고도가 낮습니다",
        "th": "อยู่เหนือขอบฟ้า แต่มุมเงยยังต่ำ",
    },
    "status_below_horizon": {
        "en": "Below the horizon",
        "ja": "地平線より下にあります",
        "ko": "지평선 아래에 있습니다",
        "th": "อยู่ใต้ขอบฟ้า",
    },
    "direction_north": {
        "en": "North",
        "ja": "北",
        "ko": "북쪽",
        "th": "ทิศเหนือ",
    },
    "direction_northeast": {
        "en": "Northeast",
        "ja": "北東",
        "ko": "북동쪽",
        "th": "ทิศตะวันออกเฉียงเหนือ",
    },
    "direction_east": {
        "en": "East",
        "ja": "東",
        "ko": "동쪽",
        "th": "ทิศตะวันออก",
    },
    "direction_southeast": {
        "en": "Southeast",
        "ja": "南東",
        "ko": "남동쪽",
        "th": "ทิศตะวันออกเฉียงใต้",
    },
    "direction_south": {
        "en": "South",
        "ja": "南",
        "ko": "남쪽",
        "th": "ทิศใต้",
    },
    "direction_southwest": {
        "en": "Southwest",
        "ja": "南西",
        "ko": "남서쪽",
        "th": "ทิศตะวันตกเฉียงใต้",
    },
    "direction_west": {
        "en": "West",
        "ja": "西",
        "ko": "서쪽",
        "th": "ทิศตะวันตก",
    },
    "direction_northwest": {
        "en": "Northwest",
        "ja": "北西",
        "ko": "북서쪽",
        "th": "ทิศตะวันตกเฉียงเหนือ",
    },
    "visibility_note": {
        "en": (
            "Atmospheric refraction is disabled. Airmass is shown "
            "only when the altitude is at least 5 degrees."
        ),
        "ja": ("大気差補正は無効です。エアマスは高度5度以上の場合のみ表示します。"),
        "ko": (
            "대기 굴절 보정은 비활성화되어 있습니다. 대기질량은 고도가 5도 이상일 때만 표시됩니다."
        ),
        "th": ("ปิดการแก้ไขการหักเหของบรรยากาศ มวลอากาศจะแสดงเมื่อมุมเงยอย่างน้อย 5 องศา"),
    },
    "visibility_error": {
        "en": "Visibility calculation error",
        "ja": "可視性計算エラー",
        "ko": "가시성 계산 오류",
        "th": "ข้อผิดพลาดในการคำนวณการมองเห็น",
    },
}
