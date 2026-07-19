from ultralytics import YOLO

print("Downloading YOLOv11 Segmentation Model...")

model = YOLO("yolo11n-seg.pt")

print("Model Ready!")