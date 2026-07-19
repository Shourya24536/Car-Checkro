"""
Label Audit & Fix Script for Scratch Detection
================================================
Identifies and removes full-image garbage polygon annotations that were
incorrectly exported from Roboflow for clean/no-scratch images.

A "garbage polygon" is one where the polygon vertices essentially cover
the entire image (coordinates near 0,0 and 1,1).

Usage:
    python scripts/audit_and_fix_labels.py
    python scripts/audit_and_fix_labels.py --dry-run
    python scripts/audit_and_fix_labels.py --fix
"""

import argparse
import shutil
import sys
from pathlib import Path
from collections import defaultdict

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATASET_ROOT = PROJECT_ROOT / "dataset"


def is_garbage_polygon(parts):
    """
    Detect if a YOLO segmentation annotation line represents a full-image
    garbage polygon.

    A garbage polygon has vertices that span nearly the entire image:
    - Some coords near 0 and some near 1
    - The polygon area covers >90% of the image
    - Typically has very few vertices (5-6 points forming a rectangle)

    Format: class_id x1 y1 x2 y2 x3 y3 ...
    """
    if len(parts) < 7:  # class_id + at least 3 points (6 coords)
        return False

    coords = [float(p) for p in parts[1:]]  # skip class_id

    # Extract x and y coordinates
    xs = coords[0::2]
    ys = coords[1::2]

    if len(xs) < 3:
        return False

    # Check if polygon spans nearly the entire image
    x_min, x_max = min(xs), max(xs)
    y_min, y_max = min(ys), max(ys)

    x_span = x_max - x_min
    y_span = y_max - y_min

    # A garbage polygon spans >95% in BOTH dimensions
    if x_span > 0.95 and y_span > 0.95:
        return True

    # Also catch the specific degenerate pattern:
    # 0 0 ~1 ~1 ~1 ~1 0 0 0 0 ~1
    # where most coords are at the extreme corners
    corner_count = 0
    for i in range(len(xs)):
        x, y = xs[i], ys[i]
        near_origin = (x < 0.05 and y < 0.05)
        near_top_right = (x > 0.95 and y > 0.95)
        near_bottom_left = (x < 0.05 and y > 0.95)
        near_top_left = (x > 0.95 and y < 0.05)
        if near_origin or near_top_right or near_bottom_left or near_top_left:
            corner_count += 1

    # If most points are at corners, it's garbage
    if corner_count >= len(xs) * 0.6 and len(xs) <= 8:
        return True

    return False


def analyze_label_file(label_path):
    """
    Analyze a single label file and classify each line.

    Returns:
        dict with:
            - total_lines: int
            - garbage_lines: list of (line_idx, line_content)
            - valid_lines: list of (line_idx, line_content)
            - empty: bool
            - file_size: int
    """
    result = {
        'total_lines': 0,
        'garbage_lines': [],
        'valid_lines': [],
        'empty': False,
        'file_size': label_path.stat().st_size,
    }

    content = label_path.read_text(encoding='utf-8').strip()

    if not content:
        result['empty'] = True
        return result

    lines = content.split('\n')
    result['total_lines'] = len(lines)

    for idx, line in enumerate(lines):
        line = line.strip()
        if not line:
            continue
        parts = line.split()
        if is_garbage_polygon(parts):
            result['garbage_lines'].append((idx, line))
        else:
            result['valid_lines'].append((idx, line))

    return result


def audit_split(split_name, split_dir):
    """Audit all labels in a dataset split."""
    images_dir = split_dir / "images"
    labels_dir = split_dir / "labels"

    if not images_dir.exists() or not labels_dir.exists():
        print(f"  [SKIP] {split_name}: missing images/ or labels/ directory")
        return {}

    image_files = sorted([f for f in images_dir.iterdir() if f.suffix.lower() in ('.jpg', '.jpeg', '.png', '.bmp')])
    label_files = sorted([f for f in labels_dir.iterdir() if f.suffix == '.txt' and f.name != 'labels.cache'])

    image_stems = {f.stem for f in image_files}
    label_stems = {f.stem for f in label_files}

    # Check pairing
    missing_labels = image_stems - label_stems
    orphan_labels = label_stems - image_stems

    if missing_labels:
        print(f"  [WARN] {split_name}: {len(missing_labels)} images missing labels")
    if orphan_labels:
        print(f"  [WARN] {split_name}: {len(orphan_labels)} orphan labels (no matching image)")

    # Analyze each label file
    results = {}
    for lf in label_files:
        results[lf] = analyze_label_file(lf)

    return results


