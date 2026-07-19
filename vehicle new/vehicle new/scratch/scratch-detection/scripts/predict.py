"""
YOLO11 Segmentation — Prediction Script
=========================================
Run inference on images and classify scratch severity based on mask area.

Severity Classification (post-processing):
  - No Scratch:       No detection
  - Small Scratch:    Mask area < 1% of image
  - Medium Scratch:   Mask area 1–5% of image
  - Large Scratch:    Mask area > 5% of image
  - Multiple:         More than one mask detected

Usage:
    python scripts/predict.py --model runs/segment/train/weights/best.pt --source image.jpg
    python scripts/predict.py --model runs/segment/train/weights/best.pt --source dataset/test/images/
    python scripts/predict.py --model runs/segment/train/weights/best.pt --source image.jpg --save-crops
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

# Set console output encoding to UTF-8 to support emojis and lines on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# ─── Severity thresholds (% of total image area) ────────────────────────────
SEVERITY_THRESHOLDS = {
    "small": 1.0,    # mask area < 1% → small
    "medium": 5.0,   # mask area 1–5% → medium
    # mask area > 5% → large
}


def parse_args():
    parser = argparse.ArgumentParser(description="Run YOLO11 Segmentation Inference")

    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to trained model weights",
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Path to image, folder, or video",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="Image size (default: 640)")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold (default: 0.25)")
    parser.add_argument("--iou", type=float, default=0.45, help="IoU threshold (default: 0.45)")
    parser.add_argument("--device", type=str, default="0", help="Device (default: 0)")
    parser.add_argument("--save", action="store_true", default=True, help="Save annotated images")
    parser.add_argument("--save-crops", action="store_true", help="Save cropped scratch regions")
    parser.add_argument("--save-json", action="store_true", help="Save results as JSON")
    parser.add_argument(
        "--output",
        type=str,
        default=str(PROJECT_ROOT / "runs" / "predict"),
        help="Output directory",
    )
    parser.add_argument("--show", action="store_true", help="Display results in window")

    # Severity thresholds
    parser.add_argument(
        "--small-thresh",
        type=float,
        default=1.0,
        help="Max mask area %% for 'small' severity (default: 1.0)",
    )
    parser.add_argument(
        "--medium-thresh",
        type=float,
        default=5.0,
        help="Max mask area %% for 'medium' severity (default: 5.0)",
    )

    return parser.parse_args()


def classify_severity(mask_area_percent, small_thresh, medium_thresh):
    """Classify scratch severity based on mask area percentage."""
    if mask_area_percent < small_thresh:
        return "SMALL"
    elif mask_area_percent < medium_thresh:
        return "MEDIUM"
    else:
        return "LARGE"


def compute_mask_area_percent(mask, image_shape):
    """Compute mask area as a percentage of total image area."""
    total_pixels = image_shape[0] * image_shape[1]
    mask_pixels = np.sum(mask > 0)
    return (mask_pixels / total_pixels) * 100


def process_results(results, args):
    """Process prediction results and classify severity."""
    all_reports = []

    for result in results:
        image_path = Path(result.path)
        image_shape = result.orig_shape  # (height, width)
        report = {
            "image": image_path.name,
            "image_path": str(image_path),
            "image_size": {"height": image_shape[0], "width": image_shape[1]},
            "scratches": [],
            "total_scratches": 0,
            "overall_severity": "NO SCRATCH",
            "total_mask_area_percent": 0.0,
        }

        if result.masks is not None and len(result.masks) > 0:
            masks = result.masks.data.cpu().numpy()
            boxes = result.boxes
            total_area = 0.0

            for i in range(len(masks)):
                # Resize mask to original image size
                mask = cv2.resize(
                    masks[i],
                    (image_shape[1], image_shape[0]),
                    interpolation=cv2.INTER_LINEAR,
                )
                area_pct = compute_mask_area_percent(mask, image_shape)
                total_area += area_pct
                severity = classify_severity(area_pct, args.small_thresh, args.medium_thresh)
                conf = float(boxes.conf[i])

                scratch_info = {
                    "id": i + 1,
                    "confidence": round(conf, 4),
                    "mask_area_percent": round(area_pct, 4),
                    "severity": severity,
                }
                report["scratches"].append(scratch_info)

            report["total_scratches"] = len(masks)
            report["total_mask_area_percent"] = round(total_area, 4)

            # Overall severity
            if len(masks) > 1:
                report["overall_severity"] = f"MULTIPLE ({len(masks)} scratches)"
            else:
                report["overall_severity"] = report["scratches"][0]["severity"]

        all_reports.append(report)

    return all_reports


def print_report(reports):
    """Print a formatted inspection report."""
    print()
    print("=" * 70)
    print("  SCRATCH INSPECTION REPORT")
    print(f"  Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    for report in reports:
        print()
        print(f"  📸 Image: {report['image']}")
        print(f"     Size:  {report['image_size']['width']}×{report['image_size']['height']}")
        print(f"     Status: {report['overall_severity']}")

        if report["total_scratches"] == 0:
            print("     ✅ No scratches detected — surface is clean")
        else:
            print(f"     Total scratches: {report['total_scratches']}")
            print(f"     Total affected area: {report['total_mask_area_percent']:.2f}%")
            print()

            for scratch in report["scratches"]:
                severity_icon = {"SMALL": "🟡", "MEDIUM": "🟠", "LARGE": "🔴"}.get(
                    scratch["severity"], "⚪"
                )
                print(
                    f"     {severity_icon} Scratch #{scratch['id']}: "
                    f"{scratch['severity']} | "
                    f"Area: {scratch['mask_area_percent']:.2f}% | "
                    f"Confidence: {scratch['confidence']:.2f}"
                )

        print("  " + "-" * 66)

    print()
    print("=" * 70)


def predict(args):
    """Run prediction and generate inspection report."""
    from ultralytics import YOLO

    print("=" * 60)
    print("  YOLO11 Scratch Detection — Inference")
    print("=" * 60)
    print(f"  Model:      {args.model}")
    print(f"  Source:      {args.source}")
    print(f"  Confidence: {args.conf}")
    print(f"  Severity:   small < {args.small_thresh}% < medium < {args.medium_thresh}% < large")
    print("=" * 60)

    # Validate paths
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"[ERROR] Model not found: {model_path}")
        sys.exit(1)

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"[ERROR] Source not found: {source_path}")
        sys.exit(1)

    # Load model
    model = YOLO(str(model_path))

    # Run prediction
    results = model.predict(
        source=str(source_path),
        imgsz=args.imgsz,
        conf=args.conf,
        iou=args.iou,
        device=args.device,
        save=args.save,
        save_crop=args.save_crops,
        project=args.output,
        name="results",
        exist_ok=True,
        show=args.show,
        verbose=False,
    )

    # Process and display results
    reports = process_results(results, args)
    print_report(reports)

    # Save JSON report
    if args.save_json:
        output_dir = Path(args.output) / "results"
        output_dir.mkdir(parents=True, exist_ok=True)
        json_path = output_dir / "inspection_report.json"
        with open(json_path, "w") as f:
            json.dump(reports, f, indent=2)
        print(f"  📄 JSON report saved: {json_path}")

    return reports


if __name__ == "__main__":
    args = parse_args()
    predict(args)
