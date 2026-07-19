"""
Calculate Precision, Recall, FP, FN on Test Split
==================================================
Reads test images and compares model predictions with ground truth labels.
Calculates binary classification metrics (Scratch vs No Scratch).
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def main():
    from ultralytics import YOLO

    model_path = PROJECT_ROOT / "runs" / "train-fixed" / "weights" / "best.pt"
    test_images_dir = PROJECT_ROOT / "dataset" / "test" / "images"
    test_labels_dir = PROJECT_ROOT / "dataset" / "test" / "labels"

    if not model_path.exists():
        print(f"Model not found: {model_path}")
        sys.exit(1)

    print("=" * 70)
    print("  BINARY CLASSIFICATION VALIDATION (Scratch vs Clean)")
    print("=" * 70)
    print(f"  Model:  {model_path.relative_to(PROJECT_ROOT)}")
    print(f"  Images: {test_images_dir.relative_to(PROJECT_ROOT)}")
    print("=" * 70)
    print()

    # Load model
    model = YOLO(str(model_path))

    # Get test files
    image_files = sorted([f for f in test_images_dir.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png')])

    tp = 0
    fp = 0
    fn = 0
    tn = 0

    detailed_results = []

    for img_file in image_files:
        # Run prediction
        res = model.predict(source=str(img_file), conf=0.25, verbose=False)[0]
        pred_has_scratch = (res.masks is not None and len(res.masks) > 0)

        # Ground truth
        label_file = test_labels_dir / f"{img_file.stem}.txt"
        gt_has_scratch = False
        if label_file.exists():
            content = label_file.read_text(encoding='utf-8').strip()
            if content:
                # Any non-empty file means it has a scratch polygon
                gt_has_scratch = True

        # Classify metric
        status = ""
        if pred_has_scratch and gt_has_scratch:
            tp += 1
            status = "TP (True Positive)"
        elif pred_has_scratch and not gt_has_scratch:
            fp += 1
            status = "FP (False Positive) ⚠️"
        elif not pred_has_scratch and gt_has_scratch:
            fn += 1
            status = "FN (False Negative) ⚠️"
        else:
            tn += 1
            status = "TN (True Negative)"

        detailed_results.append({
            "image": img_file.name,
            "gt": "Scratch" if gt_has_scratch else "Clean",
            "pred": "Scratch" if pred_has_scratch else "Clean",
            "status": status,
            "conf": float(res.boxes.conf[0]) if pred_has_scratch else 0.0
        })

    # Calculations
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
    accuracy = (tp + tn) / len(image_files) if len(image_files) > 0 else 0.0

    # Print details
    print(f"{'Image File':<60} | {'GT':<8} | {'Pred':<8} | {'Status':<20}")
    print("-" * 105)
    for r in detailed_results:
        print(f"{r['image']:<60} | {r['gt']:<8} | {r['pred']:<8} | {r['status']:<20}")

    print("\n" + "=" * 70)
    print("  METRICS SUMMARY")
    print("=" * 70)
    print(f"  Total Test Images:  {len(image_files)}")
    print(f"  True Positives:     {tp}")
    print(f"  False Positives:    {fp}")
    print(f"  False Negatives:    {fn}")
    print(f"  True Negatives:     {tn}")
    print("-" * 70)
    print(f"  Precision:          {precision:.4f} ({precision*100:.1f}%)")
    print(f"  Recall:             {recall:.4f} ({recall*100:.1f}%)")
    print(f"  F1-Score:           {f1:.4f} ({f1*100:.1f}%)")
    print(f"  Accuracy:           {accuracy:.4f} ({accuracy*100:.1f}%)")
    print("=" * 70)

if __name__ == "__main__":
    main()