def print_audit_report(all_results):
    """Print a comprehensive audit report."""
    total_files = 0
    garbage_only_files = 0
    mixed_files = 0
    valid_only_files = 0
    empty_files = 0
    total_garbage_lines = 0
    total_valid_lines = 0

    garbage_only_list = []
    mixed_list = []

    for split_name, results in all_results.items():
        for label_path, analysis in results.items():
            total_files += 1
            has_garbage = len(analysis['garbage_lines']) > 0
            has_valid = len(analysis['valid_lines']) > 0

            total_garbage_lines += len(analysis['garbage_lines'])
            total_valid_lines += len(analysis['valid_lines'])

            if analysis['empty']:
                empty_files += 1
            elif has_garbage and has_valid:
                mixed_files += 1
                mixed_list.append((split_name, label_path, analysis))
            elif has_garbage and not has_valid:
                garbage_only_files += 1
                garbage_only_list.append((split_name, label_path, analysis))
            elif has_valid:
                valid_only_files += 1

    print()
    print("=" * 70)
    print("  LABEL AUDIT REPORT")
    print("=" * 70)
    print()
    print(f"  Total label files scanned:     {total_files}")
    print(f"  Valid-only files (good):        {valid_only_files}")
    print(f"  Garbage-only files (bad):       {garbage_only_files}")
    print(f"  Mixed files (garbage + valid):  {mixed_files}")
    print(f"  Empty files:                    {empty_files}")
    print()
    print(f"  Total garbage polygon lines:    {total_garbage_lines}")
    print(f"  Total valid polygon lines:      {total_valid_lines}")
    print()

    if garbage_only_list:
        print("-" * 70)
        print(f"  GARBAGE-ONLY FILES ({len(garbage_only_list)} files)")
        print("  These have ONLY full-image garbage polygons, no real annotations.")
        print("  FIX: Will be replaced with empty files (= no scratch detected).")
        print("-" * 70)
        for split_name, lp, analysis in garbage_only_list[:10]:
            print(f"    [{split_name}] {lp.name} ({analysis['file_size']} bytes, {len(analysis['garbage_lines'])} garbage lines)")
        if len(garbage_only_list) > 10:
            print(f"    ... and {len(garbage_only_list) - 10} more")
        print()

    if mixed_list:
        print("-" * 70)
        print(f"  MIXED FILES ({len(mixed_list)} files)")
        print("  These have BOTH garbage AND valid polygons.")
        print("  FIX: Will remove garbage lines, keep valid ones.")
        print("-" * 70)
        for split_name, lp, analysis in mixed_list[:10]:
            print(f"    [{split_name}] {lp.name}")
            print(f"       {len(analysis['valid_lines'])} valid + {len(analysis['garbage_lines'])} garbage lines")
        if len(mixed_list) > 10:
            print(f"    ... and {len(mixed_list) - 10} more")
        print()

    print("=" * 70)

    return garbage_only_list, mixed_list


def fix_labels(all_results, backup=True):
    """
    Fix all garbage labels:
    - Garbage-only files → empty file (background/negative image)
    - Mixed files → remove garbage lines, keep valid ones
    """
    fixed_count = 0
    backup_dir = DATASET_ROOT / "_label_backup"

    if backup:
        backup_dir.mkdir(exist_ok=True)
        print(f"\n  Backing up labels to: {backup_dir}")

    for split_name, results in all_results.items():
        for label_path, analysis in results.items():
            has_garbage = len(analysis['garbage_lines']) > 0
            has_valid = len(analysis['valid_lines']) > 0

            if not has_garbage:
                continue

            # Backup
            if backup:
                split_backup = backup_dir / split_name
                split_backup.mkdir(exist_ok=True)
                shutil.copy2(label_path, split_backup / label_path.name)

            if has_garbage and not has_valid:
                # Garbage-only: make empty file (negative/background image)
                label_path.write_text('', encoding='utf-8')
                fixed_count += 1
            elif has_garbage and has_valid:
                # Mixed: keep only valid lines
                valid_content = '\n'.join(line for _, line in analysis['valid_lines']) + '\n'
                label_path.write_text(valid_content, encoding='utf-8')
                fixed_count += 1

    return fixed_count


def main():
    parser = argparse.ArgumentParser(description="Audit and fix YOLO segmentation labels")
    parser.add_argument("--dry-run", action="store_true",
                        help="Only report issues, don't fix anything")
    parser.add_argument("--fix", action="store_true", default=True,
                        help="Fix issues (default: True)")
    parser.add_argument("--no-backup", action="store_true",
                        help="Don't backup original labels")
    args = parser.parse_args()

    print("=" * 70)
    print("  YOLO Label Audit & Fix Tool")
    print("=" * 70)
    print(f"  Dataset: {DATASET_ROOT}")
    print(f"  Mode: {'DRY RUN (report only)' if args.dry_run else 'FIX MODE'}")
    print()

    # Audit all splits
    all_results = {}
    for split_name in ['train', 'valid', 'test']:
        split_dir = DATASET_ROOT / split_name
        if split_dir.exists():
            print(f"  Scanning {split_name}...")
            all_results[split_name] = audit_split(split_name, split_dir)
            print(f"    Found {len(all_results[split_name])} label files")
        else:
            print(f"  [SKIP] {split_name}: directory not found")

    # Print report
    garbage_only, mixed = print_audit_report(all_results)

    if args.dry_run:
        print("\n  DRY RUN complete. No files were modified.")
        print("  Run with --fix to apply corrections.")
        return

    # Fix labels
    total_bad = len(garbage_only) + len(mixed)
    if total_bad == 0:
        print("\n  No garbage labels found! Dataset is clean.")
        return

    print(f"\n  Fixing {total_bad} label files...")
    fixed = fix_labels(all_results, backup=not args.no_backup)
    print(f"  Fixed {fixed} files.")

    # Delete label caches
    print("\n  Deleting stale label caches...")
    for split_name in ['train', 'valid', 'test']:
        cache_path = DATASET_ROOT / split_name / "labels.cache"
        if cache_path.exists():
            cache_path.unlink()
            print(f"    Deleted: {cache_path.name} ({split_name})")

    print("\n" + "=" * 70)
    print("  LABEL CLEANUP COMPLETE")
    print("=" * 70)
    print(f"  Files fixed:        {fixed}")
    print(f"  Caches deleted:     yes")
    print(f"  Backup location:    {DATASET_ROOT / '_label_backup'}")
    print()
    print("  Next step: Retrain the model with cleaned labels.")
    print("=" * 70)


if __name__ == "__main__":
    main()
