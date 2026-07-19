from ultralytics import YOLO

class ScratchDetector:
    def __init__(self, model_path="ai/scratch/best.pt"):
        self.model = YOLO(model_path)

    def detect(self, frame):
        results = self.model.predict(
            source=frame,
            conf=0.05,
            verbose=False
        )
        return results

if __name__ == "__main__":
    detector = ScratchDetector()
    print("Scratch detector initialized successfully.")
    print("Model names:", detector.model.names)