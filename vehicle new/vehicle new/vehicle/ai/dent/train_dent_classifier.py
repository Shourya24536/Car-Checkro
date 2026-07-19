import os
import shutil
import random
from ultralytics import YOLO

# Define paths
SRC_DIR = os.path.dirname(os.path.abspath(__file__)) # vehicle/ai/dent
PROJECT_ROOT = os.path.dirname(os.path.dirname(SRC_DIR)) # vehicle
WORKSPACE_ROOT = os.path.dirname(PROJECT_ROOT) # vehicle new

RAW_DENT_DIR = os.path.join(WORKSPACE_ROOT, "Dent")
DATASET_DIR = os.path.join(SRC_DIR, "dataset")

def prepare_dataset():
    """
    Splits raw images in workspace_root/Dent/ into train/val sets (80/20 split)
    and formats them for YOLO classification.
    """
    print(f"[Dataset Preparation] Scanning raw Dent dataset at: {RAW_DENT_DIR}")
    if not os.path.exists(RAW_DENT_DIR):
        print(f"Error: Raw dent dataset directory not found at {RAW_DENT_DIR}!")
        return False
        
    categories = ["Major Dent", "Minor Dent", "NO Dent"]
    
    # Recreate dataset directory structure
    for split in ["train", "val"]:
        for cat in categories:
            # Replace space with underscore for class naming consistency
            cat_name = cat.replace(" ", "_")
            dir_path = os.path.join(DATASET_DIR, split, cat_name)
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path)
            os.makedirs(dir_path, exist_ok=True)
            
    # Perform split
    for cat in categories:
        cat_name = cat.replace(" ", "_")
        src_cat_dir = os.path.join(RAW_DENT_DIR, cat)
        if not os.path.exists(src_cat_dir):
            print(f"Warning: Category folder {cat} not found in Dent/")
            continue
            
        all_files = [f for f in os.listdir(src_cat_dir) if f.lower().endswith(('.jpeg', '.jpg', '.png'))]
        random.shuffle(all_files)
        
        split_idx = int(len(all_files) * 0.8)
        train_files = all_files[:split_idx]
        val_files = all_files[split_idx:]
        
        print(f" - {cat_name}: {len(train_files)} train, {len(val_files)} val")
        
        # Copy files to train
        for f in train_files:
            shutil.copy(os.path.join(src_cat_dir, f), os.path.join(DATASET_DIR, "train", cat_name, f))
            
        # Copy files to val
        for f in val_files:
            shutil.copy(os.path.join(src_cat_dir, f), os.path.join(DATASET_DIR, "val", cat_name, f))
            
    print(f"[Dataset Preparation] Dataset ready at: {DATASET_DIR}")
    return True

def train_classifier():
    if not prepare_dataset():
        return
        
    print("[Trainer] Initializing YOLOv11 classification model training...")
    # Base model. YOLOv11 classification model base
    # yolo11n-cls.pt will automatically download if not present.
    # We will train for 15 epochs for quick convergence (usually more than enough for simple features).
    model = YOLO("yolo11n-cls.pt")
    
    print("[Trainer] Starting model.train on dataset...")
    results = model.train(
        data=DATASET_DIR,
        epochs=15,
        imgsz=224,
        batch=32,
        workers=2,
        device=0 if os.environ.get("CUDA_VISIBLE_DEVICES") or shutil.which("nvidia-smi") else "cpu",
        project=os.path.join(SRC_DIR, "runs"),
        name="dent_classifier"
    )
    
    # Save the best model weight file directly to vehicle/ai/dent/best.pt
    best_weight_src = os.path.join(SRC_DIR, "runs", "dent_classifier", "weights", "best.pt")
    best_weight_dest = os.path.join(SRC_DIR, "best.pt")
    
    if os.path.exists(best_weight_src):
        shutil.copy(best_weight_src, best_weight_dest)
        print(f"[Trainer] Model trained successfully! Weights saved to: {best_weight_dest}")
    else:
        print("[Trainer] Training finished, but best.pt weight file could not be found.")

if __name__ == "__main__":
    train_classifier()
