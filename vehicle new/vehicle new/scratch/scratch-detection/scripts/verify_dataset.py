"""
YOLO11 Segmentation — Dataset Verification Script
===================================================
Verify dataset integrity before training:
  - Check folder structure
  - Validate image-label pairing
  - Check label file format (YOLO segmentation)
  - Verify polygon point counts
  - Check class consistency
  - Report statistics

Usage:
    python scripts/verify_dataset.py --data dataset/data.yaml
    python scripts/verify_dataset.py --data dataset/data.yaml --verbose --visualize
"""

import argparse
import sys
import os
from pathlib import Path
from collections import Counter

# Set console output encoding to UTF-8 to support emojis and lines on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

import yaml
import cv2
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Valid image extensions
IMG_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


def parse_args():
    parser = argparse.ArgumentParser(description="Verify YOLO Segmentation Dataset")

    parser.add_argument(
        "--data",
        type=str,
        default=str(PROJECT_ROOT / "dataset" / "data.yaml"),
        help="Path to data.yaml",
    )
    parser.add_argument("--verbose", action="store_true", help="Show detailed per-file info")
    parser.add_argument("--visualize", action="store_true", help="Visualize sample annotations")
    parser.add_argument("--max-vis", type=int, default=5, help="Max images to visualize (default: 5)")

    return parser.parse_args()


def load_data_yaml(yaml_path):
    """Load and validate data.yaml."""
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    required_keys = ["names"]
    for key in required_keys:
        if key not in data:
            print(f"  [ERROR] Missing key '{key}' in data.yaml")
            return None

    return data


def check_split(split_name, images_dir, labels_dir, expected_classes, verbose=False):
    """Check a single dataset split."""
    issues = []
    stats = {
        "total_images": 0,
        "total_labels": 0,
        "images_with_labels": 0,
        "images_without_labels": 0,
        "empty_labels": 0,
        "total_polygons": 0,
        "class_distribution": Counter(),
        "polygon_point_counts": [],
        "corrupt_labels": [],
    }

    images_path = Path(images_dir)
    labels_path = Path(labels_dir)

    if not images_path.exists():
        issues.append(f"Images directory not found: {images_path}")
        return stats, issues

    if not labels_path.exists():
        issues.append(f"Labels directory not found: {labels_path}")
        return stats, issues

    # Get all images
    image_files = sorted(
        [f for f in images_path.iterdir() if f.suffix.lower() in IMG_EXTENSIONS]
    )
    stats["total_images"] = len(image_files)

    # Get all labels
    label_files = sorted([f for f in labels_path.iterdir() if f.suffix == ".txt"])
    stats["total_labels"] = len(label_files)

    # Check each image
    for img_file in image_files:
        label_file = labels_path / (img_file.stem + ".txt")

        if label_file.exists():
            stats["images_with_labels"] += 1

            # Read and validate label
            try:
                with open(label_file, "r") as f:
                    lines = f.readlines()

                if len(lines) == 0:
                    stats["empty_labels"] += 1
                    if verbose:
                        print(f"    ⚪ {img_file.name}: empty label (no scratch)")
                    continue

                for line_num, line in enumerate(lines, 1):
                    line = line.strip()
                    if not line:
                        continue

                    parts = line.split()

                    # First value is class ID
                    try:
                        class_id = int(parts[0])
                    except ValueError:
                        stats["corrupt_labels"].append(
                            f"{label_file.name}:{line_num} — invalid class ID: {parts[0]}"
                        )
                        continue

                    # Check class ID
                    if class_id < 0 or class_id >= len(expected_classes):
                        stats["corrupt_labels"].append(
                            f"{label_file.name}:{line_num} — class ID {class_id} out of range (expected 0-{len(expected_classes)-1})"
                        )
                        continue

                    stats["class_distribution"][expected_classes[class_id]] += 1

                    # Remaining values are polygon points (x, y pairs)
                    coords = parts[1:]
                    if len(coords) < 6:  # Minimum 3 points (6 values)
                        stats["corrupt_labels"].append(
                            f"{label_file.name}:{line_num} — polygon has only {len(coords)//2} points (min 3)"
                        )
                        continue

                    if len(coords) % 2 != 0:
                        stats["corrupt_labels"].append(
                            f"{label_file.name}:{line_num} — odd number of coordinates ({len(coords)})"
                        )
                        continue

                    # Validate coordinate values (should be 0–1 normalized)
                    valid_coords = True
                    for val in coords:
                        try:
                            fval = float(val)
                            if fval < 0 or fval > 1:
                                stats["corrupt_labels"].append(
                                    f"{label_file.name}:{line_num} — coordinate {fval} out of range [0, 1]"
                                )
                                valid_coords = False
                                break
                        except ValueError:
                            stats["corrupt_labels"].append(
                                f"{label_file.name}:{line_num} — invalid coordinate: {val}"
                            )
                            valid_coords = False
                            break

                    if valid_coords:
                        num_points = len(coords) // 2
                        stats["polygon_point_counts"].append(num_points)
                        stats["total_polygons"] += 1

                        if verbose:
                            print(
                                f"    ✅ {img_file.name}: {num_points} polygon points"
                            )

            except Exception as e:
                stats["corrupt_labels"].append(f"{label_file.name} — read error: {e}")
        else:
            stats["images_without_labels"] += 1
            if verbose:
                print(f"    ⚪ {img_file.name}: no label file (no scratch)")

    # Check for orphan labels (labels without images)
    image_stems = {f.stem for f in image_files}
    for label_file in label_files:
        if label_file.stem not in image_stems:
            issues.append(f"Orphan label (no matching image): {label_file.name}")

    return stats, issues


