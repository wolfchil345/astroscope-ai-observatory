"""Translations for the NASA exoplanet explorer."""

from typing import Final

EXOPLANET_TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "exoplanet_title": {
        "en": "NASA Exoplanet Transit Explorer",
        "ja": "NASA系外惑星トランジット・エクスプローラー",
        "ko": "NASA 외계행성 트랜싯 탐색기",
        "th": "เครื่องมือสำรวจทรานซิตดาวเคราะห์นอกระบบของ NASA",
    },
    "exoplanet_subtitle": {
        "en": (
            "Explore confirmed planets, compare planetary populations, "
            "and simulate transit light curves."
        ),
        "ja": (
            "確認済み系外惑星を探索し、惑星集団を比較して、"
            "トランジット光度曲線をシミュレーションします。"
        ),
        "ko": (
            "확인된 외계행성을 탐색하고 행성 집단을 비교하며 트랜싯 광도 곡선을 시뮬레이션합니다."
        ),
        "th": (
            "สำรวจดาวเคราะห์นอกระบบที่ได้รับการยืนยัน เปรียบเทียบประชากรดาวเคราะห์ และจำลองกราฟแสงของทรานซิต"
        ),
    },
    "exoplanet_archive_note": {
        "en": (
            "Data are retrieved from the NASA Exoplanet Archive. "
            "Calculated values are educational estimates."
        ),
        "ja": ("データはNASA Exoplanet Archiveから取得します。計算値は教育目的の推定値です。"),
        "ko": (
            "데이터는 NASA Exoplanet Archive에서 가져옵니다. 계산값은 교육 목적의 추정치입니다."
        ),
        "th": ("ข้อมูลดึงมาจาก NASA Exoplanet Archive ค่าที่คำนวณเป็นค่าประมาณเพื่อการศึกษา"),
    },
    "exoplanet_search_controls": {
        "en": "Catalogue search",
        "ja": "カタログ検索",
        "ko": "카탈로그 검색",
        "th": "ค้นหาแคตตาล็อก",
    },
    "exoplanet_row_limit": {
        "en": "Maximum returned planets",
        "ja": "取得する惑星の最大数",
        "ko": "최대 반환 행성 수",
        "th": "จำนวนดาวเคราะห์สูงสุดที่แสดง",
    },
    "exoplanet_transiting_only": {
        "en": "Transiting planets only",
        "ja": "トランジット惑星のみ",
        "ko": "트랜싯 행성만",
        "th": "เฉพาะดาวเคราะห์ที่เกิดทรานซิต",
    },
    "exoplanet_discovery_method": {
        "en": "Discovery method",
        "ja": "発見方法",
        "ko": "발견 방법",
        "th": "วิธีการค้นพบ",
    },
    "exoplanet_all_methods": {
        "en": "All discovery methods",
        "ja": "すべての発見方法",
        "ko": "모든 발견 방법",
        "th": "ทุกวิธีการค้นพบ",
    },
    "exoplanet_max_distance_pc": {
        "en": "Maximum distance (pc)",
        "ja": "最大距離（pc）",
        "ko": "최대 거리 (pc)",
        "th": "ระยะทางสูงสุด (pc)",
    },
    "exoplanet_max_radius_earth": {
        "en": "Maximum planet radius (Earth radii)",
        "ja": "惑星半径の上限（地球半径）",
        "ko": "최대 행성 반지름 (지구 반지름)",
        "th": "รัศมีดาวเคราะห์สูงสุด (รัศมีโลก)",
    },
    "exoplanet_min_temperature_k": {
        "en": "Minimum equilibrium temperature (K)",
        "ja": "最低平衡温度（K）",
        "ko": "최저 평형 온도 (K)",
        "th": "อุณหภูมิสมดุลต่ำสุด (K)",
    },
    "exoplanet_max_temperature_k": {
        "en": "Maximum equilibrium temperature (K)",
        "ja": "最高平衡温度（K）",
        "ko": "최고 평형 온도 (K)",
        "th": "อุณหภูมิสมดุลสูงสุด (K)",
    },
    "exoplanet_timeout_seconds": {
        "en": "Request timeout (seconds)",
        "ja": "通信タイムアウト（秒）",
        "ko": "요청 제한 시간 (초)",
        "th": "เวลารอการเชื่อมต่อ (วินาที)",
    },
    "exoplanet_optional_filter": {
        "en": "Enable this optional filter",
        "ja": "この任意フィルターを有効にする",
        "ko": "이 선택 필터 사용",
        "th": "เปิดใช้ตัวกรองเสริมนี้",
    },
    "exoplanet_search_button": {
        "en": "Search NASA archive",
        "ja": "NASAアーカイブを検索",
        "ko": "NASA 아카이브 검색",
        "th": "ค้นหาในคลังข้อมูล NASA",
    },
    "exoplanet_searching": {
        "en": "Contacting the NASA Exoplanet Archive...",
        "ja": "NASA Exoplanet Archiveに接続しています...",
        "ko": "NASA Exoplanet Archive에 연결하는 중...",
        "th": "กำลังเชื่อมต่อ NASA Exoplanet Archive...",
    },
    "exoplanet_search_error": {
        "en": "The exoplanet search failed.",
        "ja": "系外惑星検索に失敗しました。",
        "ko": "외계행성 검색에 실패했습니다.",
        "th": "การค้นหาดาวเคราะห์นอกระบบล้มเหลว",
    },
    "exoplanet_no_results": {
        "en": "No planets matched the selected filters.",
        "ja": "選択した条件に一致する惑星はありませんでした。",
        "ko": "선택한 조건과 일치하는 행성이 없습니다.",
        "th": "ไม่พบดาวเคราะห์ที่ตรงกับตัวกรองที่เลือก",
    },
    "exoplanet_results": {
        "en": "Search results",
        "ja": "検索結果",
        "ko": "검색 결과",
        "th": "ผลการค้นหา",
    },
    "exoplanet_planet_count": {
        "en": "Returned planets",
        "ja": "取得した惑星",
        "ko": "반환된 행성",
        "th": "ดาวเคราะห์ที่พบ",
    },
    "exoplanet_transiting_count": {
        "en": "Transiting planets",
        "ja": "トランジット惑星",
        "ko": "트랜싯 행성",
        "th": "ดาวเคราะห์ทรานซิต",
    },
    "exoplanet_temperate_candidates": {
        "en": "Temperate terrestrial candidates",
        "ja": "温和な地球型候補",
        "ko": "온화한 지구형 후보",
        "th": "ผู้สมัครดาวเคราะห์หินเขตอบอุ่น",
    },
    "exoplanet_median_radius": {
        "en": "Median radius",
        "ja": "半径の中央値",
        "ko": "반지름 중앙값",
        "th": "รัศมีมัธยฐาน",
    },
    "exoplanet_nearest_planet": {
        "en": "Nearest returned planet",
        "ja": "取得結果で最も近い惑星",
        "ko": "검색 결과에서 가장 가까운 행성",
        "th": "ดาวเคราะห์ที่ใกล้ที่สุดในผลลัพธ์",
    },
    "exoplanet_smallest_planet": {
        "en": "Smallest returned planet",
        "ja": "取得結果で最小の惑星",
        "ko": "검색 결과에서 가장 작은 행성",
        "th": "ดาวเคราะห์ที่เล็กที่สุดในผลลัพธ์",
    },
    "exoplanet_radius_period_tab": {
        "en": "Radius and period",
        "ja": "半径と公転周期",
        "ko": "반지름과 공전 주기",
        "th": "รัศมีและคาบการโคจร",
    },
    "exoplanet_mass_radius_tab": {
        "en": "Mass and radius",
        "ja": "質量と半径",
        "ko": "질량과 반지름",
        "th": "มวลและรัศมี",
    },
    "exoplanet_climate_tab": {
        "en": "Temperature and insolation",
        "ja": "温度と日射量",
        "ko": "온도와 복사량",
        "th": "อุณหภูมิและพลังงานจากดาวฤกษ์",
    },
    "exoplanet_transit_tab": {
        "en": "Transit simulator",
        "ja": "トランジット・シミュレーター",
        "ko": "트랜싯 시뮬레이터",
        "th": "เครื่องจำลองทรานซิต",
    },
    "exoplanet_table_tab": {
        "en": "Planet table",
        "ja": "惑星テーブル",
        "ko": "행성 표",
        "th": "ตารางดาวเคราะห์",
    },
    "exoplanet_inspector_tab": {
        "en": "Planet inspector",
        "ja": "惑星インスペクター",
        "ko": "행성 검사기",
        "th": "เครื่องมือตรวจสอบดาวเคราะห์",
    },
    "exoplanet_export_tab": {
        "en": "Export and query",
        "ja": "エクスポートとクエリ",
        "ko": "내보내기와 쿼리",
        "th": "ส่งออกและคำสั่งค้นหา",
    },
    "exoplanet_radius_period_title": {
        "en": "Planet radius versus orbital period",
        "ja": "惑星半径と公転周期",
        "ko": "행성 반지름과 공전 주기",
        "th": "รัศมีดาวเคราะห์เทียบกับคาบการโคจร",
    },
    "exoplanet_mass_radius_title": {
        "en": "Planet mass versus radius",
        "ja": "惑星質量と半径",
        "ko": "행성 질량과 반지름",
        "th": "มวลดาวเคราะห์เทียบกับรัศมี",
    },
    "exoplanet_climate_title": {
        "en": "Equilibrium temperature and insolation",
        "ja": "平衡温度と日射量",
        "ko": "평형 온도와 복사량",
        "th": "อุณหภูมิสมดุลและพลังงานจากดาวฤกษ์",
    },
    "exoplanet_transit_title": {
        "en": "Educational transit light curve",
        "ja": "教育用トランジット光度曲線",
        "ko": "교육용 트랜싯 광도 곡선",
        "th": "กราฟแสงทรานซิตเพื่อการศึกษา",
    },
    "exoplanet_orbital_period": {
        "en": "Orbital period (days)",
        "ja": "公転周期（日）",
        "ko": "공전 주기 (일)",
        "th": "คาบการโคจร (วัน)",
    },
    "exoplanet_radius": {
        "en": "Planet radius (Earth radii)",
        "ja": "惑星半径（地球半径）",
        "ko": "행성 반지름 (지구 반지름)",
        "th": "รัศมีดาวเคราะห์ (รัศมีโลก)",
    },
    "exoplanet_mass": {
        "en": "Planet mass (Earth masses)",
        "ja": "惑星質量（地球質量）",
        "ko": "행성 질량 (지구 질량)",
        "th": "มวลดาวเคราะห์ (มวลโลก)",
    },
    "exoplanet_equilibrium_temperature": {
        "en": "Equilibrium temperature (K)",
        "ja": "平衡温度（K）",
        "ko": "평형 온도 (K)",
        "th": "อุณหภูมิสมดุล (K)",
    },
    "exoplanet_insolation": {
        "en": "Insolation (Earth units)",
        "ja": "日射量（地球比）",
        "ko": "복사량 (지구 기준)",
        "th": "พลังงานจากดาวฤกษ์ (เท่าของโลก)",
    },
    "exoplanet_transit_time": {
        "en": "Time from mid-transit (hours)",
        "ja": "トランジット中心からの時間（時間）",
        "ko": "트랜싯 중심으로부터의 시간 (시간)",
        "th": "เวลาจากกึ่งกลางทรานซิต (ชั่วโมง)",
    },
    "exoplanet_relative_flux": {
        "en": "Relative stellar flux",
        "ja": "恒星の相対光度",
        "ko": "별의 상대 광도",
        "th": "ฟลักซ์สัมพัทธ์ของดาวฤกษ์",
    },
    "exoplanet_simulated_transit": {
        "en": "Simulated transit",
        "ja": "シミュレーションしたトランジット",
        "ko": "시뮬레이션된 트랜싯",
        "th": "ทรานซิตจำลอง",
    },
    "exoplanet_no_chart_data": {
        "en": "The returned planets do not contain enough data for this chart.",
        "ja": "このグラフを作成するためのデータが不足しています。",
        "ko": "이 차트를 만들기에 충분한 데이터가 없습니다.",
        "th": "ข้อมูลของดาวเคราะห์ไม่เพียงพอสำหรับกราฟนี้",
    },
    "exoplanet_status_temperate_terrestrial": {
        "en": "Temperate terrestrial candidate",
        "ja": "温和な地球型候補",
        "ko": "온화한 지구형 후보",
        "th": "ผู้สมัครดาวเคราะห์หินเขตอบอุ่น",
    },
    "exoplanet_status_temperate_non_terrestrial": {
        "en": "Temperate, non-terrestrial size",
        "ja": "温和だが地球型サイズではない",
        "ko": "온화하지만 지구형 크기가 아님",
        "th": "อุณหภูมิพอเหมาะแต่ขนาดไม่คล้ายโลก",
    },
    "exoplanet_status_outside_temperate": {
        "en": "Outside the temperate screen",
        "ja": "温和条件の範囲外",
        "ko": "온화한 조건 범위 밖",
        "th": "อยู่นอกช่วงเขตอบอุ่น",
    },
    "exoplanet_status_insufficient_data": {
        "en": "Insufficient climate data",
        "ja": "気候データ不足",
        "ko": "기후 데이터 부족",
        "th": "ข้อมูลสภาพภูมิอากาศไม่เพียงพอ",
    },
    "exoplanet_select_planet": {
        "en": "Select a planet",
        "ja": "惑星を選択",
        "ko": "행성 선택",
        "th": "เลือกดาวเคราะห์",
    },
    "exoplanet_transit_depth": {
        "en": "Transit depth (ppm)",
        "ja": "トランジット深度（ppm）",
        "ko": "트랜싯 깊이 (ppm)",
        "th": "ความลึกของทรานซิต (ppm)",
    },
    "exoplanet_transit_duration": {
        "en": "Transit duration (hours)",
        "ja": "トランジット継続時間（時間）",
        "ko": "트랜싯 지속 시간 (시간)",
        "th": "ระยะเวลาทรานซิต (ชั่วโมง)",
    },
    "exoplanet_ingress_fraction": {
        "en": "Ingress fraction",
        "ja": "進入時間の割合",
        "ko": "진입 구간 비율",
        "th": "สัดส่วนช่วงเริ่มทรานซิต",
    },
    "exoplanet_simulator_note": {
        "en": (
            "This trapezoidal model is an educational approximation. "
            "It does not include limb darkening or instrumental noise."
        ),
        "ja": ("この台形モデルは教育用の近似です。周辺減光や観測機器のノイズは含みません。"),
        "ko": (
            "이 사다리꼴 모델은 교육용 근사입니다. 주연 감광이나 기기 잡음은 포함하지 않습니다."
        ),
        "th": (
            "แบบจำลองทรงสี่เหลี่ยมคางหมูนี้เป็นค่าประมาณเพื่อการศึกษา "
            "และไม่รวมผลมืดบริเวณขอบดาวหรือสัญญาณรบกวนจากเครื่องมือ"
        ),
    },
    "exoplanet_planet_name": {
        "en": "Planet",
        "ja": "惑星",
        "ko": "행성",
        "th": "ดาวเคราะห์",
    },
    "exoplanet_host_name": {
        "en": "Host star",
        "ja": "主星",
        "ko": "모항성",
        "th": "ดาวฤกษ์แม่",
    },
    "exoplanet_discovery_year": {
        "en": "Discovery year",
        "ja": "発見年",
        "ko": "발견 연도",
        "th": "ปีที่ค้นพบ",
    },
    "exoplanet_distance": {
        "en": "Distance (pc)",
        "ja": "距離（pc）",
        "ko": "거리 (pc)",
        "th": "ระยะทาง (pc)",
    },
    "exoplanet_semi_major_axis": {
        "en": "Semi-major axis (AU)",
        "ja": "軌道長半径（AU）",
        "ko": "긴반지름 (AU)",
        "th": "กึ่งแกนเอก (AU)",
    },
    "exoplanet_density": {
        "en": "Estimated density (g/cm³)",
        "ja": "推定密度（g/cm³）",
        "ko": "추정 밀도 (g/cm³)",
        "th": "ความหนาแน่นโดยประมาณ (g/cm³)",
    },
    "exoplanet_transit_probability": {
        "en": "Estimated transit probability",
        "ja": "推定トランジット確率",
        "ko": "추정 트랜싯 확률",
        "th": "ความน่าจะเป็นของทรานซิตโดยประมาณ",
    },
    "exoplanet_temperate_status": {
        "en": "Temperate screening status",
        "ja": "温和条件の判定",
        "ko": "온화 조건 판정",
        "th": "สถานะการคัดกรองเขตอบอุ่น",
    },
    "exoplanet_download_csv": {
        "en": "Download planet catalogue CSV",
        "ja": "惑星カタログCSVをダウンロード",
        "ko": "행성 카탈로그 CSV 다운로드",
        "th": "ดาวน์โหลดแคตตาล็อกดาวเคราะห์ CSV",
    },
    "exoplanet_adql_query": {
        "en": "NASA archive ADQL query",
        "ja": "NASAアーカイブのADQLクエリ",
        "ko": "NASA 아카이브 ADQL 쿼리",
        "th": "คำสั่ง ADQL สำหรับคลังข้อมูล NASA",
    },
    "exoplanet_calculation_warning": {
        "en": (
            "Transit probability assumes simplified geometry. "
            "Density requires both a reported mass and radius."
        ),
        "ja": (
            "トランジット確率は単純化した幾何学を仮定しています。"
            "密度の計算には質量と半径の両方が必要です。"
        ),
        "ko": (
            "트랜싯 확률은 단순화된 기하학을 가정합니다. "
            "밀도 계산에는 질량과 반지름이 모두 필요합니다."
        ),
        "th": ("ความน่าจะเป็นของทรานซิตใช้เรขาคณิตแบบง่าย และการคำนวณความหนาแน่นต้องมีทั้งมวลและรัศมี"),
    },
}
