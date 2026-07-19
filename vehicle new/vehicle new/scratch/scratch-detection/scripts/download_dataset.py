"""
YOLO11 Segmentation — Dataset Download Script
==============================================
Downloads the annotated dataset from Roboflow in YOLOv8 format and organizes it.

Usage:
    python scripts/download_dataset.py --api-key <YOUR_KEY> --project <PROJECT_ID>
"""

import argparse
import sys
import shutil
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def parse_args():
    parser = argparse.ArgumentParser(description="Download dataset from Roboflow")
    parser.add_argument("--api-key", type=str, required=True, help="Roboflow Private API Key")
    parser.add_argument("--project", type=str, required=True, help="Roboflow Project ID")
    parser.add_argument("--version", type=int, default=None, help="Specific project version (default: latest)")
    return parser.parse_args()


def download_and_setup(api_key, project_id, version_num=None):
    """Download the dataset and organize it in the project root."""
    try:
        from roboflow import Roboflow
    except ImportError:
        print("[ERROR] Roboflow package not installed. Run: pip install roboflow")
        sys.exit(1)

    print("=" * 60)
    print("  YOLO11 Scratch Detection — Dataset Downloader")
    print("=" * 60)
    print(f"  Project ID: {project_id}")
    print("=" * 60)
    print()

    print("[INFO] Connecting to Roboflow API...")
    rf = Roboflow(api_key=api_key)
    
    try:
        workspace = rf.workspace()
        print(f"[INFO] Connected to Workspace: {workspace.name}")
    except Exception as e:
        print(f"[ERROR] Failed to connect to Roboflow workspace. Check your API key. Details: {e}")
        sys.exit(1)

    try:
        project = workspace.project(project_id)
        print(f"[INFO] Found Project: {project.name}")
    except Exception as e:
        print(f"[ERROR] Failed to access project '{project_id}'. Details: {e}")
        sys.exit(1)

    # Determine version to download
    if version_num is None:
        print("[INFO] Fetching versions list...")
        versions = project.versions()
        if not versions:
            print("[ERROR] No versions found. Please generate a dataset version on Roboflow first.")
            sys.exit(1)
        # Select the latest version (usually first in the list)
        version_obj = versions[0]
        version_num = version_obj.version
        print(f"[INFO] Selecting latest version: Version {version_num} ({version_obj.name})")
    else:
        print(f"[INFO] Selecting user-specified version: Version {version_num}")

    # Create dataset directory if it doesn't exist
    dest_path = PROJECT_ROOT / "dataset"
    dest_path.mkdir(parents=True, exist_ok=True)

    # Download in yolov8 format (which includes the polygon masks for segmentation)
    print(f"[INFO] Downloading version {version_num} in YOLOv8 format...")
    try:
        downloaded = project.version(version_num).download("yolov8")
        src_path = Path(downloaded.location)
    except Exception as e:
        print(f"[ERROR] Download failed. Details: {e}")
        sys.exit(1)

    print(f"[INFO] Organizing dataset splits...")
    
    # Overwrite folders
    for split in ["train", "valid", "test"]:
        split_dest = dest_path / split
        if split_dest.exists():
            shutil.rmtree(split_dest)
        
        split_src = src_path / split
        if split_src.exists():
            shutil.move(str(split_src), str(split_dest))
            print(f"      - Prepared dataset/{split}/")
        else:
            print(f"      - [WARNING] Split '{split}' not found in the download.")

    # Overwrite data.yaml
    yaml_src = src_path / "data.yaml"
    yaml_dest = dest_path / "data.yaml"
    if yaml_src.exists():
        shutil.copy2(str(yaml_src), str(yaml_dest))
        print("      - Overwrote data.yaml")
    else:
        print("      - [WARNING] data.yaml not found in the download.")

    # Cleanup temporary folder
    print("[INFO] Cleaning up temporary download files...")
    try:
        shutil.rmtree(src_path)
    except Exception as e:
        print(f"      - [WARNING] Cleanup failed: {e}")

    print()
    print("=" * 60)
    print("  Dataset Ready!")
    print("=" * 60)
    print("  Next steps:")
    print("    1. Run verification:  python scripts/verify_dataset.py --data dataset/data.yaml")
    print("    2. Start training:    python scripts/train.py --model yolo11n-seg.pt --epochs 100")
    print("=" * 60)


if __name__ == "__main__":
    args = parse_args()
    download_and_setup(args.api_key, args.project, args.version)
