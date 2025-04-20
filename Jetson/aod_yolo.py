import torch
import cv2
import time
import os
import numpy as np
from aod_net import AODNet, prune_model, remove_pruning

### 🔁 모델 로드 및 Pruning ###
aod_model = AODNet().cuda()
checkpoint = torch.load("dehazer.pth")
new_checkpoint = {"aod_block." + k: v for k, v in checkpoint.items()}
aod_model.load_state_dict(new_checkpoint)
aod_model.eval()

# pruning 적용 및 mask 제거
prune_model(aod_model, amount=0.3)
remove_pruning(aod_model)

#
model = torch.hub.load('ultralytics/yolov5' , 'yolov5s' , device = 'cuda:0', force_reload = True)
# Jetson CSI + GStreamer 파이프라인 
gst_pipeline = (
    "nvarguscamerasrc ! "
    "video/x-raw(memory:NVMM), width=640, height=480, format=NV12, framerate=10/1 ! "
    "nvvidconv flip-method=2 ! "
    "video/x-raw, format=BGRx ! "
    "videoconvert ! "
    "video/x-raw, format=BGR ! appsink drop=1"
)

def dehaze_frame(frame):
    img = torch.from_numpy(frame).float().permute(2,0,1).unsqueeze(0).cuda() / 255.0
    with torch.no_grad():
         output = aod_model(img)
    out_img = output.squeeze().permute(1,2,0).cpu().numpy()
    out_img = (np.clip(out_img, 0 , 1)*255).astype('uint8')
    return cv2.cvtColor(out_img, cv2.COLOR_RGB2BGR)
# 카메라 연결
cap = cv2.VideoCapture(gst_pipeline, cv2.CAP_GSTREAMER)

if not cap.isOpened():
    print("❌ Failed to open CSI camera")
    exit()

print("✅ CSI camera opened. Starting YOLOv5 inference...")

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Frame read failed.")
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        dehazed = dehaze_frame(rgb)
        results = model(dehazed, size=640)
        predictions = results.pred[0]
        
        for *box, conf, cls in predictions:
            x1, y1, x2, y2 = map(int, box)
            cx = int((x1 + x2)/2)
            cy = int((y1 + y2)/2)
            
            cv2.circle(dehazed, (cx, cy),5 ,(0, 255,0), -1)
            
            print(f'class:{model.names[int(cls)]}, center: ({cx},{cy}) top_left: ({x1},{y1}) bottom_right: ({x2},{y2})')

        # 결과 시각화 후 저장
        rendered = results.render()[0]
        
        # 화면에 보여주기
        cv2.imshow("YOLOv5 CSI Preview", rendered)

        # ESC or Q로 종료
        key = cv2.waitKey(1) & 0xFF
        if key == 27 or key == ord('q'):
            break

except KeyboardInterrupt:
    print("🛑 Interrupted by user.")

finally:
    cap.release()
    cv2.destroyAllWindows()
    print("📷 CSI camera released.")
