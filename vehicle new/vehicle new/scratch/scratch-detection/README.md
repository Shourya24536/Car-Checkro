# Scratch Detection — YOLO11 Segmentation

AI-based scratch detection system using YOLO11 instance segmentation. Uses aluminum beverage cans as a prototype for vehicle body panel inspection.

## 🚀 Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Prepare Dataset

Export your annotated dataset from Roboflow in **YOLOv8 Segmentation** format and place it in the `dataset/` folder:

```
dataset/
├── train/
│   ├── images/
│   └── labels/
├── valid/
│   ├── images/
│   └── labels/
├── test/
│   ├── images/
│   └── labels/
└── data.yaml
```

### 3. Verify Dataset

```bash
python scripts/verify_dataset.py --data dataset/data.yaml --verbose
```

### 4. Train

```bash
# Quick prototype (nano model)
python scripts/train.py --model yolo11n-seg.pt --epochs 100

# Better accuracy (small model)
python scripts/train.py --model yolo11s-seg.pt --epochs 200

# Production (medium model)
python scripts/train.py --model yolo11m-seg.pt --epochs 300 --imgsz 1024 --batch 8
```

### 5. Evaluate

```bash
python scripts/validate.py --model runs/segment/train/weights/best.pt --data dataset/data.yaml
```

### 6. Predict

```bash
# Single image
python scripts/predict.py --model runs/segment/train/weights/best.pt --source path/to/image.jpg

# Folder of images
python scripts/predict.py --model runs/segment/train/weights/best.pt --source path/to/folder/ --save-json
```

### 7. Export Model

```bash
python scripts/export_model.py --model runs/segment/train/weights/best.pt --format onnx
```

---

## 📂 Project Structure

```
scratch-detection/
├── dataset/                  ← Roboflow export (YOLOv8 Segmentation)
├── raw_images/               ← Your original photos (organized by type)
│   ├── no_scratch/
│   ├── small_scratch/
│   ├── medium_scratch/
│   ├── large_scratch/
│   └── multiple_scratch/
├── scripts/
│   ├── train.py              ← Training script
│   ├── validate.py           ← Evaluation script
│   ├── predict.py            ← Inference + severity classification
│   ├── export_model.py       ← Export to ONNX/TensorRT
│   └── verify_dataset.py     ← Dataset integrity checker
├── runs/                     ← Training outputs (auto-generated)
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 🔍 Scratch Severity Classification

The model uses **one class** (`scratch`). Severity is determined post-inference by analyzing the segmentation mask area:

| Severity | Mask Area (% of image) | Condition |
|----------|------------------------|-----------|
| ✅ No Scratch | 0% | No detection |
| 🟡 Small | < 1% | Tiny marks |
| 🟠 Medium | 1–5% | Visible scratches |
| 🔴 Large | > 5% | Major damage |
| 🔴 Multiple | Any | > 1 detection |

Thresholds are configurable via CLI flags (`--small-thresh`, `--medium-thresh`).

---

## 📸 Image Collection Guidelines

| Type | Count | Description |
|------|-------|-------------|
| No Scratch | ~50 | Clean cans, no marks |
| Small Scratch | ~40 | Tiny, barely visible marks |
| Medium Scratch | ~40 | 1–3 cm scratches |
| Large Scratch | ~40 | Long, prominent scratches |
| Multiple Scratch | ~40 | 2–6 scratches on one can |
| **Total** | **~210** | Minimum recommended |

### Photo Tips
- Use consistent lighting (LED lamp recommended)
- Plain background (white or black)
- Vary angle slightly (front, left, right, top)
- Rotate can (0°, 45°, 90°, 180°)
- Keep camera distance reasonably consistent

---

## 🏷️ Annotation Rules (Roboflow)

1. **One class only:** `scratch`
2. **Use Polygon (Segmentation)** — NOT bounding boxes
3. **Trace the exact scratch boundary** — keep it tight
4. **Separate polygons** for each scratch (do not merge)
5. **Leave clean images unannotated** — the model must learn normal surfaces
6. **Close every polygon** properly

---

## 🖥️ Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | 4 GB VRAM | 8+ GB VRAM (RTX 3060+) |
| RAM | 8 GB | 16 GB |
| Storage | 5 GB | 20 GB |

No GPU? Use [Google Colab](https://colab.research.google.com/) with a free T4 GPU.

---

## 📊 Expected Results

With ~200 well-annotated images and 100–200 epochs:

| Metric | Expected Range |
|--------|----------------|
| mAP@50 | 0.70 – 0.90 |
| mAP@50-95 | 0.50 – 0.70 |
| Precision | 0.75 – 0.95 |
| Recall | 0.70 – 0.90 |

Results improve with more images, better annotations, and larger models.

---

## 📜 License

This project is for educational and research purposes.
