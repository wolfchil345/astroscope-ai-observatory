"""Four-language interface text for celestial coordinates."""

from typing import Final

COORDINATE_TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "coordinate_section": {
        "en": "Equatorial coordinates",
        "ja": "赤道座標",
        "ko": "적도 좌표",
        "th": "พิกัดศูนย์สูตร",
    },
    "coordinate_explanation": {
        "en": (
            "Enter right ascension and declination. AstroScope "
            "will convert the ICRS position into several formats."
        ),
        "ja": ("赤経と赤緯を入力してください。AstroScopeがICRS座標を複数の形式へ変換します。"),
        "ko": ("적경과 적위를 입력하세요. AstroScope가 ICRS 위치를 여러 좌표 형식으로 변환합니다."),
        "th": ("ป้อนไรต์แอสเซนชันและเดคลิเนชัน AstroScope จะแปลงตำแหน่ง ICRS เป็นรูปแบบพิกัดต่าง ๆ"),
    },
    "celestial_object": {
        "en": "Celestial-object preset",
        "ja": "天体プリセット",
        "ko": "천체 프리셋",
        "th": "วัตถุท้องฟ้าที่ตั้งไว้ล่วงหน้า",
    },
    "object_sirius": {
        "en": "Sirius",
        "ja": "シリウス",
        "ko": "시리우스",
        "th": "ซิริอุส",
    },
    "object_betelgeuse": {
        "en": "Betelgeuse",
        "ja": "ベテルギウス",
        "ko": "베텔게우스",
        "th": "เบเทลจุส",
    },
    "object_vega": {
        "en": "Vega",
        "ja": "ベガ",
        "ko": "베가",
        "th": "เวกา",
    },
    "object_polaris": {
        "en": "Polaris",
        "ja": "ポラリス（北極星）",
        "ko": "폴라리스",
        "th": "ดาวเหนือ",
    },
    "object_m31": {
        "en": "Andromeda Galaxy (M31)",
        "ja": "アンドロメダ銀河（M31）",
        "ko": "안드로메다 은하 (M31)",
        "th": "กาแล็กซีแอนดรอเมดา (M31)",
    },
    "right_ascension_input": {
        "en": "Right ascension",
        "ja": "赤経",
        "ko": "적경",
        "th": "ไรต์แอสเซนชัน",
    },
    "declination_input": {
        "en": "Declination",
        "ja": "赤緯",
        "ko": "적위",
        "th": "เดคลิเนชัน",
    },
    "ra_help": {
        "en": "Example: 06h45m08.917s. Valid range: 0h to less than 24h.",
        "ja": "例：06h45m08.917s。有効範囲は0時以上24時未満です。",
        "ko": "예: 06h45m08.917s. 유효 범위는 0시 이상 24시 미만입니다.",
        "th": "ตัวอย่าง: 06h45m08.917s ช่วงที่ใช้ได้คือตั้งแต่ 0h ถึงน้อยกว่า 24h",
    },
    "dec_help": {
        "en": "Example: -16d42m58.017s. Valid range: -90° to +90°.",
        "ja": "例：-16d42m58.017s。有効範囲は-90度から+90度です。",
        "ko": "예: -16d42m58.017s. 유효 범위는 -90도부터 +90도입니다.",
        "th": "ตัวอย่าง: -16d42m58.017s ช่วงที่ใช้ได้คือ -90° ถึง +90°",
    },
    "convert_coordinates": {
        "en": "Convert coordinates",
        "ja": "座標を変換",
        "ko": "좌표 변환",
        "th": "แปลงพิกัด",
    },
    "coordinate_results": {
        "en": "Coordinate results",
        "ja": "座標変換結果",
        "ko": "좌표 변환 결과",
        "th": "ผลการแปลงพิกัด",
    },
    "right_ascension_hms": {
        "en": "Right ascension (H:M:S)",
        "ja": "赤経（時・分・秒）",
        "ko": "적경 (시·분·초)",
        "th": "ไรต์แอสเซนชัน (ชั่วโมง:นาที:วินาที)",
    },
    "right_ascension_degrees": {
        "en": "Right ascension (degrees)",
        "ja": "赤経（度）",
        "ko": "적경 (도)",
        "th": "ไรต์แอสเซนชัน (องศา)",
    },
    "declination_dms": {
        "en": "Declination (D:M:S)",
        "ja": "赤緯（度・分・秒）",
        "ko": "적위 (도·분·초)",
        "th": "เดคลิเนชัน (องศา:ลิปดา:ฟิลิปดา)",
    },
    "declination_degrees": {
        "en": "Declination (degrees)",
        "ja": "赤緯（度）",
        "ko": "적위 (도)",
        "th": "เดคลิเนชัน (องศา)",
    },
    "galactic_longitude": {
        "en": "Galactic longitude",
        "ja": "銀経",
        "ko": "은경",
        "th": "ลองจิจูดกาแล็กซี",
    },
    "galactic_latitude": {
        "en": "Galactic latitude",
        "ja": "銀緯",
        "ko": "은위",
        "th": "ละติจูดกาแล็กซี",
    },
    "cartesian_direction": {
        "en": "Cartesian unit direction vector",
        "ja": "デカルト単位方向ベクトル",
        "ko": "직교 단위 방향 벡터",
        "th": "เวกเตอร์ทิศทางหน่วยแบบคาร์ทีเซียน",
    },
    "coordinate_note": {
        "en": (
            "One hour of right ascension equals 15 degrees. "
            "Mission 4 will convert this position into altitude "
            "and azimuth for the selected observer."
        ),
        "ja": (
            "赤経1時間は15度です。Mission 4では、この座標を"
            "選択した観測者の高度と方位角へ変換します。"
        ),
        "ko": (
            "적경 1시간은 15도입니다. Mission 4에서는 이 위치를 "
            "선택한 관측자의 고도와 방위각으로 변환합니다."
        ),
        "th": (
            "ไรต์แอสเซนชัน 1 ชั่วโมงเท่ากับ 15 องศา Mission 4 จะแปลงตำแหน่งนี้เป็นมุมเงยและมุมทิศของผู้สังเกตการณ์"
        ),
    },
    "coordinate_error": {
        "en": "Coordinate error",
        "ja": "座標エラー",
        "ko": "좌표 오류",
        "th": "ข้อผิดพลาดของพิกัด",
    },
}
