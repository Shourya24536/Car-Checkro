"""
YOLO11 Segmentation — Model Export Script
==========================================
Export trained model to ONNX or other formats for deployment.

Usage:
    python scripts/export_model.py --model runs/segment/train/weights/best.pt
    python scripts/export_model.py --model runs/segment/train/weights/best.pt --format onnx --imgsz 640
"""

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_args():
    parser = argparse.ArgumentParser(description="Export YOLO11 Segmentation Model")

    parser.add_argument(
        "--model",
        type=str,
        required=True,
        help="Path to trained model weights (best.pt)",
    )
    parser.add_argument(
        "--format",
        type=str,
        default="onnx",
        choices=["onnx", "torchscript", "engine", "openvino", "tflite", "coreml"],
        help="Export format (default: onnx)",
    )
    parser.add_argument("--imgsz", type=int, default=640, help="Image size (default: 640)")
    parser.add_argument("--half", action="store_true", help="Export with FP16 half precision")
    parser.add_argument("--dynamic", action="store_true", help="Enable dynamic axes for ONNX")
    parser.add_argument("--simplify", action="store_true", default=True, help="Simplify ONNX model")
    parser.add_argument("--device", type=str, default="0", help="Device (default: 0)")

    return parser.parse_args()


def export_model(args):
    """Export the trained model."""
    from ultralytics import YOLO

    print("=" * 60)
    print("  YOLO11 Scratch Detection — Model Export")
    print("=" * 60)
    print(f"  Model:    {args.model}")
    print(f"  Format:   {args.format}")
    print(f"  ImgSize:  {args.imgsz}")
    print(f"  FP16:     {args.half}")
    print("=" * 60)
    print()

    model_path = Path(args.model)
    if not model_path.exists():
        print(f"[ERROR] Model not found: {model_path}")
        sys.exit(1)

    # Load model
    model = YOLO(str(model_path))

    # Export
    exported_path = model.export(
        format=args.format,
        imgsz=args.imgsz,
        half=args.half,
        dynamic=args.dynamic,
        simplify=args.simplify,
        device=args.device,
    )

    print()
    print("=" * 60)
    print("  Export Complete!")
    print("=" * 60)
    print(f"  Exported model: {exported_path}")
    print()
    print("  Deployment options:")
    print("    - ONNX Runtime (Python, C++, C#, Java)")
    print("    - TensorRT (NVIDIA GPUs)")
    print("    - OpenVINO (Intel hardware)")
    print("    - CoreML (Apple devices)")
    print("=" * 60)

    return exported_path


if __name__ == "__main__":
    args = parse_args()
    export_model(args)
