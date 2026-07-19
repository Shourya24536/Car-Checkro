"""
YOLO11 Segmentation — Training Script
======================================
Train a YOLO11 segmentation model for scratch detection on aluminum cans.

Usage:
    python scripts/train.py --data dataset/data.yaml --epochs 100
    python scripts/train.py --model yolo11s-seg.pt --data dataset/data.yaml --epochs 200 --imgsz 1024 --batch 8
"""

import argparse
import sys
from pathlib import Path

# Set console output encoding to UTF-8 to support emojis and lines on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_args():
    parser = argparse.ArgumentParser(
        description="Train YOLO11 Segmentation for Scratch Detection",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Quick prototype (nano model, 50 epochs):
    python scripts/train.py --model yolo11n-seg.pt --epochs 50

  Balanced training (small model, 100 epochs):
    python scripts/train.py --model yolo11s-seg.pt --epochs 100

  Production training (medium model, 300 epochs):
    python scripts/train.py --model yolo11m-seg.pt --epochs 300 --imgsz 1024 --batch 8

  Resume interrupted training:
    python scripts/train.py --resume runs/segment/train/weights/last.pt
        """,
    )

    # Model
    parser.add_argument(
        "--model",
        type=str,
        default="yolo11n-seg.pt",
        choices=[
            "yolo11n-seg.pt",
            "yolo11s-seg.pt",
            "yolo11m-seg.pt",
            "yolo11l-seg.pt",
            "yolo11x-seg.pt",
        ],
        help="YOLO11 segmentation model variant (default: yolo11n-seg.pt)",
    )

    # Dataset
    parser.add_argument(
        "--data",
        type=str,
        default=str(PROJECT_ROOT / "dataset" / "data.yaml"),
        help="Path to data.yaml (default: dataset/data.yaml)",
    )

    # Training hyperparameters
    parser.add_argument("--epochs", type=int, default=100, help="Number of training epochs (default: 100)")
    parser.add_argument("--imgsz", type=int, default=640, help="Input image size (default: 640)")
    parser.add_argument("--batch", type=int, default=16, help="Batch size (default: 16)")
    parser.add_argument("--lr0", type=float, default=0.01, help="Initial learning rate (default: 0.01)")
    parser.add_argument("--lrf", type=float, default=0.01, help="Final learning rate factor (default: 0.01)")
    parser.add_argument("--optimizer", type=str, default="AdamW", help="Optimizer (default: AdamW)")
    parser.add_argument("--patience", type=int, default=50, help="Early stopping patience (default: 50)")
    parser.add_argument("--workers", type=int, default=8, help="Dataloader workers (default: 8)")

    # Augmentation
    parser.add_argument("--augment", action="store_true", default=True, help="Enable augmentation (default: True)")
    parser.add_argument("--mosaic", type=float, default=1.0, help="Mosaic augmentation probability (default: 1.0)")
    parser.add_argument("--flipud", type=float, default=0.0, help="Vertical flip probability (default: 0.0)")
    parser.add_argument("--fliplr", type=float, default=0.5, help="Horizontal flip probability (default: 0.5)")
    parser.add_argument("--degrees", type=float, default=15.0, help="Rotation degrees (default: 15.0)")
    parser.add_argument("--hsv_h", type=float, default=0.015, help="HSV hue augmentation (default: 0.015)")
    parser.add_argument("--hsv_s", type=float, default=0.7, help="HSV saturation augmentation (default: 0.7)")
    parser.add_argument("--hsv_v", type=float, default=0.4, help="HSV value augmentation (default: 0.4)")

    # Output
    parser.add_argument("--project", type=str, default=str(PROJECT_ROOT / "runs"), help="Output project directory")
    parser.add_argument("--name", type=str, default="train", help="Run name (default: train)")
    parser.add_argument("--exist_ok", action="store_true", help="Allow overwriting existing run")

    # Device
    parser.add_argument(
        "--device",
        type=str,
        default="0",
        help="Device: '0' for GPU 0, 'cpu' for CPU, '0,1' for multi-GPU (default: 0)",
    )

    # Resume
    parser.add_argument("--resume", type=str, default=None, help="Path to last.pt to resume training")

    return parser.parse_args()


def train(args):
    """Run YOLO11 segmentation training."""
    from ultralytics import YOLO

    # Print configuration
    print("=" * 60)
    print("  YOLO11 Scratch Detection — Segmentation Training")
    print("=" * 60)
    print(f"  Model:      {args.model}")
    print(f"  Dataset:    {args.data}")
    print(f"  Epochs:     {args.epochs}")
    print(f"  Image Size: {args.imgsz}")
    print(f"  Batch Size: {args.batch}")
    print(f"  Device:     {args.device}")
    print(f"  Optimizer:  {args.optimizer}")
    print(f"  Patience:   {args.patience}")
    print("=" * 60)
    print()

    # Validate dataset path
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"[ERROR] Dataset config not found: {data_path}")
        print("        Please export your Roboflow dataset into the 'dataset/' folder.")
        print("        The data.yaml file should be at: dataset/data.yaml")
        sys.exit(1)

    # Resume or fresh training
    if args.resume:
        print(f"[INFO] Resuming training from: {args.resume}")
        model = YOLO(args.resume)
        results = model.train(resume=True)
    else:
        # Load pretrained model
        print(f"[INFO] Loading pretrained model: {args.model}")
        model = YOLO(args.model)

        # Train
        results = model.train(
            data=str(data_path),
            epochs=args.epochs,
            imgsz=args.imgsz,
            batch=args.batch,
            lr0=args.lr0,
            lrf=args.lrf,
            optimizer=args.optimizer,
            patience=args.patience,
            workers=args.workers,
            # Augmentation
            augment=args.augment,
            mosaic=args.mosaic,
            flipud=args.flipud,
            fliplr=args.fliplr,
            degrees=args.degrees,
            hsv_h=args.hsv_h,
            hsv_s=args.hsv_s,
            hsv_v=args.hsv_v,
            # Output
            project=args.project,
            name=args.name,
            exist_ok=args.exist_ok,
            # Device
            device=args.device,
            # Logging
            verbose=True,
            plots=True,
            save=True,
            save_period=25,  # Save checkpoint every 25 epochs
        )

    # Print results
    print()
    print("=" * 60)
    print("  Training Complete!")
    print("=" * 60)
    print(f"  Best weights: {args.project}/{args.name}/weights/best.pt")
    print(f"  Last weights: {args.project}/{args.name}/weights/last.pt")
    print(f"  Results:      {args.project}/{args.name}/")
    print()
    print("  Next steps:")
    print("    1. Validate: python scripts/validate.py --model runs/segment/train/weights/best.pt")
    print("    2. Predict:  python scripts/predict.py --model runs/segment/train/weights/best.pt --source <image>")
    print("    3. Export:   python scripts/export_model.py --model runs/segment/train/weights/best.pt")
    print("=" * 60)

    return results


if __name__ == "__main__":
    args = parse_args()
    train(args)
