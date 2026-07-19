"""
YOLO11 Segmentation — Validation Script
========================================
Evaluate a trained YOLO11 segmentation model on the test/validation set.

Usage:
    python scripts/validate.py --model runs/segment/train/weights/best.pt
    python scripts/validate.py --model runs/segment/train/weights/best.pt --data dataset/data.yaml --split test
"""

import argparse
import sys
from pathlib import Path

# Set console output encoding to UTF-8 to support emojis and lines on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_args():
    parser = argparse.ArgumentParser(description="Validate YOLO11 Segmentation Model")

    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to trained model weights (e.g., runs/segment/train/weights/best.pt)",
    )
    parser.add_argument(
        "--data",
        type=str,
        default=str(PROJECT_ROOT / "dataset" / "data.yaml"),
        help="Path to data.yaml",
    )
    parser.add_argument(
        "--split",
        type=str,
        default="test",
        choices=["val", "test"],
        help="Dataset split to evaluate on (default: test)",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="Image size (default: 640)")
    parser.add_argument("--batch", type=int, default=16, help="Batch size (default: 16)")
    parser.add_argument("--conf", type=float, default=0.25, help="Confidence threshold (default: 0.25)")
    parser.add_argument("--iou", type=float, default=0.6, help="IoU threshold for NMS (default: 0.6)")
    parser.add_argument("--device", type=str, default="0", help="Device (default: 0)")
    parser.add_argument("--verbose", action="store_true", default=True, help="Verbose output")

    return parser.parse_args()


def validate(args):
    """Run validation on the specified dataset split."""
    from ultralytics import YOLO

    print("=" * 60)
    print("  YOLO11 Scratch Detection — Validation")
    print("=" * 60)
    print(f"  Model:      {args.model}")
    print(f"  Dataset:    {args.data}")
    print(f"  Split:      {args.split}")
    print(f"  Confidence: {args.conf}")
    print(f"  IoU:        {args.iou}")
    print("=" * 60)
    print()

    # Validate paths
    model_path = Path(args.model)
    if not model_path.exists():
        print(f"[ERROR] Model not found: {model_path}")
        sys.exit(1)

    data_path = Path(args.data)
    if not data_path.exists():
        print(f"[ERROR] Dataset config not found: {data_path}")
        sys.exit(1)

    # Load model
    model = YOLO(str(model_path))

    # Run validation
    results = model.val(
        data=str(data_path),
        split=args.split,
        imgsz=args.imgsz,
        batch=args.batch,
        conf=args.conf,
        iou=args.iou,
        device=args.device,
        verbose=args.verbose,
        plots=True,
    )

    # Print summary
    print()
    print("=" * 60)
    print("  Validation Results")
    print("=" * 60)

    # Segmentation metrics
    if hasattr(results, "seg"):
        seg = results.seg
        print(f"  Mask mAP@50:      {seg.map50:.4f}")
        print(f"  Mask mAP@50-95:   {seg.map:.4f}")
        print(f"  Mask Precision:    {seg.mp:.4f}")
        print(f"  Mask Recall:       {seg.mr:.4f}")

    # Box metrics (if available)
    if hasattr(results, "box"):
        box = results.box
        print()
        print(f"  Box mAP@50:       {box.map50:.4f}")
        print(f"  Box mAP@50-95:    {box.map:.4f}")
        print(f"  Box Precision:    {box.mp:.4f}")
        print(f"  Box Recall:       {box.mr:.4f}")

    print("=" * 60)
    print()
    print("  Performance Guide:")
    print("    mAP@50 > 0.70  → Good baseline")
    print("    mAP@50 > 0.85  → Strong performance")
    print("    mAP@50 > 0.90  → Production-ready")
    print()
    print("  If results are poor, consider:")
    print("    - Adding more training images")
    print("    - Improving annotation quality")
    print("    - Training for more epochs")
    print("    - Using a larger model variant (yolo11s-seg or yolo11m-seg)")
    print("=" * 60)

    return results


if __name__ == "__main__":
    args = parse_args()
    validate(args)
