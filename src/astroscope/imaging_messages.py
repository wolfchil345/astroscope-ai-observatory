"""Four-language text for the astrophotography planner."""

from typing import Final

IMAGING_TRANSLATIONS: Final[dict[str, dict[str, str]]] = {
    "imaging_section": {
        "en": "Astrophotography sensor and mosaic planner",
        "ja": "天体撮影センサー・モザイクプランナー",
        "ko": "천체사진 센서 및 모자이크 플래너",
        "th": "เครื่องวางแผนเซนเซอร์และภาพโมเสกดาราศาสตร์",
    },
    "imaging_explanation": {
        "en": (
            "Evaluate image scale, sensor field, atmospheric "
            "sampling, target framing, and mosaic requirements."
        ),
        "ja": (
            "画像スケール、センサー視野、大気サンプリング、天体の収まり、モザイク要件を評価します。"
        ),
        "ko": (
            "이미지 스케일, 센서 시야, 대기 샘플링, 대상 프레이밍과 모자이크 요구량을 평가합니다."
        ),
        "th": (
            "ประเมินสเกลภาพ สนามมองของเซนเซอร์ "
            "การสุ่มตัวอย่างตามสภาพบรรยากาศ "
            "การจัดกรอบวัตถุ และจำนวนภาพโมเสก"
        ),
    },
    "imaging_specification_mode": {
        "en": "Specification mode",
        "ja": "仕様入力モード",
        "ko": "사양 입력 방식",
        "th": "รูปแบบการกำหนดข้อมูล",
    },
    "imaging_mode_preset": {
        "en": "Preset",
        "ja": "プリセット",
        "ko": "프리셋",
        "th": "ค่าที่ตั้งไว้",
    },
    "imaging_mode_custom": {
        "en": "Custom",
        "ja": "カスタム",
        "ko": "사용자 지정",
        "th": "กำหนดเอง",
    },
    "camera_preset": {
        "en": "Camera preset",
        "ja": "カメラプリセット",
        "ko": "카메라 프리셋",
        "th": "กล้องที่ตั้งไว้",
    },
    "camera_preset_planetary_camera": {
        "en": "Small planetary camera",
        "ja": "小型惑星カメラ",
        "ko": "소형 행성 카메라",
        "th": "กล้องดาวเคราะห์ขนาดเล็ก",
    },
    "camera_preset_square_cooled_camera": {
        "en": "Square cooled camera",
        "ja": "正方形冷却カメラ",
        "ko": "정사각형 냉각 카메라",
        "th": "กล้องระบายความร้อนเซนเซอร์สี่เหลี่ยม",
    },
    "camera_preset_four_thirds_camera": {
        "en": "Four Thirds camera",
        "ja": "フォーサーズカメラ",
        "ko": "포서즈 카메라",
        "th": "กล้อง Four Thirds",
    },
    "camera_preset_aps_c_camera": {
        "en": "APS-C camera",
        "ja": "APS-Cカメラ",
        "ko": "APS-C 카메라",
        "th": "กล้อง APS-C",
    },
    "camera_preset_full_frame_camera": {
        "en": "Full-frame camera",
        "ja": "フルサイズカメラ",
        "ko": "풀프레임 카메라",
        "th": "กล้องฟูลเฟรม",
    },
    "sensor_width_pixels": {
        "en": "Sensor width",
        "ja": "センサー横画素数",
        "ko": "센서 가로 픽셀",
        "th": "จำนวนพิกเซลแนวนอน",
    },
    "sensor_height_pixels": {
        "en": "Sensor height",
        "ja": "センサー縦画素数",
        "ko": "센서 세로 픽셀",
        "th": "จำนวนพิกเซลแนวตั้ง",
    },
    "pixel_size_um": {
        "en": "Pixel size",
        "ja": "ピクセルサイズ",
        "ko": "픽셀 크기",
        "th": "ขนาดพิกเซล",
    },
    "seeing_arcseconds": {
        "en": "Atmospheric seeing",
        "ja": "大気シーイング",
        "ko": "대기 시상",
        "th": "ค่าซีอิงของบรรยากาศ",
    },
    "run_imaging_simulation": {
        "en": "Run imaging simulation",
        "ja": "撮影シミュレーションを実行",
        "ko": "촬영 시뮬레이션 실행",
        "th": "เริ่มการจำลองการถ่ายภาพ",
    },
    "imaging_results": {
        "en": "Imaging setup results",
        "ja": "撮影設定の結果",
        "ko": "촬영 설정 결과",
        "th": "ผลการตั้งค่าการถ่ายภาพ",
    },
    "image_scale": {
        "en": "Image scale",
        "ja": "画像スケール",
        "ko": "이미지 스케일",
        "th": "สเกลภาพ",
    },
    "sensor_dimensions": {
        "en": "Sensor dimensions",
        "ja": "センサー寸法",
        "ko": "센서 크기",
        "th": "ขนาดเซนเซอร์",
    },
    "camera_megapixels": {
        "en": "Camera resolution",
        "ja": "カメラ画素数",
        "ko": "카메라 해상도",
        "th": "ความละเอียดของกล้อง",
    },
    "sensor_field": {
        "en": "Sensor sky field",
        "ja": "センサーの空視野",
        "ko": "센서 하늘 시야",
        "th": "สนามท้องฟ้าของเซนเซอร์",
    },
    "field_width": {
        "en": "Field width",
        "ja": "視野幅",
        "ko": "시야 너비",
        "th": "ความกว้างสนามมอง",
    },
    "field_height": {
        "en": "Field height",
        "ja": "視野高さ",
        "ko": "시야 높이",
        "th": "ความสูงสนามมอง",
    },
    "field_diagonal": {
        "en": "Field diagonal",
        "ja": "視野対角",
        "ko": "시야 대각선",
        "th": "เส้นทแยงมุมสนามมอง",
    },
    "seeing_disk_pixels": {
        "en": "Seeing disk sampling",
        "ja": "シーイング像のサンプリング",
        "ko": "시상 원반 샘플링",
        "th": "จำนวนพิกเซลต่อดิสก์ซีอิง",
    },
    "dawes_sampling_pixels": {
        "en": "Dawes-resolution sampling",
        "ja": "ドーズ限界のサンプリング",
        "ko": "도스 한계 샘플링",
        "th": "การสุ่มตัวอย่างขีดจำกัดดอว์ส",
    },
    "ideal_image_scale": {
        "en": "Suggested image-scale range",
        "ja": "推奨画像スケール範囲",
        "ko": "권장 이미지 스케일 범위",
        "th": "ช่วงสเกลภาพที่แนะนำ",
    },
    "sampling_status": {
        "en": "Sampling assessment",
        "ja": "サンプリング評価",
        "ko": "샘플링 평가",
        "th": "การประเมินการสุ่มตัวอย่าง",
    },
    "sampling_status_oversampled": {
        "en": (
            "Oversampled: the image scale is finer than normally required by the selected seeing."
        ),
        "ja": (
            "オーバーサンプリングです。選択したシーイングに"
            "対して画像スケールが細かすぎる可能性があります。"
        ),
        "ko": ("오버샘플링입니다. 선택한 시상에 비해 이미지 스케일이 지나치게 세밀할 수 있습니다."),
        "th": ("สุ่มตัวอย่างมากเกินไป สเกลภาพละเอียดกว่าที่จำเป็นสำหรับค่าซีอิงที่เลือก"),
    },
    "sampling_status_well_sampled": {
        "en": (
            "Well sampled: the image scale is within the suggested range for the selected seeing."
        ),
        "ja": ("適切なサンプリングです。画像スケールは選択したシーイングの推奨範囲内です。"),
        "ko": ("적절한 샘플링입니다. 이미지 스케일이 선택한 시상의 권장 범위에 있습니다."),
        "th": ("สุ่มตัวอย่างเหมาะสม สเกลภาพอยู่ในช่วงที่แนะนำสำหรับค่าซีอิงที่เลือก"),
    },
    "sampling_status_undersampled": {
        "en": ("Undersampled: fine detail may occupy too few pixels."),
        "ja": ("アンダーサンプリングです。細部を構成する画素数が少ない可能性があります。"),
        "ko": ("언더샘플링입니다. 미세한 세부가 너무 적은 픽셀에 기록될 수 있습니다."),
        "th": ("สุ่มตัวอย่างไม่เพียงพอ รายละเอียดเล็กอาจใช้พิกเซลน้อยเกินไป"),
    },
    "sampling_status_severely_undersampled": {
        "en": ("Severely undersampled: the image scale is coarser than the selected seeing disk."),
        "ja": (
            "大幅なアンダーサンプリングです。画像スケールが"
            "選択したシーイング像より粗くなっています。"
        ),
        "ko": ("심한 언더샘플링입니다. 이미지 스케일이 선택한 시상 원반보다 거칩니다."),
        "th": ("สุ่มตัวอย่างไม่เพียงพออย่างมาก สเกลภาพหยาบกว่าดิสก์ซีอิงที่เลือก"),
    },
    "camera_comparison": {
        "en": "Camera comparison",
        "ja": "カメラ比較",
        "ko": "카메라 비교",
        "th": "เปรียบเทียบกล้อง",
    },
    "target_framing": {
        "en": "Target framing and mosaic",
        "ja": "天体のフレーミングとモザイク",
        "ko": "대상 프레이밍 및 모자이크",
        "th": "การจัดกรอบวัตถุและภาพโมเสก",
    },
    "imaging_target": {
        "en": "Imaging target",
        "ja": "撮影対象",
        "ko": "촬영 대상",
        "th": "วัตถุสำหรับถ่ายภาพ",
    },
    "target_rosette_nebula": {
        "en": "Rosette Nebula",
        "ja": "ばら星雲",
        "ko": "장미 성운",
        "th": "เนบิวลากุหลาบ",
    },
    "target_lagoon_nebula": {
        "en": "Lagoon Nebula",
        "ja": "干潟星雲",
        "ko": "석호 성운",
        "th": "เนบิวลาลากูน",
    },
    "mosaic_overlap": {
        "en": "Mosaic overlap",
        "ja": "モザイク重複率",
        "ko": "모자이크 중첩률",
        "th": "พื้นที่ซ้อนทับของภาพโมเสก",
    },
    "sensor_rotation": {
        "en": "Sensor rotation",
        "ja": "センサー回転角",
        "ko": "센서 회전",
        "th": "มุมหมุนเซนเซอร์",
    },
    "framing_status": {
        "en": "Framing assessment",
        "ja": "フレーミング評価",
        "ko": "프레이밍 평가",
        "th": "การประเมินการจัดกรอบ",
    },
    "framing_status_comfortable": {
        "en": "The target fits comfortably inside one frame.",
        "ja": "天体は1枚のフレームに余裕を持って収まります。",
        "ko": "대상이 한 프레임 안에 여유 있게 들어옵니다.",
        "th": "วัตถุอยู่ภายในเฟรมเดียวอย่างสบาย",
    },
    "framing_status_tight": {
        "en": "The target fits in one frame, but framing is tight.",
        "ja": "1枚に収まりますが、フレーミングの余裕は小さいです。",
        "ko": "한 프레임에 들어오지만 여유가 적습니다.",
        "th": "วัตถุอยู่ในเฟรมเดียวแต่มีพื้นที่เหลือน้อย",
    },
    "framing_status_mosaic_required": {
        "en": "The complete target requires a mosaic.",
        "ja": "天体全体を撮影するにはモザイクが必要です。",
        "ko": "대상 전체를 촬영하려면 모자이크가 필요합니다.",
        "th": "ต้องใช้ภาพโมเสกเพื่อถ่ายวัตถุทั้งหมด",
    },
    "horizontal_panels": {
        "en": "Horizontal panels",
        "ja": "横方向パネル数",
        "ko": "가로 패널 수",
        "th": "จำนวนแผงแนวนอน",
    },
    "vertical_panels": {
        "en": "Vertical panels",
        "ja": "縦方向パネル数",
        "ko": "세로 패널 수",
        "th": "จำนวนแผงแนวตั้ง",
    },
    "total_panels": {
        "en": "Total panels",
        "ja": "総パネル数",
        "ko": "전체 패널 수",
        "th": "จำนวนแผงทั้งหมด",
    },
    "width_fill": {
        "en": "Width fill",
        "ja": "横方向占有率",
        "ko": "가로 점유율",
        "th": "สัดส่วนความกว้าง",
    },
    "height_fill": {
        "en": "Height fill",
        "ja": "縦方向占有率",
        "ko": "세로 점유율",
        "th": "สัดส่วนความสูง",
    },
    "covered_field": {
        "en": "Mosaic coverage",
        "ja": "モザイク撮影範囲",
        "ko": "모자이크 촬영 범위",
        "th": "พื้นที่ครอบคลุมของโมเสก",
    },
    "imaging_frame_title": {
        "en": "Sensor frame, target, and mosaic layout",
        "ja": "センサー視野・天体・モザイク配置",
        "ko": "센서 프레임, 대상 및 모자이크 배치",
        "th": "เฟรมเซนเซอร์ วัตถุ และรูปแบบโมเสก",
    },
    "horizontal_angle": {
        "en": "Horizontal angular distance",
        "ja": "横方向角距離",
        "ko": "가로 각거리",
        "th": "ระยะเชิงมุมแนวนอน",
    },
    "vertical_angle": {
        "en": "Vertical angular distance",
        "ja": "縦方向角距離",
        "ko": "세로 각거리",
        "th": "ระยะเชิงมุมแนวตั้ง",
    },
    "sensor_panel": {
        "en": "Sensor panel",
        "ja": "センサーパネル",
        "ko": "센서 패널",
        "th": "แผงเซนเซอร์",
    },
    "mosaic_layout": {
        "en": "Mosaic layout",
        "ja": "モザイク配置",
        "ko": "모자이크 배치",
        "th": "รูปแบบโมเสก",
    },
    "imaging_note": {
        "en": (
            "The framing model uses approximate angular target "
            "sizes. Sensor rotation is visualized geometrically, "
            "while panel counts use axis-aligned field dimensions."
        ),
        "ja": (
            "フレーミングには概算の天体角サイズを使用します。"
            "センサー回転は図に反映されますが、パネル数は回転前の"
            "視野寸法から計算します。"
        ),
        "ko": (
            "프레이밍은 근사 대상 각크기를 사용합니다. 센서 "
            "회전은 그림에 반영되지만 패널 수는 회전 전 시야 "
            "크기로 계산합니다."
        ),
        "th": (
            "การจัดกรอบใช้ขนาดเชิงมุมโดยประมาณ มุมหมุนเซนเซอร์"
            "แสดงในภาพ แต่จำนวนแผงคำนวณจากขนาดสนามมองก่อนหมุน"
        ),
    },
    "imaging_error": {
        "en": "Astrophotography-planner error",
        "ja": "天体撮影プランナーエラー",
        "ko": "천체사진 플래너 오류",
        "th": "ข้อผิดพลาดของเครื่องวางแผนถ่ายภาพดาราศาสตร์",
    },
}
