"""Four-language interface text for telescope simulation."""

from typing import Final

TELESCOPE_TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "telescope_section": {
        "en": "Telescope and eyepiece simulator",
        "ja": "望遠鏡・接眼レンズシミュレーター",
        "ko": "망원경 및 접안렌즈 시뮬레이터",
        "th": "เครื่องจำลองกล้องโทรทรรศน์และเลนส์ตา",
    },
    "telescope_explanation": {
        "en": (
            "Calculate magnification, exit pupil, true field, "
            "focal ratio, and approximate resolution."
        ),
        "ja": ("倍率、射出瞳径、実視界、F値、概算分解能を計算します。"),
        "ko": ("배율, 사출동공, 실제 시야, 초점비, 근사 분해능을 계산합니다."),
        "th": ("คำนวณกำลังขยาย รูม่านตาออก สนามมองจริง อัตราส่วนโฟกัส และกำลังแยกโดยประมาณ"),
    },
    "telescope_input_mode": {
        "en": "Specification mode",
        "ja": "仕様入力モード",
        "ko": "사양 입력 방식",
        "th": "รูปแบบการกำหนดข้อมูล",
    },
    "telescope_mode_preset": {
        "en": "Preset",
        "ja": "プリセット",
        "ko": "프리셋",
        "th": "ค่าที่ตั้งไว้",
    },
    "telescope_mode_custom": {
        "en": "Custom",
        "ja": "カスタム",
        "ko": "사용자 지정",
        "th": "กำหนดเอง",
    },
    "telescope_preset": {
        "en": "Telescope preset",
        "ja": "望遠鏡プリセット",
        "ko": "망원경 프리셋",
        "th": "กล้องโทรทรรศน์ที่ตั้งไว้",
    },
    "eyepiece_preset": {
        "en": "Eyepiece preset",
        "ja": "接眼レンズプリセット",
        "ko": "접안렌즈 프리셋",
        "th": "เลนส์ตาที่ตั้งไว้",
    },
    "telescope_aperture": {
        "en": "Aperture",
        "ja": "口径",
        "ko": "구경",
        "th": "เส้นผ่านศูนย์กลางหน้ากล้อง",
    },
    "telescope_focal_length": {
        "en": "Telescope focal length",
        "ja": "望遠鏡の焦点距離",
        "ko": "망원경 초점거리",
        "th": "ทางยาวโฟกัสของกล้อง",
    },
    "eyepiece_focal_length": {
        "en": "Eyepiece focal length",
        "ja": "接眼レンズの焦点距離",
        "ko": "접안렌즈 초점거리",
        "th": "ทางยาวโฟกัสของเลนส์ตา",
    },
    "apparent_field": {
        "en": "Apparent field of view",
        "ja": "見掛け視界",
        "ko": "겉보기 시야",
        "th": "สนามมองปรากฏ",
    },
    "barlow_factor": {
        "en": "Barlow factor",
        "ja": "バローレンズ倍率",
        "ko": "바로우 배율",
        "th": "อัตราขยายบาร์โลว์",
    },
    "reducer_factor": {
        "en": "Focal-reducer factor",
        "ja": "レデューサー倍率",
        "ko": "포컬 리듀서 배율",
        "th": "อัตราตัวลดโฟกัส",
    },
    "run_optical_simulation": {
        "en": "Run optical simulation",
        "ja": "光学シミュレーションを実行",
        "ko": "광학 시뮬레이션 실행",
        "th": "เริ่มการจำลองระบบแสง",
    },
    "optical_results": {
        "en": "Optical simulation results",
        "ja": "光学シミュレーション結果",
        "ko": "광학 시뮬레이션 결과",
        "th": "ผลการจำลองระบบแสง",
    },
    "native_focal_ratio": {
        "en": "Native focal ratio",
        "ja": "標準F値",
        "ko": "기본 초점비",
        "th": "อัตราส่วนโฟกัสดั้งเดิม",
    },
    "effective_focal_length": {
        "en": "Effective focal length",
        "ja": "有効焦点距離",
        "ko": "유효 초점거리",
        "th": "ทางยาวโฟกัสที่มีผล",
    },
    "effective_focal_ratio": {
        "en": "Effective focal ratio",
        "ja": "有効F値",
        "ko": "유효 초점비",
        "th": "อัตราส่วนโฟกัสที่มีผล",
    },
    "magnification": {
        "en": "Magnification",
        "ja": "倍率",
        "ko": "배율",
        "th": "กำลังขยาย",
    },
    "exit_pupil": {
        "en": "Exit pupil",
        "ja": "射出瞳径",
        "ko": "사출동공",
        "th": "รูม่านตาออก",
    },
    "true_field": {
        "en": "True field of view",
        "ja": "実視界",
        "ko": "실제 시야",
        "th": "สนามมองจริง",
    },
    "dawes_resolution": {
        "en": "Dawes resolution",
        "ja": "ドーズ限界",
        "ko": "도스 한계",
        "th": "ขีดจำกัดดอว์ส",
    },
    "rayleigh_resolution": {
        "en": "Rayleigh resolution",
        "ja": "レイリー限界",
        "ko": "레일리 한계",
        "th": "ขีดจำกัดเรย์ลี",
    },
    "minimum_useful_magnification": {
        "en": "Minimum useful magnification",
        "ja": "最低有効倍率",
        "ko": "최소 유효 배율",
        "th": "กำลังขยายใช้งานต่ำสุด",
    },
    "maximum_useful_magnification": {
        "en": "Maximum useful magnification",
        "ja": "最高有効倍率",
        "ko": "최대 유효 배율",
        "th": "กำลังขยายใช้งานสูงสุด",
    },
    "optical_status": {
        "en": "Optical status",
        "ja": "光学設定の評価",
        "ko": "광학 설정 평가",
        "th": "สถานะระบบแสง",
    },
    "optical_status_excessive_exit_pupil": {
        "en": "Exit pupil may be larger than the observer's eye pupil.",
        "ja": "射出瞳径が観測者の瞳孔より大きい可能性があります。",
        "ko": "사출동공이 관측자의 동공보다 클 수 있습니다.",
        "th": "รูม่านตาออกอาจใหญ่กว่ารูม่านตาของผู้สังเกต",
    },
    "optical_status_wide_field": {
        "en": "Wide-field and low-power configuration.",
        "ja": "広視野・低倍率向けの構成です。",
        "ko": "광시야 및 저배율 구성입니다.",
        "th": "เหมาะสำหรับสนามกว้างและกำลังขยายต่ำ",
    },
    "optical_status_general_purpose": {
        "en": "Balanced general-purpose configuration.",
        "ja": "バランスの良い汎用構成です。",
        "ko": "균형 잡힌 범용 구성입니다.",
        "th": "ระบบสมดุลสำหรับการใช้งานทั่วไป",
    },
    "optical_status_high_power": {
        "en": "High-power configuration for small targets.",
        "ja": "小さな天体向けの高倍率構成です。",
        "ko": "작은 대상을 위한 고배율 구성입니다.",
        "th": "ระบบกำลังขยายสูงสำหรับวัตถุขนาดเล็ก",
    },
    "optical_status_excessive_magnification": {
        "en": "Magnification is beyond the practical range.",
        "ja": "倍率が実用的な範囲を超えています。",
        "ko": "배율이 실용 범위를 초과합니다.",
        "th": "กำลังขยายเกินช่วงที่ใช้งานได้จริง",
    },
    "eyepiece_comparison": {
        "en": "Eyepiece comparison",
        "ja": "接眼レンズ比較",
        "ko": "접안렌즈 비교",
        "th": "เปรียบเทียบเลนส์ตา",
    },
    "fov_visualizer": {
        "en": "Field-of-view visualizer",
        "ja": "視野シミュレーター",
        "ko": "시야 시각화",
        "th": "ภาพจำลองสนามมอง",
    },
    "angular_target": {
        "en": "Angular-size target",
        "ja": "角直径比較天体",
        "ko": "각크기 비교 대상",
        "th": "วัตถุเปรียบเทียบขนาดเชิงมุม",
    },
    "field_fit": {
        "en": "Target fit",
        "ja": "視野への収まり",
        "ko": "시야 적합도",
        "th": "ความพอดีในสนามมอง",
    },
    "field_fit_comfortable": {
        "en": "The complete target fits comfortably.",
        "ja": "天体全体が十分な余裕を持って視野に収まります。",
        "ko": "대상 전체가 여유 있게 시야에 들어옵니다.",
        "th": "วัตถุทั้งหมดอยู่ในสนามมองอย่างสบาย",
    },
    "field_fit_tight": {
        "en": "The target fits, but framing is tight.",
        "ja": "視野には収まりますが、余裕が小さいです。",
        "ko": "시야에 들어오지만 여유가 적습니다.",
        "th": "วัตถุอยู่ในสนามมองแต่มีพื้นที่เหลือน้อย",
    },
    "field_fit_too_large": {
        "en": "The complete target does not fit in the field.",
        "ja": "天体全体は視野に収まりません。",
        "ko": "대상 전체가 시야에 들어오지 않습니다.",
        "th": "วัตถุทั้งหมดไม่สามารถอยู่ในสนามมองได้",
    },
    "fov_chart_title": {
        "en": "Telescope field and target angular size",
        "ja": "望遠鏡視野と天体の角サイズ",
        "ko": "망원경 시야와 대상 각크기",
        "th": "สนามมองของกล้องและขนาดเชิงมุมของวัตถุ",
    },
    "angular_distance": {
        "en": "Angular distance",
        "ja": "角距離",
        "ko": "각거리",
        "th": "ระยะเชิงมุม",
    },
    "target_angular_size": {
        "en": "Target angular size",
        "ja": "天体の角サイズ",
        "ko": "대상 각크기",
        "th": "ขนาดเชิงมุมของวัตถุ",
    },
    "target_moon": {
        "en": "Moon",
        "ja": "月",
        "ko": "달",
        "th": "ดวงจันทร์",
    },
    "target_m31": {
        "en": "Andromeda Galaxy",
        "ja": "アンドロメダ銀河",
        "ko": "안드로메다 은하",
        "th": "ดาราจักรแอนดรอเมดา",
    },
    "target_pleiades": {
        "en": "Pleiades",
        "ja": "プレアデス星団",
        "ko": "플레이아데스 성단",
        "th": "กระจุกดาวลูกไก่",
    },
    "target_orion_nebula": {
        "en": "Orion Nebula",
        "ja": "オリオン大星雲",
        "ko": "오리온 성운",
        "th": "เนบิวลานายพราน",
    },
    "telescope_preset_small_refractor": {
        "en": "70 mm f/10 refractor",
        "ja": "70 mm F10 屈折望遠鏡",
        "ko": "70 mm F10 굴절망원경",
        "th": "กล้องหักเหแสง 70 mm f/10",
    },
    "telescope_preset_medium_refractor": {
        "en": "100 mm f/9 refractor",
        "ja": "100 mm F9 屈折望遠鏡",
        "ko": "100 mm F9 굴절망원경",
        "th": "กล้องหักเหแสง 100 mm f/9",
    },
    "telescope_preset_compact_reflector": {
        "en": "130 mm f/5 reflector",
        "ja": "130 mm F5 反射望遠鏡",
        "ko": "130 mm F5 반사망원경",
        "th": "กล้องสะท้อนแสง 130 mm f/5",
    },
    "telescope_preset_large_reflector": {
        "en": "200 mm f/5 reflector",
        "ja": "200 mm F5 反射望遠鏡",
        "ko": "200 mm F5 반사망원경",
        "th": "กล้องสะท้อนแสง 200 mm f/5",
    },
    "telescope_preset_long_focus_cassegrain": {
        "en": "203 mm f/10 Cassegrain",
        "ja": "203 mm F10 カセグレン",
        "ko": "203 mm F10 카세그레인",
        "th": "กล้องแคสสิเกรน 203 mm f/10",
    },
    "eyepiece_preset_plossl_32": {
        "en": "32 mm Plössl, 50°",
        "ja": "32 mm プルーセル、50°",
        "ko": "32 mm 플뢰슬, 50°",
        "th": "Plössl 32 mm, 50°",
    },
    "eyepiece_preset_plossl_25": {
        "en": "25 mm Plössl, 50°",
        "ja": "25 mm プルーセル、50°",
        "ko": "25 mm 플뢰슬, 50°",
        "th": "Plössl 25 mm, 50°",
    },
    "eyepiece_preset_wide_24": {
        "en": "24 mm wide field, 68°",
        "ja": "24 mm 広視野、68°",
        "ko": "24 mm 광시야, 68°",
        "th": "เลนส์มุมกว้าง 24 mm, 68°",
    },
    "eyepiece_preset_plossl_10": {
        "en": "10 mm Plössl, 50°",
        "ja": "10 mm プルーセル、50°",
        "ko": "10 mm 플뢰슬, 50°",
        "th": "Plössl 10 mm, 50°",
    },
    "eyepiece_preset_planetary_6": {
        "en": "6 mm planetary, 60°",
        "ja": "6 mm 惑星用、60°",
        "ko": "6 mm 행성용, 60°",
        "th": "เลนส์ดาวเคราะห์ 6 mm, 60°",
    },
    "telescope_solar_warning": {
        "en": (
            "Never observe the Sun through a telescope without "
            "a correctly installed, certified front-aperture "
            "solar filter."
        ),
        "ja": (
            "適切に装着された認証済み対物太陽フィルターなしで、"
            "望遠鏡を通して太陽を観察しないでください。"
        ),
        "ko": ("올바르게 장착된 인증 전면 태양 필터 없이 망원경으로 태양을 관측하지 마세요."),
        "th": ("ห้ามสังเกตดวงอาทิตย์ผ่านกล้องโทรทรรศน์โดยไม่มีแผ่นกรองแสงอาทิตย์ด้านหน้าที่ได้รับการรับรอง"),
    },
    "telescope_note": {
        "en": (
            "The results are optical approximations. Seeing, "
            "collimation, optical quality, target brightness, "
            "and the observer's eyesight also affect performance."
        ),
        "ja": (
            "結果は光学的な概算です。シーイング、光軸調整、"
            "光学品質、天体の明るさ、観測者の視力も影響します。"
        ),
        "ko": (
            "결과는 광학적 근사값입니다. 시상, 광축 정렬, "
            "광학 품질, 대상 밝기, 관측자의 시력도 영향을 줍니다."
        ),
        "th": (
            "ผลลัพธ์เป็นค่าประมาณทางแสง สภาพบรรยากาศ "
            "การปรับแนว คุณภาพอุปกรณ์ ความสว่าง และสายตา"
            "ของผู้สังเกตล้วนมีผล"
        ),
    },
    "telescope_error": {
        "en": "Telescope-simulator error",
        "ja": "望遠鏡シミュレーターエラー",
        "ko": "망원경 시뮬레이터 오류",
        "th": "ข้อผิดพลาดของเครื่องจำลองกล้องโทรทรรศน์",
    },
}
