"""Internationalization utilities for AstroScope AI."""

from typing import Final

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
        "en": "An intelligent observatory planner and interactive planetarium",
        "ja": "インテリジェント観測計画システムとインタラクティブ・プラネタリウム",
        "ko": "지능형 관측 계획 시스템과 인터랙티브 플라네타륨",
        "th": "ระบบวางแผนการสังเกตการณ์อัจฉริยะและท้องฟ้าจำลองแบบโต้ตอบ",
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
        "th": "โครงสร้างพื้นฐานของโปรเจกต์หลายภาษากำลังทำงานอย่างถูกต้อง",
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


def translate(key: str, language: str) -> str:
    """Return translated text for a key and language code.

    Args:
        key: Translation key.
        language: ISO-style project language code.

    Raises:
        KeyError: If the key or language is unsupported.
    """
    if key not in TRANSLATIONS:
        raise KeyError(f"Unknown translation key: {key}")

    if language not in SUPPORTED_LANGUAGES.values():
        raise KeyError(f"Unsupported language: {language}")

    return TRANSLATIONS[key][language]
    