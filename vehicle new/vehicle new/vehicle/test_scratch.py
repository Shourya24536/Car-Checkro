import cv2
from ai.scratch.detector import ScratchDetector

URL = "http://192.168.160.43:8080/video"   # Replace with your IP Webcam URL

cap = cv2.VideoCapture(URL)

detector = ScratchDetector()

while True:

    ret, frame = cap.read()

    if not ret:
        break

    results = detector.detect(frame)
    print("Boxes:", results[0].boxes)
    print("Masks:", results[0].masks)
    
    annotated = results[0].plot()

    cv2.imshow("Scratch Detection", annotated)

    if cv2.waitKey(1) == 27:
        break

cap.release()
cv2.destroyAllWindows()