"""Four-language interface text for the Solar System explorer."""

from typing import Final

SOLAR_SYSTEM_TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "solar_system_section": {
        "en": "Solar System explorer",
        "ja": "太陽系エクスプローラー",
        "ko": "태양계 탐색기",
        "th": "เครื่องมือสำรวจระบบสุริยะ",
    },
    "solar_system_explanation": {
        "en": (
            "Calculate the apparent position of the Sun, Moon, "
            "or a planet for the selected observer and time."
        ),
        "ja": ("選択した観測地点と時刻から、太陽、月、惑星の見かけの位置を計算します。"),
        "ko": ("선택한 관측 위치와 시간을 기준으로 태양, 달, 행성의 겉보기 위치를 계산합니다."),
        "th": ("คำนวณตำแหน่งปรากฏของดวงอาทิตย์ ดวงจันทร์ หรือดาวเคราะห์ตามสถานที่และเวลาที่เลือก"),
    },
    "solar_system_body": {
        "en": "Solar System body",
        "ja": "太陽系天体",
        "ko": "태양계 천체",
        "th": "วัตถุในระบบสุริยะ",
    },
    "body_sun": {
        "en": "Sun",
        "ja": "太陽",
        "ko": "태양",
        "th": "ดวงอาทิตย์",
    },
    "body_moon": {
        "en": "Moon",
        "ja": "月",
        "ko": "달",
        "th": "ดวงจันทร์",
    },
    "body_mercury": {
        "en": "Mercury",
        "ja": "水星",
        "ko": "수성",
        "th": "ดาวพุธ",
    },
    "body_venus": {
        "en": "Venus",
        "ja": "金星",
        "ko": "금성",
        "th": "ดาวศุกร์",
    },
    "body_mars": {
        "en": "Mars",
        "ja": "火星",
        "ko": "화성",
        "th": "ดาวอังคาร",
    },
    "body_jupiter": {
        "en": "Jupiter",
        "ja": "木星",
        "ko": "목성",
        "th": "ดาวพฤหัสบดี",
    },
    "body_saturn": {
        "en": "Saturn",
        "ja": "土星",
        "ko": "토성",
        "th": "ดาวเสาร์",
    },
    "body_uranus": {
        "en": "Uranus",
        "ja": "天王星",
        "ko": "천왕성",
        "th": "ดาวยูเรนัส",
    },
    "body_neptune": {
        "en": "Neptune",
        "ja": "海王星",
        "ko": "해왕성",
        "th": "ดาวเนปจูน",
    },
    "calculate_solar_system": {
        "en": "Calculate Solar System position",
        "ja": "太陽系天体の位置を計算",
        "ko": "태양계 천체 위치 계산",
        "th": "คำนวณตำแหน่งวัตถุในระบบสุริยะ",
    },
    "solar_system_results": {
        "en": "Apparent-position results",
        "ja": "見かけの位置の計算結果",
        "ko": "겉보기 위치 계산 결과",
        "th": "ผลการคำนวณตำแหน่งปรากฏ",
    },
    "apparent_ra": {
        "en": "Apparent right ascension",
        "ja": "見かけの赤経",
        "ko": "겉보기 적경",
        "th": "ไรต์แอสเซนชันปรากฏ",
    },
    "apparent_dec": {
        "en": "Apparent declination",
        "ja": "見かけの赤緯",
        "ko": "겉보기 적위",
        "th": "เดคลิเนชันปรากฏ",
    },
    "distance_au": {
        "en": "Observer distance (AU)",
        "ja": "観測者からの距離（AU）",
        "ko": "관측자 거리 (AU)",
        "th": "ระยะจากผู้สังเกตการณ์ (AU)",
    },
    "distance_km": {
        "en": "Observer distance (km)",
        "ja": "観測者からの距離（km）",
        "ko": "관측자 거리 (km)",
        "th": "ระยะจากผู้สังเกตการณ์ (กม.)",
    },
    "solar_elongation": {
        "en": "Separation from the Sun",
        "ja": "太陽からの角距離",
        "ko": "태양과의 각거리",
        "th": "ระยะเชิงมุมจากดวงอาทิตย์",
    },
    "moon_separation": {
        "en": "Separation from the Moon",
        "ja": "月からの角距離",
        "ko": "달과의 각거리",
        "th": "ระยะเชิงมุมจากดวงจันทร์",
    },
    "moon_illumination": {
        "en": "Approximate Moon illumination",
        "ja": "月の概算照明率",
        "ko": "달의 근사 조명 비율",
        "th": "สัดส่วนความสว่างโดยประมาณของดวงจันทร์",
    },
    "ephemeris": {
        "en": "Ephemeris",
        "ja": "天体暦",
        "ko": "천체력",
        "th": "เอเฟเมอริส",
    },
    "builtin_ephemeris": {
        "en": "Astropy built-in ephemeris",
        "ja": "Astropy内蔵天体暦",
        "ko": "Astropy 내장 천체력",
        "th": "เอเฟเมอริสในตัวของ Astropy",
    },
    "solar_system_note": {
        "en": (
            "Positions are apparent topocentric results calculated "
            "with Astropy's built-in ephemeris. Atmospheric "
            "refraction is disabled."
        ),
        "ja": ("Astropy内蔵天体暦を使用した見かけの地心差補正済み位置です。大気差補正は無効です。"),
        "ko": (
            "Astropy 내장 천체력으로 계산한 겉보기 관측지 중심 "
            "위치입니다. 대기 굴절은 비활성화되어 있습니다."
        ),
        "th": (
            "ตำแหน่งนี้เป็นตำแหน่งปรากฏแบบอ้างอิงผู้สังเกตการณ์ "
            "คำนวณด้วยเอเฟเมอริสในตัวของ Astropy "
            "และปิดการหักเหของบรรยากาศ"
        ),
    },
    "solar_system_error": {
        "en": "Solar System calculation error",
        "ja": "太陽系計算エラー",
        "ko": "태양계 계산 오류",
        "th": "ข้อผิดพลาดในการคำนวณระบบสุริยะ",
    },
}
