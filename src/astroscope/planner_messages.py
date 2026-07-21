"""Four-language interface text for observation planning."""

from typing import Final

PLANNER_TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "planner_section": {
        "en": "Smart observation planner",
        "ja": "スマート観測プランナー",
        "ko": "스마트 관측 플래너",
        "th": "ระบบวางแผนการสังเกตการณ์อัจฉริยะ",
    },
    "planner_explanation": {
        "en": (
            "Rank night-sky targets using altitude, airmass, Moon separation, and sky darkness."
        ),
        "ja": ("高度、エアマス、月からの角距離、空の暗さを用いて夜空の観測対象を順位付けします。"),
        "ko": (
            "고도, 대기질량, 달과의 각거리, 하늘의 어두움을 "
            "사용하여 밤하늘 관측 대상을 순위화합니다."
        ),
        "th": ("จัดอันดับวัตถุท้องฟ้ายามค่ำคืนจากมุมเงย มวลอากาศ ระยะจากดวงจันทร์ และความมืดของท้องฟ้า"),
    },
    "include_catalog_targets": {
        "en": "Include catalogue targets",
        "ja": "カタログ天体を含める",
        "ko": "카탈로그 대상 포함",
        "th": "รวมวัตถุจากแค็ตตาล็อก",
    },
    "include_solar_system_targets": {
        "en": "Include Solar System targets",
        "ja": "太陽系天体を含める",
        "ko": "태양계 대상 포함",
        "th": "รวมวัตถุในระบบสุริยะ",
    },
    "minimum_moon_separation": {
        "en": "Minimum Moon separation",
        "ja": "月からの最低角距離",
        "ko": "달과의 최소 각거리",
        "th": "ระยะเชิงมุมต่ำสุดจากดวงจันทร์",
    },
    "minimum_planner_score": {
        "en": "Minimum recommendation score",
        "ja": "推奨スコアの最低値",
        "ko": "최소 추천 점수",
        "th": "คะแนนแนะนำขั้นต่ำ",
    },
    "maximum_targets": {
        "en": "Maximum targets to display",
        "ja": "表示する天体の最大数",
        "ko": "표시할 최대 대상 수",
        "th": "จำนวนวัตถุสูงสุดที่จะแสดง",
    },
    "recommended_only": {
        "en": "Show recommended targets only",
        "ja": "推奨天体のみ表示",
        "ko": "추천 대상만 표시",
        "th": "แสดงเฉพาะวัตถุที่แนะนำ",
    },
    "create_observation_plan": {
        "en": "Create ranked observation plan",
        "ja": "順位付き観測計画を作成",
        "ko": "순위별 관측 계획 생성",
        "th": "สร้างแผนการสังเกตการณ์แบบจัดอันดับ",
    },
    "planner_results": {
        "en": "Ranked observation targets",
        "ja": "観測対象ランキング",
        "ko": "관측 대상 순위",
        "th": "อันดับวัตถุสำหรับการสังเกตการณ์",
    },
    "recommended_target_count": {
        "en": "Recommended targets",
        "ja": "推奨天体数",
        "ko": "추천 대상 수",
        "th": "จำนวนวัตถุที่แนะนำ",
    },
    "planner_total_targets": {
        "en": "Evaluated targets",
        "ja": "評価した天体数",
        "ko": "평가한 대상 수",
        "th": "จำนวนวัตถุที่ประเมิน",
    },
    "sun_altitude": {
        "en": "Sun altitude",
        "ja": "太陽高度",
        "ko": "태양 고도",
        "th": "มุมเงยของดวงอาทิตย์",
    },
    "best_target": {
        "en": "Highest-ranked target",
        "ja": "最高順位の天体",
        "ko": "최고 순위 대상",
        "th": "วัตถุอันดับสูงสุด",
    },
    "planner_rank": {
        "en": "Rank",
        "ja": "順位",
        "ko": "순위",
        "th": "อันดับ",
    },
    "planner_target": {
        "en": "Target",
        "ja": "観測対象",
        "ko": "관측 대상",
        "th": "วัตถุ",
    },
    "planner_category": {
        "en": "Category",
        "ja": "カテゴリー",
        "ko": "카테고리",
        "th": "ประเภท",
    },
    "category_catalog": {
        "en": "Catalogue",
        "ja": "カタログ天体",
        "ko": "카탈로그",
        "th": "แค็ตตาล็อก",
    },
    "category_solar_system": {
        "en": "Solar System",
        "ja": "太陽系",
        "ko": "태양계",
        "th": "ระบบสุริยะ",
    },
    "planner_score": {
        "en": "Score",
        "ja": "スコア",
        "ko": "점수",
        "th": "คะแนน",
    },
    "planner_rating": {
        "en": "Rating",
        "ja": "評価",
        "ko": "평가",
        "th": "ระดับ",
    },
    "rating_excellent": {
        "en": "Excellent",
        "ja": "最適",
        "ko": "매우 우수",
        "th": "ยอดเยี่ยม",
    },
    "rating_very_good": {
        "en": "Very good",
        "ja": "非常に良い",
        "ko": "매우 좋음",
        "th": "ดีมาก",
    },
    "rating_good": {
        "en": "Good",
        "ja": "良い",
        "ko": "좋음",
        "th": "ดี",
    },
    "rating_fair": {
        "en": "Fair",
        "ja": "普通",
        "ko": "보통",
        "th": "พอใช้",
    },
    "rating_poor": {
        "en": "Poor",
        "ja": "不向き",
        "ko": "좋지 않음",
        "th": "ไม่เหมาะสม",
    },
    "planner_altitude": {
        "en": "Altitude",
        "ja": "高度",
        "ko": "고도",
        "th": "มุมเงย",
    },
    "planner_airmass": {
        "en": "Airmass",
        "ja": "エアマス",
        "ko": "대기질량",
        "th": "มวลอากาศ",
    },
    "planner_moon_separation": {
        "en": "Moon separation",
        "ja": "月からの角距離",
        "ko": "달과의 각거리",
        "th": "ระยะจากดวงจันทร์",
    },
    "planner_recommended": {
        "en": "Recommended",
        "ja": "推奨",
        "ko": "추천",
        "th": "แนะนำ",
    },
    "ranking_chart": {
        "en": "Observation-score ranking",
        "ja": "観測スコアランキング",
        "ko": "관측 점수 순위",
        "th": "อันดับคะแนนการสังเกตการณ์",
    },
    "no_planner_categories": {
        "en": "Select at least one target category.",
        "ja": "少なくとも1つの天体カテゴリーを選択してください。",
        "ko": "대상 카테고리를 하나 이상 선택하세요.",
        "th": "เลือกประเภทวัตถุอย่างน้อยหนึ่งประเภท",
    },
    "no_recommended_targets": {
        "en": (
            "No targets meet every recommendation filter. "
            "The highest-ranked available targets are shown instead."
        ),
        "ja": ("すべての推奨条件を満たす天体がありません。代わりに現在の上位天体を表示します。"),
        "ko": (
            "모든 추천 조건을 충족하는 대상이 없습니다. "
            "대신 현재 가장 높은 순위의 대상을 표시합니다."
        ),
        "th": ("ไม่มีวัตถุที่ผ่านเงื่อนไขแนะนำทั้งหมด ระบบจะแสดงวัตถุที่มีอันดับสูงสุดแทน"),
    },
    "planner_note": {
        "en": (
            "This is a transparent heuristic ranking, not a weather "
            "forecast or photometric-quality guarantee."
        ),
        "ja": (
            "これは説明可能なヒューリスティック評価です。"
            "天気予報や測光品質を保証するものではありません。"
        ),
        "ko": ("이 결과는 설명 가능한 휴리스틱 순위이며 날씨나 측광 품질을 보장하지 않습니다."),
        "th": ("ผลลัพธ์นี้เป็นการจัดอันดับด้วยกฎที่อธิบายได้ ไม่ใช่การพยากรณ์อากาศหรือการรับประกันคุณภาพเชิงแสง"),
    },
    "planner_error": {
        "en": "Observation-planner error",
        "ja": "観測プランナーエラー",
        "ko": "관측 플래너 오류",
        "th": "ข้อผิดพลาดของระบบวางแผนการสังเกตการณ์",
    },
}
