"""Translations for the exoplanet transit observation scheduler."""

from __future__ import annotations

from typing import Final

SUPPORTED_TRANSIT_LANGUAGES: Final[tuple[str, ...]] = (
    "English",
    "日本語",
    "한국어",
    "ไทย",
)

_LANGUAGE_ALIASES: Final[dict[str, str]] = {
    "english": "en",
    "en": "en",
    "日本語": "ja",
    "japanese": "ja",
    "ja": "ja",
    "한국어": "ko",
    "korean": "ko",
    "ko": "ko",
    "ไทย": "th",
    "thai": "th",
    "th": "th",
}

_TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "en": {
        "title": "Exoplanet Transit Observation Scheduler",
        "description": (
            "Predict and rank transit observing windows using ephemerides, "
            "observer geometry, darkness, Moon separation, timing confidence, "
            "transit depth, and host-star brightness."
        ),
        "utc_caption": "All schedule dates and displayed event times use UTC.",
        "number_targets": "Number of targets",
        "observer_site": "Observer site",
        "site_name": "Site name",
        "latitude": "Latitude (degrees)",
        "longitude": "Longitude (degrees)",
        "elevation": "Elevation (meters)",
        "schedule_range": "Schedule range",
        "start_date": "Start date",
        "end_date": "End date",
        "observation_settings": "Observation settings",
        "baseline_before": "Baseline before transit (hours)",
        "baseline_after": "Baseline after transit (hours)",
        "uncertainty_multiplier": "Timing uncertainty multiplier",
        "minimum_altitude": "Minimum altitude (degrees)",
        "maximum_sun_altitude": "Maximum Sun altitude (degrees)",
        "visibility_samples": "Visibility samples",
        "transit_targets": "Transit targets",
        "target_number": "Target {number}",
        "planet_name": "Planet name",
        "host_star_name": "Host-star name",
        "right_ascension": "Right ascension (degrees)",
        "declination": "Declination (degrees)",
        "orbital_period": "Orbital period (days)",
        "reference_midpoint": "Reference midpoint (JD)",
        "transit_duration": "Transit duration (hours)",
        "period_uncertainty": "Period uncertainty (days)",
        "epoch_uncertainty": "Epoch uncertainty (days)",
        "transit_depth": "Transit depth (ppm)",
        "host_magnitude": "Host apparent magnitude",
        "generate_schedule": "Generate ranked schedule",
        "generating": "Predicting and ranking transit events...",
        "unable_generate": "Unable to generate schedule: {error}",
        "schedule_results": "Schedule results",
        "predicted_events": "Predicted events",
        "observable_events": "Observable events",
        "fully_visible": "Fully visible",
        "targets_searched": "Targets searched",
        "no_midpoint_prefix": ("No transit midpoint occurred in the selected range for: "),
        "no_events": "No transit events were predicted in the selected date range.",
        "inspect_event": "Inspect a ranked event",
        "priority_score": "Priority score",
        "midpoint_altitude": "Midpoint altitude",
        "observable_fraction": "Observable fraction",
        "timing_uncertainty": "Timing uncertainty",
        "event_times": ("Ingress: {ingress} | Midpoint: {midpoint} | Egress: {egress}"),
        "neutral_fields_prefix": "Neutral scores were used for missing fields: ",
        "download_schedule": "Download schedule",
        "download_caption": (
            "Export the ranked observation plan for analysis, automation, or calendar scheduling."
        ),
        "download_csv": "Download CSV",
        "download_json": "Download JSON",
        "download_calendar": "Download calendar",
        "column_rank": "Rank",
        "column_planet": "Planet",
        "column_score": "Score",
        "column_mid_transit": "Mid-transit UTC",
        "column_observable_fraction": "Observable fraction",
        "column_full_window": "Full window visible",
        "column_midpoint_altitude": "Midpoint altitude (deg)",
        "column_moon_separation": "Moon separation (deg)",
        "column_timing_uncertainty": "Timing uncertainty (h)",
    },
    "ja": {
        "title": "系外惑星トランジット観測スケジューラー",
        "description": (
            "軌道暦、観測地点の幾何条件、夜空の暗さ、月との離角、"
            "時刻精度、トランジット深度、主星の明るさを用いて、"
            "観測可能時間を予測・順位付けします。"
        ),
        "utc_caption": "日付とイベント時刻はすべてUTCで表示されます。",
        "number_targets": "対象数",
        "observer_site": "観測地点",
        "site_name": "地点名",
        "latitude": "緯度（度）",
        "longitude": "経度（度）",
        "elevation": "標高（m）",
        "schedule_range": "検索期間",
        "start_date": "開始日",
        "end_date": "終了日",
        "observation_settings": "観測設定",
        "baseline_before": "トランジット前の基準観測（時間）",
        "baseline_after": "トランジット後の基準観測（時間）",
        "uncertainty_multiplier": "時刻不確かさの倍率",
        "minimum_altitude": "最低高度（度）",
        "maximum_sun_altitude": "太陽高度の上限（度）",
        "visibility_samples": "可視性サンプル数",
        "transit_targets": "トランジット対象",
        "target_number": "対象 {number}",
        "planet_name": "惑星名",
        "host_star_name": "主星名",
        "right_ascension": "赤経（度）",
        "declination": "赤緯（度）",
        "orbital_period": "公転周期（日）",
        "reference_midpoint": "基準中央時刻（JD）",
        "transit_duration": "トランジット継続時間（時間）",
        "period_uncertainty": "周期の不確かさ（日）",
        "epoch_uncertainty": "基準時刻の不確かさ（日）",
        "transit_depth": "トランジット深度（ppm）",
        "host_magnitude": "主星の見かけの等級",
        "generate_schedule": "観測スケジュールを作成",
        "generating": "トランジットを予測し、順位付けしています...",
        "unable_generate": "スケジュールを作成できませんでした: {error}",
        "schedule_results": "スケジュール結果",
        "predicted_events": "予測イベント数",
        "observable_events": "観測可能イベント数",
        "fully_visible": "全時間観測可能",
        "targets_searched": "検索対象数",
        "no_midpoint_prefix": "選択期間内に中央時刻がない対象: ",
        "no_events": "選択期間内にトランジットは予測されませんでした。",
        "inspect_event": "詳細を確認するイベント",
        "priority_score": "優先度スコア",
        "midpoint_altitude": "中央時刻の高度",
        "observable_fraction": "観測可能割合",
        "timing_uncertainty": "時刻の不確かさ",
        "event_times": ("開始: {ingress} | 中央: {midpoint} | 終了: {egress}"),
        "neutral_fields_prefix": "欠損項目には中立スコアを使用しました: ",
        "download_schedule": "スケジュールをダウンロード",
        "download_caption": ("順位付き観測計画を解析、自動処理、カレンダー登録用に出力します。"),
        "download_csv": "CSVをダウンロード",
        "download_json": "JSONをダウンロード",
        "download_calendar": "カレンダーをダウンロード",
        "column_rank": "順位",
        "column_planet": "惑星",
        "column_score": "スコア",
        "column_mid_transit": "中央時刻 UTC",
        "column_observable_fraction": "観測可能割合",
        "column_full_window": "全時間観測可能",
        "column_midpoint_altitude": "中央高度（度）",
        "column_moon_separation": "月との離角（度）",
        "column_timing_uncertainty": "時刻不確かさ（時間）",
    },
    "ko": {
        "title": "외계행성 통과 관측 스케줄러",
        "description": (
            "궤도력, 관측지 기하 조건, 밤하늘의 어두움, 달과의 각거리, "
            "시각 정확도, 통과 깊이, 모항성 밝기를 이용하여 "
            "관측 가능 시간을 예측하고 순위를 매깁니다."
        ),
        "utc_caption": "모든 날짜와 이벤트 시각은 UTC로 표시됩니다.",
        "number_targets": "대상 수",
        "observer_site": "관측 장소",
        "site_name": "장소 이름",
        "latitude": "위도(도)",
        "longitude": "경도(도)",
        "elevation": "고도(m)",
        "schedule_range": "검색 기간",
        "start_date": "시작 날짜",
        "end_date": "종료 날짜",
        "observation_settings": "관측 설정",
        "baseline_before": "통과 전 기준 관측(시간)",
        "baseline_after": "통과 후 기준 관측(시간)",
        "uncertainty_multiplier": "시각 불확실성 배수",
        "minimum_altitude": "최소 고도(도)",
        "maximum_sun_altitude": "최대 태양 고도(도)",
        "visibility_samples": "가시성 샘플 수",
        "transit_targets": "통과 관측 대상",
        "target_number": "대상 {number}",
        "planet_name": "행성 이름",
        "host_star_name": "모항성 이름",
        "right_ascension": "적경(도)",
        "declination": "적위(도)",
        "orbital_period": "공전 주기(일)",
        "reference_midpoint": "기준 중앙 시각(JD)",
        "transit_duration": "통과 지속 시간(시간)",
        "period_uncertainty": "주기 불확실성(일)",
        "epoch_uncertainty": "기준 시각 불확실성(일)",
        "transit_depth": "통과 깊이(ppm)",
        "host_magnitude": "모항성 겉보기 등급",
        "generate_schedule": "순위 관측 일정 생성",
        "generating": "통과 이벤트를 예측하고 순위를 계산하는 중...",
        "unable_generate": "일정을 생성할 수 없습니다: {error}",
        "schedule_results": "일정 결과",
        "predicted_events": "예측 이벤트",
        "observable_events": "관측 가능 이벤트",
        "fully_visible": "전체 구간 관측 가능",
        "targets_searched": "검색 대상",
        "no_midpoint_prefix": "선택 기간에 중앙 시각이 없는 대상: ",
        "no_events": "선택 기간에 예측된 통과 이벤트가 없습니다.",
        "inspect_event": "상세 확인 이벤트",
        "priority_score": "우선순위 점수",
        "midpoint_altitude": "중앙 시각 고도",
        "observable_fraction": "관측 가능 비율",
        "timing_uncertainty": "시각 불확실성",
        "event_times": ("진입: {ingress} | 중앙: {midpoint} | 이탈: {egress}"),
        "neutral_fields_prefix": "누락된 항목에는 중립 점수를 사용했습니다: ",
        "download_schedule": "일정 다운로드",
        "download_caption": ("순위 관측 계획을 분석, 자동화 또는 캘린더 등록용으로 내보냅니다."),
        "download_csv": "CSV 다운로드",
        "download_json": "JSON 다운로드",
        "download_calendar": "캘린더 다운로드",
        "column_rank": "순위",
        "column_planet": "행성",
        "column_score": "점수",
        "column_mid_transit": "중앙 시각 UTC",
        "column_observable_fraction": "관측 가능 비율",
        "column_full_window": "전체 구간 관측 가능",
        "column_midpoint_altitude": "중앙 고도(도)",
        "column_moon_separation": "달과의 각거리(도)",
        "column_timing_uncertainty": "시각 불확실성(시간)",
    },
    "th": {
        "title": "เครื่องมือจัดตารางสังเกตการณ์ทรานซิตดาวเคราะห์นอกระบบ",
        "description": (
            "คาดการณ์และจัดอันดับช่วงเวลาสังเกตการณ์ทรานซิตจากข้อมูลวงโคจร "
            "ตำแหน่งผู้สังเกต ความมืดของท้องฟ้า ระยะห่างจากดวงจันทร์ "
            "ความแม่นยำของเวลา ความลึกของทรานซิต และความสว่างของดาวฤกษ์แม่"
        ),
        "utc_caption": "วันที่และเวลาเหตุการณ์ทั้งหมดแสดงเป็นเวลา UTC",
        "number_targets": "จำนวนเป้าหมาย",
        "observer_site": "สถานที่สังเกตการณ์",
        "site_name": "ชื่อสถานที่",
        "latitude": "ละติจูด (องศา)",
        "longitude": "ลองจิจูด (องศา)",
        "elevation": "ความสูง (เมตร)",
        "schedule_range": "ช่วงวันที่ค้นหา",
        "start_date": "วันที่เริ่มต้น",
        "end_date": "วันที่สิ้นสุด",
        "observation_settings": "การตั้งค่าการสังเกตการณ์",
        "baseline_before": "เวลาสังเกตก่อนทรานซิต (ชั่วโมง)",
        "baseline_after": "เวลาสังเกตหลังทรานซิต (ชั่วโมง)",
        "uncertainty_multiplier": "ตัวคูณความไม่แน่นอนของเวลา",
        "minimum_altitude": "มุมเงยต่ำสุด (องศา)",
        "maximum_sun_altitude": "มุมเงยสูงสุดของดวงอาทิตย์ (องศา)",
        "visibility_samples": "จำนวนจุดตัวอย่างการมองเห็น",
        "transit_targets": "เป้าหมายทรานซิต",
        "target_number": "เป้าหมาย {number}",
        "planet_name": "ชื่อดาวเคราะห์",
        "host_star_name": "ชื่อดาวฤกษ์แม่",
        "right_ascension": "ไรต์แอสเซนชัน (องศา)",
        "declination": "เดคลิเนชัน (องศา)",
        "orbital_period": "คาบการโคจร (วัน)",
        "reference_midpoint": "เวลากึ่งกลางอ้างอิง (JD)",
        "transit_duration": "ระยะเวลาทรานซิต (ชั่วโมง)",
        "period_uncertainty": "ความไม่แน่นอนของคาบ (วัน)",
        "epoch_uncertainty": "ความไม่แน่นอนของเวลาอ้างอิง (วัน)",
        "transit_depth": "ความลึกของทรานซิต (ppm)",
        "host_magnitude": "โชติมาตรปรากฏของดาวฤกษ์แม่",
        "generate_schedule": "สร้างตารางสังเกตการณ์",
        "generating": "กำลังคาดการณ์และจัดอันดับเหตุการณ์ทรานซิต...",
        "unable_generate": "ไม่สามารถสร้างตารางได้: {error}",
        "schedule_results": "ผลลัพธ์ตารางสังเกตการณ์",
        "predicted_events": "เหตุการณ์ที่คาดการณ์",
        "observable_events": "เหตุการณ์ที่สังเกตได้",
        "fully_visible": "สังเกตได้ตลอดช่วง",
        "targets_searched": "เป้าหมายที่ค้นหา",
        "no_midpoint_prefix": "ไม่มีเวลากึ่งกลางทรานซิตในช่วงที่เลือกสำหรับ: ",
        "no_events": "ไม่พบเหตุการณ์ทรานซิตในช่วงวันที่เลือก",
        "inspect_event": "ตรวจสอบเหตุการณ์ตามอันดับ",
        "priority_score": "คะแนนลำดับความสำคัญ",
        "midpoint_altitude": "มุมเงย ณ เวลากึ่งกลาง",
        "observable_fraction": "สัดส่วนที่สังเกตได้",
        "timing_uncertainty": "ความไม่แน่นอนของเวลา",
        "event_times": ("เริ่มเข้า: {ingress} | กึ่งกลาง: {midpoint} | ออกสิ้นสุด: {egress}"),
        "neutral_fields_prefix": "ใช้คะแนนกลางสำหรับข้อมูลที่ขาดหาย: ",
        "download_schedule": "ดาวน์โหลดตาราง",
        "download_caption": ("ส่งออกแผนการสังเกตการณ์เพื่อการวิเคราะห์ ระบบอัตโนมัติ หรือเพิ่มลงในปฏิทิน"),
        "download_csv": "ดาวน์โหลด CSV",
        "download_json": "ดาวน์โหลด JSON",
        "download_calendar": "ดาวน์โหลดปฏิทิน",
        "column_rank": "อันดับ",
        "column_planet": "ดาวเคราะห์",
        "column_score": "คะแนน",
        "column_mid_transit": "เวลากึ่งกลาง UTC",
        "column_observable_fraction": "สัดส่วนที่สังเกตได้",
        "column_full_window": "สังเกตได้ตลอดช่วง",
        "column_midpoint_altitude": "มุมเงยกึ่งกลาง (องศา)",
        "column_moon_separation": "ระยะห่างจากดวงจันทร์ (องศา)",
        "column_timing_uncertainty": "ความไม่แน่นอนของเวลา (ชั่วโมง)",
    },
}


def normalize_transit_language(language: str) -> str:
    """Convert a language name or code into an internal language code."""

    normalized = language.strip().casefold()
    return _LANGUAGE_ALIASES.get(normalized, "en")


def translate_transit(
    key: str,
    language: str = "English",
    **values: object,
) -> str:
    """Translate one scheduler interface string."""

    language_code = normalize_transit_language(language)

    try:
        template = _TRANSLATIONS[language_code][key]
    except KeyError as error:
        raise KeyError(f"Unknown transit scheduler translation key: {key}") from error

    return template.format(**values)


def transit_translation_keys() -> frozenset[str]:
    """Return the complete scheduler translation-key collection."""

    return frozenset(_TRANSLATIONS["en"])


def validate_transit_translations() -> None:
    """Require every language to contain exactly the same keys."""

    expected = transit_translation_keys()

    for language_code, translations in _TRANSLATIONS.items():
        actual = frozenset(translations)

        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)

            raise RuntimeError(
                "Transit translation keys do not match for "
                f"{language_code}. Missing={missing}, extra={extra}"
            )


validate_transit_translations()
