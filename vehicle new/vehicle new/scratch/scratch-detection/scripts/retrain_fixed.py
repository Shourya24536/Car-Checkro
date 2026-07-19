"""
Retrain YOLO11 Segmentation with Cleaned Labels
=================================================
This script retrains from scratch with corrected annotations.
Optimized hyperparameters for scratch detection.
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def main():
    import torch
    from ultralytics import YOLO

    # Clear any leftover GPU memory
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.reset_peak_memory_stats()

    data_path = PROJECT_ROOT / "dataset" / "data.yaml"

    print("=" * 70)
    print("  RETRAINING — Cleaned Labels, Fresh Start")
    print("=" * 70)
    print(f"  Model:    yolo11n-seg.pt (pretrained)")
    print(f"  Dataset:  {data_path}")
    print(f"  Device:   GPU 0 (RTX 3050)")
    print("=" * 70)

    # Load fresh pretrained model — NOT the old corrupted weights
    model = YOLO("yolo11n-seg.pt")

    # Train with optimized hyperparameters for scratch detection
    results = model.train(
        data=str(data_path),
        epochs=150,
        imgsz=640,
        batch=4,            # RTX 3050 6GB — batch=8 OOMs, batch=4 is safe
        lr0=0.01,
        lrf=0.01,
        optimizer="AdamW",
        patience=50,
        workers=4,
        # Augmentation — tuned for scratch detection
        augment=True,
        mosaic=0.5,          # Reduced from 1.0 — mosaic can destroy small scratches
        flipud=0.0,
        fliplr=0.5,
        degrees=10.0,        # Slight rotation
        hsv_h=0.015,
        hsv_s=0.5,           # Reduced from 0.7 — scratches are texture, not color
        hsv_v=0.3,           # Reduced from 0.4
        erasing=0.0,         # DISABLED — random erasing can erase the scratches!
        scale=0.3,           # Reduced from 0.5 — less aggressive scaling
        # Output
        project=str(PROJECT_ROOT / "runs"),
        name="train-fixed",
        exist_ok=True,
        # Device
        device=0,
        # Logging
        verbose=True,
        plots=True,
        save=True,
        save_period=25,
    )

    print()
    print("=" * 70)
    print("  TRAINING COMPLETE!")
    print("=" * 70)
    print(f"  Best weights: runs/train-fixed/weights/best.pt")
    print(f"  Last weights: runs/train-fixed/weights/last.pt")
    print("=" * 70)

    return results


if __name__ == "__main__":
    main()
