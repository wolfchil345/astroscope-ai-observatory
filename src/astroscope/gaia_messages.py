"""Four-language interface text for the Gaia explorer."""

from typing import Final

GAIA_TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "gaia_section": {
        "en": "Gaia DR3 stellar catalogue explorer",
        "ja": "Gaia DR3恒星カタログ探索",
        "ko": "Gaia DR3 항성 카탈로그 탐색기",
        "th": "เครื่องสำรวจแค็ตตาล็อกดาว Gaia DR3",
    },
    "gaia_explanation": {
        "en": (
            "Search Gaia DR3 around any sky coordinate and "
            "inspect astrometry, photometry, and stellar motion."
        ),
        "ja": ("任意の空座標周辺をGaia DR3で検索し、位置天文学、測光、恒星運動を調べます。"),
        "ko": (
            "임의의 하늘 좌표 주변을 Gaia DR3에서 검색하고 "
            "천체측량, 측광 및 항성 운동을 확인합니다."
        ),
        "th": ("ค้นหา Gaia DR3 รอบพิกัดท้องฟ้า และตรวจสอบตำแหน่ง ความสว่าง และการเคลื่อนที่"),
    },
    "gaia_ra": {
        "en": "Centre right ascension",
        "ja": "中心赤経",
        "ko": "중심 적경",
        "th": "ไรต์แอสเซนชันศูนย์กลาง",
    },
    "gaia_dec": {
        "en": "Centre declination",
        "ja": "中心赤緯",
        "ko": "중심 적위",
        "th": "เดคลิเนชันศูนย์กลาง",
    },
    "gaia_radius_arcmin": {
        "en": "Search radius",
        "ja": "検索半径",
        "ko": "검색 반경",
        "th": "รัศมีค้นหา",
    },
    "gaia_row_limit": {
        "en": "Maximum sources",
        "ja": "最大天体数",
        "ko": "최대 소스 수",
        "th": "จำนวนแหล่งข้อมูลสูงสุด",
    },
    "gaia_limit_g": {
        "en": "Apply G-magnitude limit",
        "ja": "G等級上限を使用",
        "ko": "G등급 제한 사용",
        "th": "ใช้ขีดจำกัดโชติมาตร G",
    },
    "gaia_max_g": {
        "en": "Maximum G magnitude",
        "ja": "最大G等級",
        "ko": "최대 G등급",
        "th": "โชติมาตร G สูงสุด",
    },
    "gaia_filter_snr": {
        "en": "Apply parallax-quality filter",
        "ja": "年周視差品質フィルターを使用",
        "ko": "시차 품질 필터 사용",
        "th": "ใช้ตัวกรองคุณภาพพารัลแลกซ์",
    },
    "gaia_min_snr": {
        "en": "Minimum parallax S/N",
        "ja": "最小年周視差S/N",
        "ko": "최소 시차 S/N",
        "th": "S/N พารัลแลกซ์ต่ำสุด",
    },
    "gaia_timeout": {
        "en": "Request timeout",
        "ja": "通信タイムアウト",
        "ko": "요청 제한 시간",
        "th": "เวลาหมดอายุของคำขอ",
    },
    "gaia_search": {
        "en": "Search Gaia DR3",
        "ja": "Gaia DR3を検索",
        "ko": "Gaia DR3 검색",
        "th": "ค้นหา Gaia DR3",
    },
    "gaia_searching": {
        "en": "Querying the Gaia Archive...",
        "ja": "Gaia Archiveを検索しています...",
        "ko": "Gaia Archive를 검색하는 중...",
        "th": "กำลังค้นหา Gaia Archive...",
    },
    "gaia_error": {
        "en": "Gaia catalogue error",
        "ja": "Gaiaカタログエラー",
        "ko": "Gaia 카탈로그 오류",
        "th": "ข้อผิดพลาดแค็ตตาล็อก Gaia",
    },
    "gaia_no_sources": {
        "en": "No Gaia sources matched the selected filters.",
        "ja": "選択条件に一致するGaia天体はありません。",
        "ko": "선택한 조건과 일치하는 Gaia 소스가 없습니다.",
        "th": "ไม่พบแหล่งข้อมูล Gaia ที่ตรงกับตัวกรอง",
    },
    "gaia_results": {
        "en": "Gaia search results",
        "ja": "Gaia検索結果",
        "ko": "Gaia 검색 결과",
        "th": "ผลการค้นหา Gaia",
    },
    "gaia_source_count": {
        "en": "Returned sources",
        "ja": "取得天体数",
        "ko": "반환된 소스",
        "th": "แหล่งข้อมูลที่พบ",
    },
    "gaia_median_g": {
        "en": "Median G magnitude",
        "ja": "G等級中央値",
        "ko": "G등급 중앙값",
        "th": "ค่ามัธยฐานโชติมาตร G",
    },
    "gaia_closest_center": {
        "en": "Closest to search centre",
        "ja": "検索中心に最も近い天体",
        "ko": "검색 중심에 가장 가까운 소스",
        "th": "ใกล้ศูนย์กลางค้นหาที่สุด",
    },
    "gaia_brightest": {
        "en": "Brightest returned source",
        "ja": "取得天体中で最も明るい天体",
        "ko": "반환된 소스 중 가장 밝은 소스",
        "th": "แหล่งข้อมูลที่สว่างที่สุด",
    },
    "gaia_local_sky": {
        "en": "Local Gaia sky map",
        "ja": "Gaia局所星図",
        "ko": "Gaia 국부 하늘 지도",
        "th": "แผนที่ท้องฟ้า Gaia บริเวณใกล้เคียง",
    },
    "gaia_hr_diagram": {
        "en": "Colour–magnitude diagram",
        "ja": "色等級図",
        "ko": "색–등급도",
        "th": "แผนภาพสี–โชติมาตร",
    },
    "gaia_proper_motion": {
        "en": "Proper-motion vectors",
        "ja": "固有運動ベクトル",
        "ko": "고유운동 벡터",
        "th": "เวกเตอร์การเคลื่อนที่เฉพาะ",
    },
    "gaia_catalog_table": {
        "en": "Gaia source table",
        "ja": "Gaia天体表",
        "ko": "Gaia 소스 표",
        "th": "ตารางแหล่งข้อมูล Gaia",
    },
    "gaia_source_details": {
        "en": "Source inspector",
        "ja": "天体詳細",
        "ko": "소스 상세 정보",
        "th": "รายละเอียดแหล่งข้อมูล",
    },
    "gaia_select_source": {
        "en": "Select a Gaia source",
        "ja": "Gaia天体を選択",
        "ko": "Gaia 소스 선택",
        "th": "เลือกแหล่งข้อมูล Gaia",
    },
    "gaia_designation": {
        "en": "Designation",
        "ja": "天体識別名",
        "ko": "명칭",
        "th": "ชื่อระบุ",
    },
    "gaia_source_id": {
        "en": "Source ID",
        "ja": "ソースID",
        "ko": "소스 ID",
        "th": "รหัสแหล่งข้อมูล",
    },
    "gaia_angular_distance": {
        "en": "Angular distance",
        "ja": "角距離",
        "ko": "각거리",
        "th": "ระยะเชิงมุม",
    },
    "gaia_parallax": {
        "en": "Parallax",
        "ja": "年周視差",
        "ko": "시차",
        "th": "พารัลแลกซ์",
    },
    "gaia_parallax_snr": {
        "en": "Parallax S/N",
        "ja": "年周視差S/N",
        "ko": "시차 S/N",
        "th": "S/N พารัลแลกซ์",
    },
    "gaia_pmra": {
        "en": "Proper motion in RA",
        "ja": "赤経方向固有運動",
        "ko": "적경 방향 고유운동",
        "th": "การเคลื่อนที่เฉพาะใน RA",
    },
    "gaia_pmdec": {
        "en": "Proper motion in Dec",
        "ja": "赤緯方向固有運動",
        "ko": "적위 방향 고유운동",
        "th": "การเคลื่อนที่เฉพาะใน Dec",
    },
    "gaia_total_pm": {
        "en": "Total proper motion",
        "ja": "合成固有運動",
        "ko": "전체 고유운동",
        "th": "การเคลื่อนที่เฉพาะรวม",
    },
    "gaia_g_mag": {
        "en": "G magnitude",
        "ja": "G等級",
        "ko": "G등급",
        "th": "โชติมาตร G",
    },
    "gaia_bp_mag": {
        "en": "BP magnitude",
        "ja": "BP等級",
        "ko": "BP등급",
        "th": "โชติมาตร BP",
    },
    "gaia_rp_mag": {
        "en": "RP magnitude",
        "ja": "RP等級",
        "ko": "RP등급",
        "th": "โชติมาตร RP",
    },
    "gaia_bp_rp": {
        "en": "BP−RP colour",
        "ja": "BP−RP色指数",
        "ko": "BP−RP 색지수",
        "th": "ดัชนีสี BP−RP",
    },
    "gaia_radial_velocity": {
        "en": "Radial velocity",
        "ja": "視線速度",
        "ko": "시선속도",
        "th": "ความเร็วแนวรัศมี",
    },
    "gaia_temperature": {
        "en": "Effective temperature",
        "ja": "有効温度",
        "ko": "유효온도",
        "th": "อุณหภูมิยังผล",
    },
    "gaia_naive_distance": {
        "en": "Naive parallax distance",
        "ja": "単純年周視差距離",
        "ko": "단순 시차 거리",
        "th": "ระยะทางจากพารัลแลกซ์แบบง่าย",
    },
    "gaia_absolute_g": {
        "en": "Estimated absolute G magnitude",
        "ja": "推定絶対G等級",
        "ko": "추정 절대 G등급",
        "th": "โชติมาตรสัมบูรณ์ G โดยประมาณ",
    },
    "gaia_download_csv": {
        "en": "Download Gaia CSV",
        "ja": "Gaia CSVをダウンロード",
        "ko": "Gaia CSV 다운로드",
        "th": "ดาวน์โหลด Gaia CSV",
    },
    "gaia_adql_preview": {
        "en": "ADQL query preview",
        "ja": "ADQLクエリ表示",
        "ko": "ADQL 쿼리 미리보기",
        "th": "ตัวอย่างคำสั่ง ADQL",
    },
    "gaia_distance_warning": {
        "en": (
            "Distances and absolute magnitudes shown here use "
            "simple positive-parallax inversion. Treat them as "
            "educational estimates, especially for low-S/N data."
        ),
        "ja": (
            "表示距離と絶対等級は正の年周視差を単純に逆数化した"
            "教育目的の概算です。低S/Nデータでは特に注意してください。"
        ),
        "ko": (
            "표시된 거리와 절대등급은 양의 시차를 단순 역산한 "
            "교육용 추정값입니다. 낮은 S/N 자료는 특히 주의하세요."
        ),
        "th": ("ระยะทางและโชติมาตรสัมบูรณ์คำนวณจากการกลับค่าพารัลแลกซ์บวกแบบง่าย ควรใช้เพื่อการศึกษาเท่านั้น"),
    },
    "gaia_attribution": {
        "en": "Catalogue data: ESA/Gaia/DPAC.",
        "ja": "カタログデータ: ESA/Gaia/DPAC。",
        "ko": "카탈로그 데이터: ESA/Gaia/DPAC.",
        "th": "ข้อมูลแค็ตตาล็อก: ESA/Gaia/DPAC",
    },
    "gaia_ra_offset": {
        "en": "RA offset from centre (degrees)",
        "ja": "中心からの赤経差（度）",
        "ko": "중심으로부터의 적경 차이(도)",
        "th": "ส่วนต่าง RA จากศูนย์กลาง (องศา)",
    },
    "gaia_dec_offset": {
        "en": "Dec offset from centre (degrees)",
        "ja": "中心からの赤緯差（度）",
        "ko": "중심으로부터의 적위 차이(도)",
        "th": "ส่วนต่าง Dec จากศูนย์กลาง (องศา)",
    },
    "gaia_no_chart_data": {
        "en": "No sources contain the values required for this chart.",
        "ja": "この図に必要な値を持つ天体がありません。",
        "ko": "이 차트에 필요한 값을 가진 소스가 없습니다.",
        "th": "ไม่มีแหล่งข้อมูลที่มีค่าครบสำหรับแผนภาพนี้",
    },
    "gaia_missing_color": {
        "en": "Sources without BP−RP",
        "ja": "BP−RP未取得天体",
        "ko": "BP−RP가 없는 소스",
        "th": "แหล่งข้อมูลที่ไม่มี BP−RP",
    },
}
