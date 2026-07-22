"""Internationalization utilities for AstroScope AI."""

from typing import Final

from astroscope.coordinate_messages import COORDINATE_TRANSLATIONS
from astroscope.exoplanet_messages import EXOPLANET_TRANSLATIONS
from astroscope.gaia_messages import GAIA_TRANSLATIONS
from astroscope.imaging_messages import IMAGING_TRANSLATIONS
from astroscope.observation_log_messages import OBSERVATION_LOG_TRANSLATIONS
from astroscope.planner_messages import PLANNER_TRANSLATIONS
from astroscope.schedule_messages import SCHEDULE_TRANSLATIONS
from astroscope.sky_map_messages import SKY_MAP_TRANSLATIONS
from astroscope.solar_system_messages import SOLAR_SYSTEM_TRANSLATIONS
from astroscope.telescope_messages import TELESCOPE_TRANSLATIONS
from astroscope.visibility_messages import VISIBILITY_TRANSLATIONS
from astroscope.weather_messages import WEATHER_TRANSLATIONS

SUPPORTED_LANGUAGES: Final[dict[str, str]] = {
    "English": "en",
    "日本語": "ja",
    "한국어": "ko",
    "ไทย": "th",
}

TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "app_title": {
        "en": "AstroScope AI Observatory",
        "ja": "AstroScope AI 天文台",
        "ko": "AstroScope AI 천문대",
        "th": "หอดูดาว AstroScope AI",
    },
    "app_subtitle": {
        "en": ("An intelligent observatory planner and interactive planetarium"),
        "ja": ("インテリジェント観測計画システムとインタラクティブ・プラネタリウム"),
        "ko": "지능형 관측 계획 시스템과 인터랙티브 플라네타륨",
        "th": ("ระบบวางแผนการสังเกตการณ์อัจฉริยะและท้องฟ้าจำลองแบบโต้ตอบ"),
    },
    "welcome": {
        "en": "Welcome to Project No. 2.",
        "ja": "プロジェクト第2号へようこそ。",
        "ko": "두 번째 프로젝트에 오신 것을 환영합니다.",
        "th": "ยินดีต้อนรับสู่โปรเจกต์หมายเลข 2",
    },
    "foundation_message": {
        "en": "The multilingual project foundation is working.",
        "ja": "多言語プロジェクトの基盤が正常に動作しています。",
        "ko": "다국어 프로젝트 기반이 정상적으로 작동하고 있습니다.",
        "th": "โครงสร้างพื้นฐานของโปรเจกต์หลายภาษาทำงานอย่างถูกต้อง",
    },
    "observer_section": {
        "en": "Observer location and astronomical time",
        "ja": "観測地点と天文時刻",
        "ko": "관측 위치와 천문 시간",
        "th": "ตำแหน่งผู้สังเกตการณ์และเวลาดาราศาสตร์",
    },
    "observer_explanation": {
        "en": (
            "Choose an observing site and local date and time. "
            "AstroScope converts them into astronomical time values."
        ),
        "ja": ("観測地点と現地日時を選択してください。AstroScopeが天文時刻へ変換します。"),
        "ko": (
            "관측 장소와 현지 날짜 및 시간을 선택하세요. AstroScope가 천문 시간 값으로 변환합니다."
        ),
        "th": ("เลือกสถานที่สังเกตการณ์และวันเวลาท้องถิ่น AstroScope จะแปลงเป็นค่าทางเวลาดาราศาสตร์"),
    },
    "observer_preset": {
        "en": "Observing site",
        "ja": "観測地点",
        "ko": "관측 장소",
        "th": "สถานที่สังเกตการณ์",
    },
    "preset_osaka": {
        "en": "Osaka, Japan",
        "ja": "大阪（日本）",
        "ko": "오사카, 일본",
        "th": "โอซากะ ประเทศญี่ปุ่น",
    },
    "preset_bangkok": {
        "en": "Bangkok, Thailand",
        "ja": "バンコク（タイ）",
        "ko": "방콕, 태국",
        "th": "กรุงเทพมหานคร ประเทศไทย",
    },
    "preset_seoul": {
        "en": "Seoul, South Korea",
        "ja": "ソウル（韓国）",
        "ko": "서울, 대한민국",
        "th": "โซล ประเทศเกาหลีใต้",
    },
    "preset_greenwich": {
        "en": "Greenwich, United Kingdom",
        "ja": "グリニッジ（イギリス）",
        "ko": "그리니치, 영국",
        "th": "กรีนิช สหราชอาณาจักร",
    },
    "latitude": {
        "en": "Latitude (degrees)",
        "ja": "緯度（度）",
        "ko": "위도 (도)",
        "th": "ละติจูด (องศา)",
    },
    "longitude": {
        "en": "Longitude (degrees)",
        "ja": "経度（度）",
        "ko": "경도 (도)",
        "th": "ลองจิจูด (องศา)",
    },
    "elevation": {
        "en": "Elevation (metres)",
        "ja": "標高（メートル）",
        "ko": "고도 (미터)",
        "th": "ความสูงจากระดับน้ำทะเล (เมตร)",
    },
    "timezone": {
        "en": "Time zone",
        "ja": "タイムゾーン",
        "ko": "시간대",
        "th": "เขตเวลา",
    },
    "observation_date": {
        "en": "Observation date",
        "ja": "観測日",
        "ko": "관측 날짜",
        "th": "วันที่สังเกตการณ์",
    },
    "observation_time": {
        "en": "Local observation time",
        "ja": "現地観測時刻",
        "ko": "현지 관측 시간",
        "th": "เวลาสังเกตการณ์ท้องถิ่น",
    },
    "coordinate_help": {
        "en": "East longitude is positive. West longitude is negative.",
        "ja": "東経は正、西経は負の値を使用します。",
        "ko": "동경은 양수이고 서경은 음수입니다.",
        "th": "ลองจิจูดตะวันออกเป็นบวก และตะวันตกเป็นลบ",
    },
    "calculate_time": {
        "en": "Calculate astronomical time",
        "ja": "天文時刻を計算",
        "ko": "천문 시간 계산",
        "th": "คำนวณเวลาดาราศาสตร์",
    },
    "results": {
        "en": "Astronomical time results",
        "ja": "天文時刻の計算結果",
        "ko": "천문 시간 계산 결과",
        "th": "ผลการคำนวณเวลาดาราศาสตร์",
    },
    "local_datetime": {
        "en": "Local datetime",
        "ja": "現地日時",
        "ko": "현지 날짜 및 시간",
        "th": "วันเวลาท้องถิ่น",
    },
    "utc_datetime": {
        "en": "UTC datetime",
        "ja": "UTC日時",
        "ko": "UTC 날짜 및 시간",
        "th": "วันเวลา UTC",
    },
    "julian_date": {
        "en": "Julian Date",
        "ja": "ユリウス日",
        "ko": "율리우스일",
        "th": "วันจูเลียน",
    },
    "modified_julian_date": {
        "en": "Modified Julian Date",
        "ja": "修正ユリウス日",
        "ko": "수정 율리우스일",
        "th": "วันจูเลียนดัดแปลง",
    },
    "local_sidereal_time": {
        "en": "Local apparent sidereal time",
        "ja": "地方視恒星時",
        "ko": "지방 겉보기 항성시",
        "th": "เวลาดาราคติปรากฏท้องถิ่น",
    },
    "result_note": {
        "en": (
            "Local sidereal time indicates which right ascension is crossing the local meridian."
        ),
        "ja": ("地方恒星時は、どの赤経が観測地点の子午線を通過しているかを示します。"),
        "ko": ("지방 항성시는 현재 어떤 적경이 관측지의 자오선을 통과하는지 나타냅니다."),
        "th": ("เวลาดาราคติท้องถิ่นแสดงว่าไรต์แอสเซนชันใดกำลังผ่านเส้นเมริเดียนของผู้สังเกตการณ์"),
    },
    "calculation_error": {
        "en": "Calculation error",
        "ja": "計算エラー",
        "ko": "계산 오류",
        "th": "ข้อผิดพลาดในการคำนวณ",
    },
    "future_features": {
        "en": "Future features",
        "ja": "今後実装する機能",
        "ko": "향후 기능",
        "th": "ฟังก์ชันที่จะพัฒนาในอนาคต",
    },
    "feature_visibility": {
        "en": "Celestial-object visibility calculations",
        "ja": "天体の可視性計算",
        "ko": "천체 가시성 계산",
        "th": "การคำนวณการมองเห็นวัตถุท้องฟ้า",
    },
    "feature_planetarium": {
        "en": "Interactive planetarium",
        "ja": "インタラクティブ・プラネタリウム",
        "ko": "인터랙티브 플라네타륨",
        "th": "ท้องฟ้าจำลองแบบโต้ตอบ",
    },
    "feature_telescope": {
        "en": "Telescope and eyepiece simulator",
        "ja": "望遠鏡・接眼レンズシミュレータ",
        "ko": "망원경 및 접안렌즈 시뮬레이터",
        "th": "เครื่องจำลองกล้องโทรทรรศน์และเลนส์ใกล้ตา",
    },
}


TRANSLATIONS.update(COORDINATE_TRANSLATIONS)
TRANSLATIONS.update(VISIBILITY_TRANSLATIONS)


TRANSLATIONS.update(SOLAR_SYSTEM_TRANSLATIONS)


TRANSLATIONS.update(SKY_MAP_TRANSLATIONS)


TRANSLATIONS.update(PLANNER_TRANSLATIONS)


TRANSLATIONS.update(SCHEDULE_TRANSLATIONS)


TRANSLATIONS.update(WEATHER_TRANSLATIONS)


TRANSLATIONS.update(TELESCOPE_TRANSLATIONS)


TRANSLATIONS.update(IMAGING_TRANSLATIONS)


TRANSLATIONS.update(OBSERVATION_LOG_TRANSLATIONS)


TRANSLATIONS.update(GAIA_TRANSLATIONS)
TRANSLATIONS.update(EXOPLANET_TRANSLATIONS)


def translate(key: str, language: str) -> str:
    """Return translated text for a key and language code."""

    if key not in TRANSLATIONS:
        raise KeyError(f"Unknown translation key: {key}")

    if language not in SUPPORTED_LANGUAGES.values():
        raise KeyError(f"Unsupported language: {language}")

    return TRANSLATIONS[key][language]