def visualize_annotations(images_dir, labels_dir, max_vis=5):
    """Visualize sample annotations."""
    images_path = Path(images_dir)
    labels_path = Path(labels_dir)

    image_files = sorted(
        [f for f in images_path.iterdir() if f.suffix.lower() in IMG_EXTENSIONS]
    )

    visualized = 0
    for img_file in image_files:
        if visualized >= max_vis:
            break

        label_file = labels_path / (img_file.stem + ".txt")
        if not label_file.exists():
            continue

        with open(label_file, "r") as f:
            lines = f.readlines()

        if not lines:
            continue

        # Read image
        img = cv2.imread(str(img_file))
        if img is None:
            continue

        h, w = img.shape[:2]
        overlay = img.copy()

        for line in lines:
            parts = line.strip().split()
            if len(parts) < 7:
                continue

            coords = [float(x) for x in parts[1:]]
            points = []
            for j in range(0, len(coords), 2):
                px = int(coords[j] * w)
                py = int(coords[j + 1] * h)
                points.append([px, py])

            points = np.array(points, dtype=np.int32)

            # Draw filled polygon with transparency
            cv2.fillPoly(overlay, [points], (0, 0, 255))
            cv2.polylines(img, [points], True, (0, 255, 0), 2)

        # Blend
        alpha = 0.3
        result = cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0)

        # Save visualization
        vis_dir = PROJECT_ROOT / "runs" / "verify"
        vis_dir.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(vis_dir / f"vis_{img_file.name}"), result)
        visualized += 1

    if visualized > 0:
        print(f"  📸 Saved {visualized} visualizations to: runs/verify/")


def verify(args):
    """Run full dataset verification."""
    print("=" * 70)
    print("  YOLO11 Segmentation — Dataset Verification")
    print("=" * 70)
    print()

    # Load data.yaml
    data_path = Path(args.data)
    if not data_path.exists():
        print(f"  [ERROR] data.yaml not found: {data_path}")
        print("  Please export your Roboflow dataset first.")
        sys.exit(1)

    data = load_data_yaml(data_path)
    if data is None:
        sys.exit(1)

    dataset_root = data_path.parent
    class_names = data["names"]
    if isinstance(class_names, dict):
        class_names = [class_names[i] for i in sorted(class_names.keys())]

    print(f"  Dataset root: {dataset_root}")
    print(f"  Classes ({len(class_names)}): {class_names}")
    print()

    # Verify each split
    splits = {
        "train": (dataset_root / "train" / "images", dataset_root / "train" / "labels"),
        "valid": (dataset_root / "valid" / "images", dataset_root / "valid" / "labels"),
        "test": (dataset_root / "test" / "images", dataset_root / "test" / "labels"),
    }

    all_issues = []
    total_images = 0
    total_polygons = 0

    for split_name, (img_dir, lbl_dir) in splits.items():
        print(f"  ── {split_name.upper()} ──")

        stats, issues = check_split(split_name, img_dir, lbl_dir, class_names, args.verbose)
        all_issues.extend(issues)

        print(f"    Images:              {stats['total_images']}")
        print(f"    With annotations:    {stats['images_with_labels']}")
        print(f"    Without annotations: {stats['images_without_labels']} (clean images)")
        print(f"    Empty labels:        {stats['empty_labels']}")
        print(f"    Total polygons:      {stats['total_polygons']}")

        if stats["class_distribution"]:
            print(f"    Class distribution:  {dict(stats['class_distribution'])}")

        if stats["polygon_point_counts"]:
            pts = stats["polygon_point_counts"]
            print(
                f"    Polygon points:      min={min(pts)}, max={max(pts)}, avg={sum(pts)/len(pts):.1f}"
            )

        if stats["corrupt_labels"]:
            print(f"    ⚠️  Corrupt labels:   {len(stats['corrupt_labels'])}")
            for err in stats["corrupt_labels"][:5]:
                print(f"       - {err}")
            if len(stats["corrupt_labels"]) > 5:
                print(f"       ... and {len(stats['corrupt_labels']) - 5} more")

        total_images += stats["total_images"]
        total_polygons += stats["total_polygons"]
        print()

    # Visualize if requested
    if args.visualize:
        train_imgs = splits["train"][0]
        train_lbls = splits["train"][1]
        if train_imgs.exists():
            visualize_annotations(train_imgs, train_lbls, args.max_vis)

    # Summary
    print("=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    print(f"  Total images:   {total_images}")
    print(f"  Total polygons: {total_polygons}")
    print(f"  Issues found:   {len(all_issues)}")

    if all_issues:
        print()
        print("  ⚠️  Issues:")
        for issue in all_issues:
            print(f"    - {issue}")
    else:
        print("  ✅ Dataset looks good! Ready for training.")

    print("=" * 70)

    return len(all_issues) == 0


if __name__ == "__main__":
    args = parse_args()
    success = verify(args)
    sys.exit(0 if success else 1)
