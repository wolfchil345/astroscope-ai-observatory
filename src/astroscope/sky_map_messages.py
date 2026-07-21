"""Four-language interface text for the interactive sky map."""

from typing import Final

SKY_MAP_TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "sky_map_section": {
        "en": "Interactive local sky map",
        "ja": "インタラクティブ現地星図",
        "ko": "인터랙티브 현지 하늘 지도",
        "th": "แผนที่ท้องฟ้าท้องถิ่นแบบโต้ตอบ",
    },
    "sky_map_explanation": {
        "en": (
            "Display catalogue objects and Solar System bodies "
            "that are currently above the observer's horizon."
        ),
        "ja": ("観測者の地平線より上にあるカタログ天体と太陽系天体を表示します。"),
        "ko": ("관측자의 지평선 위에 있는 카탈로그 천체와 태양계 천체를 표시합니다."),
        "th": ("แสดงวัตถุจากแค็ตตาล็อกและวัตถุในระบบสุริยะที่อยู่เหนือขอบฟ้าของผู้สังเกตการณ์"),
    },
    "include_catalog_objects": {
        "en": "Include catalogue objects",
        "ja": "カタログ天体を含める",
        "ko": "카탈로그 천체 포함",
        "th": "รวมวัตถุจากแค็ตตาล็อก",
    },
    "include_solar_system_objects": {
        "en": "Include Solar System objects",
        "ja": "太陽系天体を含める",
        "ko": "태양계 천체 포함",
        "th": "รวมวัตถุในระบบสุริยะ",
    },
    "generate_sky_map": {
        "en": "Generate interactive sky map",
        "ja": "インタラクティブ星図を生成",
        "ko": "인터랙티브 하늘 지도 생성",
        "th": "สร้างแผนที่ท้องฟ้าแบบโต้ตอบ",
    },
    "sky_map_title": {
        "en": "Local sky above the horizon",
        "ja": "地平線より上の現地星空",
        "ko": "지평선 위의 현지 하늘",
        "th": "ท้องฟ้าท้องถิ่นเหนือขอบฟ้า",
    },
    "catalog_trace": {
        "en": "Catalogue objects",
        "ja": "カタログ天体",
        "ko": "카탈로그 천체",
        "th": "วัตถุจากแค็ตตาล็อก",
    },
    "solar_system_trace": {
        "en": "Solar System objects",
        "ja": "太陽系天体",
        "ko": "태양계 천체",
        "th": "วัตถุในระบบสุริยะ",
    },
    "visible_object_count": {
        "en": "Objects above the horizon",
        "ja": "地平線より上の天体数",
        "ko": "지평선 위 천체 수",
        "th": "จำนวนวัตถุเหนือขอบฟ้า",
    },
    "below_horizon_count": {
        "en": "Objects below the horizon",
        "ja": "地平線より下の天体数",
        "ko": "지평선 아래 천체 수",
        "th": "จำนวนวัตถุใต้ขอบฟ้า",
    },
    "sky_map_altitude": {
        "en": "Altitude",
        "ja": "高度",
        "ko": "고도",
        "th": "มุมเงย",
    },
    "sky_map_azimuth": {
        "en": "Azimuth",
        "ja": "方位角",
        "ko": "방위각",
        "th": "มุมทิศ",
    },
    "sky_map_direction": {
        "en": "Direction",
        "ja": "方角",
        "ko": "방향",
        "th": "ทิศทาง",
    },
    "sky_map_status": {
        "en": "Visibility status",
        "ja": "可視性",
        "ko": "가시성 상태",
        "th": "สถานะการมองเห็น",
    },
    "sky_map_zenith": {
        "en": "Zenith",
        "ja": "天頂",
        "ko": "천정",
        "th": "จุดเหนือศีรษะ",
    },
    "sky_map_horizon": {
        "en": "Horizon",
        "ja": "地平線",
        "ko": "지평선",
        "th": "ขอบฟ้า",
    },
    "no_sky_map_category": {
        "en": "Select at least one object category.",
        "ja": "少なくとも1つの天体カテゴリーを選択してください。",
        "ko": "천체 카테고리를 하나 이상 선택하세요.",
        "th": "เลือกประเภทวัตถุอย่างน้อยหนึ่งประเภท",
    },
    "no_visible_sky_objects": {
        "en": "No selected objects are currently above the horizon.",
        "ja": "選択した天体は現在すべて地平線より下にあります。",
        "ko": "선택한 천체가 현재 모두 지평선 아래에 있습니다.",
        "th": "ขณะนี้ไม่มีวัตถุที่เลือกอยู่เหนือขอบฟ้า",
    },
    "sky_map_note": {
        "en": (
            "The centre represents the zenith. The outer circle "
            "represents the horizon. Hover over an object for details."
        ),
        "ja": ("中心は天頂、外周は地平線を表します。天体にカーソルを合わせると詳細を表示します。"),
        "ko": (
            "중심은 천정을, 바깥 원은 지평선을 나타냅니다. "
            "천체 위에 마우스를 올리면 세부 정보가 표시됩니다."
        ),
        "th": ("จุดศูนย์กลางแทนจุดเหนือศีรษะ วงกลมด้านนอกแทนขอบฟ้า เลื่อนเมาส์เหนือวัตถุเพื่อดูรายละเอียด"),
    },
    "sky_map_error": {
        "en": "Sky-map calculation error",
        "ja": "星図計算エラー",
        "ko": "하늘 지도 계산 오류",
        "th": "ข้อผิดพลาดในการคำนวณแผนที่ท้องฟ้า",
    },
}
