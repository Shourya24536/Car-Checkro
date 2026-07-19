from ultralytics import YOLO

model = YOLO("ai/scratch/best.pt")

results = model.predict(
    source="ai/scratch/dataset/test/image_001.jpeg",   # Change to an actual image path
    conf=0.05,
    save=True,
    verbose=True
)

print(results[0].boxes)
print(results[0].masks)