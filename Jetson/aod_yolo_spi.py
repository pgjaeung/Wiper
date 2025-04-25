import torch
import cv2
import time
import os
import numpy as np
import spidev  # SPI 통신 모듈
from aod_net import AODNet, prune_model, remove_pruning

# === AODNet 모델 로드 ===
aod_model = AODNet().cuda()
checkpoint = torch.load("dehazer.pth")
new_checkpoint = {"aod_block." + k: v for k, v in checkpoint.items()}
aod_model.load_state_dict(new_checkpoint)
aod_model.eval()

prune_model(aod_model, amount=0.3)
remove_pruning(aod_model)

# === YOLOv5 모델 로드 ===
model = torch.hub.load('ultralytics/yolov5', 'yolov5s', device='cuda:0', force_reload=True)

# === GStreamer 카메라 파이프라인 설정 ===
gst_pipeline = (
    "nvarguscamerasrc ! "
    "video/x-raw(memory:NVMM), width=640, height=480, format=NV12, framerate=10/1 ! "
    "nvvidconv flip-method=2 ! "
    "video/x-raw, format=BGRx ! "
    "videoconvert ! "
    "video/x-raw, format=BGR ! appsink drop=1"
)

# === SPI 초기화 ===
spi = spidev.SpiDev()
spi.open(0, 0)
spi.max_speed_hz = 1000000
spi.mode = 0b00

# === SPI 통신 함수 ===
def send_jetson_signals(human, red_light, car):
    tx_byte = (int(human) << 2) | (int(red_light) << 1) | int(car)
    rx_data = spi.xfer2([tx_byte])
    print(f"[Jetson] TX: {bin(tx_byte)} | RX: {rx_data}")

# === 디헤이징 함수 ===
def dehaze_frame(frame):
    img = torch.from_numpy(frame).float().permute(2,0,1).unsqueeze(0).cuda() / 255.0
    with torch.no_grad():
        output = aod_model(img)
    out_img = output.squeeze().permute(1,2,0).cpu().numpy()
    out_img = (np.clip(out_img, 0 , 1)*255).astype('uint8')
    return cv2.cvtColor(out_img, cv2.COLOR_RGB2BGR)

# === 변수 초기값 ===
prev_human = prev_red = prev_car = -1  # -1로 설정하여 처음에는 무조건 SPI 송신
cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("⚠️ Failed to open CSI camera")
    exit()

print("📸 CSI camera opened. Starting YOLOv5 inference...")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("❌ Frame read failed.")
            break

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        dehazed = dehaze_frame(rgb)
        results = model(dehazed, size=640)
        predictions = results.pred[0]

        # === 객체 인식 결과에서 클래스 판단 ===
        detected_classes = [int(cls) for *box, conf, cls in predictions]

        # YOLOv5 클래스 이름 기반 판별
        human = 0
        red_light = 0
        car = 0

        for cls_id in detected_classes:
            label = model.names[cls_id]
            if label == 'person':
                human = 1
            elif label in ['traffic light', 'stop sign']:
                red_light = 1
            elif label in ['car', 'truck', 'bus']:
                car = 1

        # === 값이 바뀌었을 경우 SPI 통신 ===
        if (human, red_light, car) != (prev_human, prev_red, prev_car):
            send_jetson_signals(human, red_light, car)
            prev_human, prev_red, prev_car = human, red_light, car

        # 결과 화면 출력
        rendered = results.render()[0]
        cv2.imshow("YOLOv5 CSI Preview", rendered)

        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord('q'):
            break

except KeyboardInterrupt:
    print("🛑 Interrupted by user.")

finally:
    cap.release()
    cv2.destroyAllWindows()
    spi.close()
    print("✅ Camera and SPI released.")

