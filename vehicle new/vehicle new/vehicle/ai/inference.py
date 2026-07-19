from ultralytics import YOLO

# Load pretrained segmentation model
model = YOLO("yolo11n-seg.pt")

# Test image
results = model.predict(
    source="data/test.jpg",
    save=True,
    conf=0.25
)

print("Inference Completed")