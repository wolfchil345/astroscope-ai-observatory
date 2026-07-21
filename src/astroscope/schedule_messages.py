"""Four-language interface text for night scheduling."""

from typing import Final

SCHEDULE_TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "schedule_section": {
        "en": "Night timeline and observation schedule",
        "ja": "夜間タイムラインと観測スケジュール",
        "ko": "야간 타임라인과 관측 일정",
        "th": "ไทม์ไลน์กลางคืนและตารางการสังเกตการณ์",
    },
    "schedule_explanation": {
        "en": (
            "Evaluate targets throughout the night and create "
            "a chronological schedule from the best recommended target."
        ),
        "ja": (
            "夜間を通して天体を評価し、各時間帯で最も推奨される"
            "天体から時系列の観測予定を作成します。"
        ),
        "ko": (
            "밤 동안 천체를 평가하고 각 시간대의 최고 추천 대상으로 시간순 관측 일정을 생성합니다."
        ),
        "th": ("ประเมินวัตถุตลอดทั้งคืนและสร้างตารางตามลำดับเวลาจากวัตถุที่ได้รับคำแนะนำสูงสุดในแต่ละช่วง"),
    },
    "schedule_start_time": {
        "en": "Schedule start time",
        "ja": "スケジュール開始時刻",
        "ko": "일정 시작 시간",
        "th": "เวลาเริ่มตาราง",
    },
    "schedule_end_time": {
        "en": "Schedule end time",
        "ja": "スケジュール終了時刻",
        "ko": "일정 종료 시간",
        "th": "เวลาสิ้นสุดตาราง",
    },
    "sampling_interval": {
        "en": "Sampling interval",
        "ja": "計算間隔",
        "ko": "계산 간격",
        "th": "ช่วงเวลาการคำนวณ",
    },
    "minutes_short": {
        "en": "minutes",
        "ja": "分",
        "ko": "분",
        "th": "นาที",
    },
    "schedule_minimum_moon_separation": {
        "en": "Schedule Moon-separation minimum",
        "ja": "スケジュール用の月離角最低値",
        "ko": "일정 달 각거리 최솟값",
        "th": "ระยะขั้นต่ำจากดวงจันทร์สำหรับตาราง",
    },
    "schedule_minimum_score": {
        "en": "Schedule recommendation score",
        "ja": "スケジュール用の推奨スコア",
        "ko": "일정 추천 점수",
        "th": "คะแนนแนะนำสำหรับตาราง",
    },
    "schedule_catalog_targets": {
        "en": "Schedule catalogue targets",
        "ja": "カタログ天体を予定に含める",
        "ko": "카탈로그 대상 일정 포함",
        "th": "รวมวัตถุแค็ตตาล็อกในตาราง",
    },
    "schedule_solar_targets": {
        "en": "Schedule Solar System targets",
        "ja": "太陽系天体を予定に含める",
        "ko": "태양계 대상 일정 포함",
        "th": "รวมวัตถุระบบสุริยะในตาราง",
    },
    "generate_schedule": {
        "en": "Generate night schedule",
        "ja": "夜間観測スケジュールを生成",
        "ko": "야간 관측 일정 생성",
        "th": "สร้างตารางการสังเกตการณ์กลางคืน",
    },
    "schedule_results": {
        "en": "Generated observation schedule",
        "ja": "生成された観測スケジュール",
        "ko": "생성된 관측 일정",
        "th": "ตารางการสังเกตการณ์ที่สร้างแล้ว",
    },
    "schedule_block_count": {
        "en": "Observation blocks",
        "ja": "観測ブロック数",
        "ko": "관측 블록 수",
        "th": "จำนวนช่วงสังเกตการณ์",
    },
    "scheduled_minutes": {
        "en": "Scheduled minutes",
        "ja": "観測予定時間（分）",
        "ko": "예정된 관측 시간(분)",
        "th": "นาทีที่จัดตาราง",
    },
    "timeline_samples": {
        "en": "Timeline samples",
        "ja": "タイムライン計算点",
        "ko": "타임라인 표본 수",
        "th": "จำนวนจุดในไทม์ไลน์",
    },
    "schedule_top_target": {
        "en": "Top scheduled target",
        "ja": "最高評価の予定天体",
        "ko": "최고 일정 대상",
        "th": "วัตถุอันดับสูงสุดในตาราง",
    },
    "schedule_start": {
        "en": "Start",
        "ja": "開始",
        "ko": "시작",
        "th": "เริ่ม",
    },
    "schedule_end": {
        "en": "End",
        "ja": "終了",
        "ko": "종료",
        "th": "สิ้นสุด",
    },
    "schedule_duration": {
        "en": "Duration",
        "ja": "観測時間",
        "ko": "관측 시간",
        "th": "ระยะเวลา",
    },
    "schedule_peak_time": {
        "en": "Peak time",
        "ja": "最高スコア時刻",
        "ko": "최고 점수 시간",
        "th": "เวลาคะแนนสูงสุด",
    },
    "schedule_peak_score": {
        "en": "Peak score",
        "ja": "最高スコア",
        "ko": "최고 점수",
        "th": "คะแนนสูงสุด",
    },
    "schedule_peak_altitude": {
        "en": "Peak altitude",
        "ja": "最高評価時の高度",
        "ko": "최고 평가 고도",
        "th": "มุมเงยเมื่อคะแนนสูงสุด",
    },
    "schedule_peak_moon_separation": {
        "en": "Moon separation at peak",
        "ja": "最高評価時の月離角",
        "ko": "최고 평가 시 달 각거리",
        "th": "ระยะจากดวงจันทร์เมื่อคะแนนสูงสุด",
    },
    "schedule_timeline_chart": {
        "en": "Target scores throughout the night",
        "ja": "夜間における天体スコアの変化",
        "ko": "밤 동안의 대상 점수 변화",
        "th": "การเปลี่ยนแปลงคะแนนวัตถุตลอดคืน",
    },
    "schedule_time_axis": {
        "en": "Local observation time",
        "ja": "現地観測時刻",
        "ko": "현지 관측 시간",
        "th": "เวลาสังเกตการณ์ท้องถิ่น",
    },
    "schedule_score_axis": {
        "en": "Observation score",
        "ja": "観測スコア",
        "ko": "관측 점수",
        "th": "คะแนนการสังเกตการณ์",
    },
    "no_schedule_blocks": {
        "en": ("No target met every scheduling condition during the selected period."),
        "ja": ("選択した時間帯では、すべての条件を満たす観測対象がありませんでした。"),
        "ko": ("선택한 시간 동안 모든 일정 조건을 만족하는 관측 대상이 없습니다."),
        "th": ("ไม่มีวัตถุที่ผ่านเงื่อนไขทั้งหมดในช่วงเวลาที่เลือก"),
    },
    "schedule_note": {
        "en": (
            "Each interval is assigned to the highest-ranked "
            "recommended target. Smaller intervals provide finer "
            "detail but require more calculation time."
        ),
        "ja": (
            "各時間帯には最高順位の推奨天体を割り当てます。"
            "計算間隔を短くすると詳細になりますが、処理時間が増えます。"
        ),
        "ko": (
            "각 시간대에는 최고 순위 추천 대상이 배정됩니다. "
            "간격이 짧을수록 정밀하지만 계산 시간이 증가합니다."
        ),
        "th": ("แต่ละช่วงจะถูกกำหนดให้กับวัตถุแนะนำอันดับสูงสุด ช่วงที่สั้นลงให้รายละเอียดมากขึ้นแต่ใช้เวลาคำนวณมากขึ้น"),
    },
    "schedule_error": {
        "en": "Schedule-generation error",
        "ja": "スケジュール生成エラー",
        "ko": "일정 생성 오류",
        "th": "ข้อผิดพลาดในการสร้างตาราง",
    },
}
