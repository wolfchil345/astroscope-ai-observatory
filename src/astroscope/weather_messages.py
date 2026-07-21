"""Four-language interface text for observing weather."""

from typing import Final

WEATHER_TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "weather_section": {
        "en": "Weather-aware observing conditions",
        "ja": "天気を考慮した観測条件",
        "ko": "날씨를 반영한 관측 조건",
        "th": "สภาพการสังเกตการณ์ที่คำนึงถึงสภาพอากาศ",
    },
    "weather_explanation": {
        "en": (
            "Retrieve an hourly forecast and evaluate cloud cover, "
            "precipitation, visibility, humidity, wind, and dew risk."
        ),
        "ja": ("時間別予報を取得し、雲量、降水、視程、湿度、風、結露リスクを評価します。"),
        "ko": ("시간별 예보를 불러와 운량, 강수, 가시거리, 습도, 바람, 이슬 위험을 평가합니다."),
        "th": ("ดึงข้อมูลพยากรณ์รายชั่วโมงและประเมินเมฆ ฝน ทัศนวิสัย ความชื้น ลม และความเสี่ยงจากน้ำค้าง"),
    },
    "weather_start_time": {
        "en": "Weather-window start",
        "ja": "天気確認の開始時刻",
        "ko": "날씨 확인 시작 시간",
        "th": "เวลาเริ่มตรวจสอบสภาพอากาศ",
    },
    "weather_end_time": {
        "en": "Weather-window end",
        "ja": "天気確認の終了時刻",
        "ko": "날씨 확인 종료 시간",
        "th": "เวลาสิ้นสุดการตรวจสอบสภาพอากาศ",
    },
    "fetch_weather_forecast": {
        "en": "Retrieve observing forecast",
        "ja": "観測用天気予報を取得",
        "ko": "관측용 날씨 예보 불러오기",
        "th": "ดึงข้อมูลพยากรณ์สำหรับการสังเกตการณ์",
    },
    "weather_results": {
        "en": "Hourly observing forecast",
        "ja": "時間別の観測予報",
        "ko": "시간별 관측 예보",
        "th": "พยากรณ์การสังเกตการณ์รายชั่วโมง",
    },
    "best_weather_hour": {
        "en": "Best forecast hour",
        "ja": "最良の予報時刻",
        "ko": "최적 예보 시간",
        "th": "ชั่วโมงที่พยากรณ์ดีที่สุด",
    },
    "best_weather_score": {
        "en": "Best weather score",
        "ja": "最高天気スコア",
        "ko": "최고 날씨 점수",
        "th": "คะแนนสภาพอากาศสูงสุด",
    },
    "average_weather_score": {
        "en": "Average weather score",
        "ja": "平均天気スコア",
        "ko": "평균 날씨 점수",
        "th": "คะแนนสภาพอากาศเฉลี่ย",
    },
    "maximum_cloud_cover": {
        "en": "Maximum cloud cover",
        "ja": "最大雲量",
        "ko": "최대 운량",
        "th": "ปริมาณเมฆสูงสุด",
    },
    "worst_dew_risk": {
        "en": "Worst dew risk",
        "ja": "最大結露リスク",
        "ko": "최대 이슬 위험",
        "th": "ความเสี่ยงจากน้ำค้างสูงสุด",
    },
    "weather_time": {
        "en": "Local time",
        "ja": "現地時刻",
        "ko": "현지 시간",
        "th": "เวลาท้องถิ่น",
    },
    "weather_score": {
        "en": "Weather score",
        "ja": "天気スコア",
        "ko": "날씨 점수",
        "th": "คะแนนสภาพอากาศ",
    },
    "weather_rating": {
        "en": "Weather rating",
        "ja": "天気評価",
        "ko": "날씨 평가",
        "th": "ระดับสภาพอากาศ",
    },
    "weather_rating_excellent": {
        "en": "Excellent",
        "ja": "非常に良い",
        "ko": "매우 좋음",
        "th": "ยอดเยี่ยม",
    },
    "weather_rating_good": {
        "en": "Good",
        "ja": "良い",
        "ko": "좋음",
        "th": "ดี",
    },
    "weather_rating_fair": {
        "en": "Fair",
        "ja": "普通",
        "ko": "보통",
        "th": "พอใช้",
    },
    "weather_rating_poor": {
        "en": "Poor",
        "ja": "悪い",
        "ko": "나쁨",
        "th": "ไม่ดี",
    },
    "weather_rating_unsuitable": {
        "en": "Unsuitable",
        "ja": "観測不適",
        "ko": "관측 부적합",
        "th": "ไม่เหมาะสำหรับการสังเกต",
    },
    "temperature_c": {
        "en": "Temperature",
        "ja": "気温",
        "ko": "기온",
        "th": "อุณหภูมิ",
    },
    "dew_point_c": {
        "en": "Dew point",
        "ja": "露点",
        "ko": "이슬점",
        "th": "จุดน้ำค้าง",
    },
    "dew_spread_c": {
        "en": "Dew-point spread",
        "ja": "気温と露点の差",
        "ko": "기온과 이슬점 차이",
        "th": "ส่วนต่างอุณหภูมิกับจุดน้ำค้าง",
    },
    "relative_humidity": {
        "en": "Relative humidity",
        "ja": "相対湿度",
        "ko": "상대 습도",
        "th": "ความชื้นสัมพัทธ์",
    },
    "cloud_cover": {
        "en": "Cloud cover",
        "ja": "雲量",
        "ko": "운량",
        "th": "ปริมาณเมฆ",
    },
    "precipitation_probability": {
        "en": "Precipitation probability",
        "ja": "降水確率",
        "ko": "강수 확률",
        "th": "โอกาสเกิดฝน",
    },
    "precipitation_amount": {
        "en": "Precipitation",
        "ja": "降水量",
        "ko": "강수량",
        "th": "ปริมาณน้ำฝน",
    },
    "visibility_km": {
        "en": "Visibility",
        "ja": "視程",
        "ko": "가시거리",
        "th": "ทัศนวิสัย",
    },
    "wind_speed": {
        "en": "Wind speed",
        "ja": "風速",
        "ko": "풍속",
        "th": "ความเร็วลม",
    },
    "wind_gusts": {
        "en": "Wind gusts",
        "ja": "最大瞬間風速",
        "ko": "돌풍",
        "th": "ลมกระโชก",
    },
    "dew_risk": {
        "en": "Dew risk",
        "ja": "結露リスク",
        "ko": "이슬 위험",
        "th": "ความเสี่ยงจากน้ำค้าง",
    },
    "dew_risk_low": {
        "en": "Low",
        "ja": "低い",
        "ko": "낮음",
        "th": "ต่ำ",
    },
    "dew_risk_moderate": {
        "en": "Moderate",
        "ja": "中程度",
        "ko": "보통",
        "th": "ปานกลาง",
    },
    "dew_risk_high": {
        "en": "High",
        "ja": "高い",
        "ko": "높음",
        "th": "สูง",
    },
    "dew_risk_critical": {
        "en": "Critical",
        "ja": "非常に高い",
        "ko": "매우 높음",
        "th": "วิกฤต",
    },
    "dew_warning_low": {
        "en": "Dew risk is low for the selected period.",
        "ja": "選択した時間帯の結露リスクは低いです。",
        "ko": "선택한 시간대의 이슬 위험이 낮습니다.",
        "th": "ความเสี่ยงจากน้ำค้างในช่วงที่เลือกอยู่ในระดับต่ำ",
    },
    "dew_warning_moderate": {
        "en": ("Moderate dew risk detected. Keep lens heaters or protective covers available."),
        "ja": ("中程度の結露リスクがあります。レンズヒーターや保護カバーを準備してください。"),
        "ko": ("중간 수준의 이슬 위험이 있습니다. 렌즈 히터나 보호 덮개를 준비하세요."),
        "th": ("ตรวจพบความเสี่ยงจากน้ำค้างระดับปานกลาง ควรเตรียมฮีตเตอร์เลนส์หรืออุปกรณ์ป้องกัน"),
    },
    "dew_warning_high": {
        "en": ("High dew risk detected. Active dew prevention is strongly recommended."),
        "ja": ("高い結露リスクがあります。積極的な結露対策を強く推奨します。"),
        "ko": ("이슬 위험이 높습니다. 적극적인 이슬 방지 대책을 강력히 권장합니다."),
        "th": ("ตรวจพบความเสี่ยงจากน้ำค้างสูง ควรใช้อุปกรณ์ป้องกันน้ำค้างอย่างจริงจัง"),
    },
    "dew_warning_critical": {
        "en": (
            "Critical condensation risk. Equipment may become wet "
            "without active heating and protection."
        ),
        "ja": (
            "結露リスクが非常に高いです。加熱や保護を行わない場合、機材が濡れる可能性があります。"
        ),
        "ko": ("응결 위험이 매우 높습니다. 적극적인 가열과 보호가 없으면 장비가 젖을 수 있습니다."),
        "th": ("มีความเสี่ยงต่อการควบแน่นระดับวิกฤต อุปกรณ์อาจเปียกหากไม่มีการให้ความร้อนและการป้องกัน"),
    },
    "unsafe_weather_warning": {
        "en": (
            "At least one hour is unsuitable because of rain, "
            "strong wind, or a very low weather score."
        ),
        "ja": ("雨、強風、または非常に低い天気スコアにより、観測に適さない時間帯があります。"),
        "ko": ("비, 강풍 또는 매우 낮은 날씨 점수로 인해 관측에 부적합한 시간이 있습니다."),
        "th": ("มีอย่างน้อยหนึ่งช่วงเวลาที่ไม่เหมาะสมเนื่องจากฝน ลมแรง หรือคะแนนสภาพอากาศต่ำมาก"),
    },
    "weather_score_chart": {
        "en": "Observing-weather score timeline",
        "ja": "観測天気スコアのタイムライン",
        "ko": "관측 날씨 점수 타임라인",
        "th": "ไทม์ไลน์คะแนนสภาพอากาศ",
    },
    "weather_conditions_chart": {
        "en": "Cloud and precipitation forecast",
        "ja": "雲量と降水の予報",
        "ko": "운량과 강수 예보",
        "th": "พยากรณ์เมฆและฝน",
    },
    "weather_time_axis": {
        "en": "Local forecast time",
        "ja": "現地予報時刻",
        "ko": "현지 예보 시간",
        "th": "เวลาพยากรณ์ท้องถิ่น",
    },
    "weather_source": {
        "en": "Forecast source",
        "ja": "予報データ提供元",
        "ko": "예보 데이터 출처",
        "th": "แหล่งข้อมูลพยากรณ์",
    },
    "weather_attribution": {
        "en": (
            "Weather data: [Open-Meteo](https://open-meteo.com/) "
            "under [CC BY 4.0]"
            "(https://creativecommons.org/licenses/by/4.0/). "
            "AstroScope transforms the data by calculating observing "
            "scores, ratings, and dew-risk categories."
        ),
        "ja": (
            "天気データ：[Open-Meteo](https://open-meteo.com/)、"
            "[CC BY 4.0]"
            "(https://creativecommons.org/licenses/by/4.0/)。"
            "AstroScopeは観測スコア、評価、結露リスクを計算して"
            "データを加工しています。"
        ),
        "ko": (
            "날씨 데이터: [Open-Meteo](https://open-meteo.com/), "
            "[CC BY 4.0]"
            "(https://creativecommons.org/licenses/by/4.0/). "
            "AstroScope는 관측 점수, 평가, 이슬 위험을 계산하여 "
            "원본 데이터를 변환합니다."
        ),
        "th": (
            "ข้อมูลสภาพอากาศ: [Open-Meteo]"
            "(https://open-meteo.com/) ภายใต้ "
            "[CC BY 4.0]"
            "(https://creativecommons.org/licenses/by/4.0/) "
            "AstroScope ปรับข้อมูลโดยคำนวณคะแนน ระดับ "
            "และความเสี่ยงจากน้ำค้าง"
        ),
    },
    "weather_forecast_note": {
        "en": (
            "Forecasts are available only for supported near-term "
            "dates. They are model predictions, not guarantees of "
            "actual observing conditions."
        ),
        "ja": (
            "予報を取得できるのは対応する近日の日付のみです。"
            "モデル予測であり、実際の観測条件を保証しません。"
        ),
        "ko": (
            "지원되는 가까운 날짜에 대해서만 예보를 조회할 수 "
            "있습니다. 실제 관측 조건을 보장하지 않습니다."
        ),
        "th": ("พยากรณ์ใช้ได้เฉพาะวันที่ในอนาคตอันใกล้ที่รองรับ และไม่รับประกันสภาพการสังเกตการณ์จริง"),
    },
    "weather_error": {
        "en": "Weather forecast error",
        "ja": "天気予報エラー",
        "ko": "날씨 예보 오류",
        "th": "ข้อผิดพลาดของข้อมูลพยากรณ์อากาศ",
    },
}
