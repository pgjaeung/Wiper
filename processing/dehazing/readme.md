
# 🌫️ Dehazing 모듈 설명

이 폴더는 자율주행 영상 처리에서 안개(Haze)를 시뮬레이션하거나 제거(Dehaze)하는 데 사용되는 모듈들을 포함합니다. 각 모듈은 전처리 파이프라인 또는 실험 환경에서 단독 또는 연계하여 사용할 수 있습니다.

---

## 📁 구성 파일 설명

### 1. `haze_filter.py`
- **기능:** 이미지 또는 영상 프레임에 안개 효과를 적용합니다.
- **주요 함수:**
  - `apply_fog_tensor(image_tensor, beta=2.3, A=0.8, layers=100)`
    - 중심에서 멀어질수록 흐려지는 자연스러운 안개를 생성합니다.
    - `beta`: 안개 농도, `A`: 대기광 강도, `layers`: 누적 깊이 조절
- **사용 예:**

```python
from haze_filter import apply_fog_tensor
hazy = apply_fog_tensor(image_tensor, beta=2.3, A=0.8)
```

---

### 2. `dehaze_utils.py`
- **기능:** 학습된 디헤이징 모델(AOD-Net)을 이용하여 이미지를 원래 상태로 복원합니다.
- **주요 함수:**
  - `dehaze_image_tensor(model, image_tensor)` — 텐서 입력을 디헤이징하여 numpy로 반환
  - `dehaze_image_np(model, rgb_image_np, device)` — numpy 입력을 내부적으로 텐서로 변환 후 처리
- **사용 예:**

```python
from dehaze_utils import dehaze_image_np
clean_img = dehaze_image_np(model, rgb_img, device)
```

---

### 3. `net.py`
- **기능:** AOD-Net 모델 구조 정의
- **클래스:**
  - `dehaze_net`: PyTorch 기반 디헤이징 모델 구조
- **사용 예:**

```python
from net import dehaze_net
model = dehaze_net().to(device)
```

---

### 4. `roi_utils.py`
- **기능:** 중심 ROI(Region of Interest) 영역에 대해 재디헤이징 처리 및 블렌딩 지원
- **주요 함수:**
  - `create_alpha_mask(h, w)`: 중심이 진하고 외곽이 연한 원형 알파 마스크 생성
  - `apply_roi_blend(base_image, roi_image, x1, y1, alpha_mask)`: base 이미지의 지정 영역에 ROI를 부드럽게 합성
- **사용 예:**

```python
from roi_utils import create_alpha_mask, apply_roi_blend
alpha = create_alpha_mask(roi_h, roi_w)
blended = apply_roi_blend(base_img, roi_img, x1, y1, alpha)
```

---

### 5. `hazing_and_dehazing.py`
- **기능:** 전체 프레임 파이프라인 (안개 생성 → 디헤이징 → ROI 재처리 → 저장)
- **지원 인자:**
  - `--enable_haze`: 안개 적용 여부
  - `--enable_aod`: 전체 프레임 디헤이징 여부
  - `--enable_roi`: 중앙 영역 재디헤이징 여부
  - `--enable_blend`: ROI를 부드럽게 블렌딩할지 여부
  - `--haze_beta`, `--haze_A`, `--haze_layers`: 안개 강도 조절
- **사용 예:**

```bash
python hazing_and_dehazing.py \
  --enable_haze --enable_aod --enable_roi --enable_blend \
  --haze_beta 2.3 --haze_A 0.8 --haze_layers 100 \
  --output_suffix blended_test
```

---

### 6. `test_run.py`
- **기능:** `dehaze_net` 모델 테스트, hazing 함수 단위 확인 등을 위한 실험용 스크립트
- **비고:** 프레임 단위 테스트나 시각화 디버깅 용도로 자유롭게 수정하여 사용 가능

---

## 📦 기타 파일

| 파일명           | 설명                                       |
|------------------|--------------------------------------------|
| `dehazer.pth`    | 학습된 AOD-Net PyTorch 모델 가중치 파일     |
| `final_output.mp4` | 디헤이징 및 객체 인식 결과 비디오 예시 출력 파일 |

---

## 🧪 실행 흐름 요약

```text
[원본 프레임]
    ↓
[안개 적용 (선택)]
    ↓
[전체 디헤이징 (선택)]
    ↓
[ROI 재디헤이징 및 블렌딩 (선택)]
    ↓
[영상 저장]
```

---

## 🔗 연계 사용

- 이 모듈은 `processing/hazing_yolo_pipeline.py`에 연계하여 사용됩니다.
- Jetson 기반 실시간 영상 처리나 자율주행 인식 실험에 활용 가능합니다.
