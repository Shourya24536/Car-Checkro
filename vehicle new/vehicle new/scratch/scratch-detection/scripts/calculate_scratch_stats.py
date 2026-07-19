"""
Calculate Dataset Scratch Statistics (Label Distribution)
=========================================================
Calculates detailed scratch statistics from YOLO polygon annotations.
"""

import sys
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

PROJECT_ROOT = Path(__file__).resolve().parent.parent

def polygon_area(coords):
    """Calculate the area of a polygon using the Shoelace formula."""
    xs = coords[0::2]
    ys = coords[1::2]
    
    # Shoelace formula
    return 0.5 * abs(sum(xs[i]*ys[i+1] - xs[i+1]*ys[i] for i in range(len(xs)-1)) + xs[-1]*ys[0] - xs[0]*ys[-1])

def analyze_labels_split(split_name, labels_dir):
    """Analyze labels in a split."""
    if not labels_dir.exists():
        return None
        
    label_files = [f for f in labels_dir.iterdir() if f.suffix == '.txt' and f.name != 'labels.cache']
    
    total_images = len(label_files)
    images_with_zero_scratches = 0
    scratches = []
    
    for lf in label_files:
        content = lf.read_text(encoding='utf-8').strip()
        if not content:
            images_with_zero_scratches += 1
            continue
            
        lines = content.split('\n')
        has_scratch = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) < 7:
                continue
                
            coords = [float(p) for p in parts[1:]]
            area = polygon_area(coords)
            scratches.append({
                "file": lf.name,
                "area_pct": area * 100
            })
            has_scratch = True
            
        if not has_scratch:
            images_with_zero_scratches += 1
            
    return {
        "total_images": total_images,
        "zero_scratch_images": images_with_zero_scratches,
        "scratches": scratches
    }

def main():
    dataset_dir = PROJECT_ROOT / "dataset"
    splits = ['train', 'valid', 'test']
    
    all_scratches = []
    total_images = 0
    total_zero_scratches = 0
    
    print("=" * 70)
    print("  LABEL DISTRIBUTION & SCRATCH STATISTICS")
    print("=" * 70)
    
    for split in splits:
        labels_dir = dataset_dir / split / "labels"
        stats = analyze_labels_split(split, labels_dir)
        if stats:
            total_images += stats["total_images"]
            total_zero_scratches += stats["zero_scratch_images"]
            all_scratches.extend(stats["scratches"])
            
            print(f"\n  Split: {split.upper()}")
            print(f"    Images:                    {stats['total_images']}")
            print(f"    Images with zero scratches: {stats['zero_scratch_images']}")
            print(f"    Total scratches:            {len(stats['scratches'])}")
            
            if stats["scratches"]:
                areas = [s["area_pct"] for s in stats["scratches"]]
                print(f"    Avg scratch size:          {sum(areas)/len(areas):.4f}% of image")
                print(f"    Smallest scratch size:     {min(areas):.4f}% of image")
                print(f"    Largest scratch size:      {max(areas):.4f}% of image")
            else:
                print("    No scratches found in this split.")
                
    print("\n" + "=" * 70)
    print("  OVERALL DATASET STATISTICS")
    print("=" * 70)
    print(f"  Total Images:               {total_images}")
    print(f"  Images with Zero Scratches: {total_zero_scratches}")
    print(f"  Images with Scratches:      {total_images - total_zero_scratches}")
    print(f"  Total Scratches detected:   {len(all_scratches)}")
    
    if all_scratches:
        overall_areas = [s["area_pct"] for s in all_scratches]
        print(f"  Average scratch size:       {sum(overall_areas)/len(overall_areas):.4f}% of image")
        print(f"  Smallest scratch:           {min(overall_areas):.4f}% of image")
        print(f"  Largest scratch:            {max(overall_areas):.4f}% of image")
        
        # Sort scratches to find files
        all_scratches_sorted = sorted(all_scratches, key=lambda x: x["area_pct"])
        print(f"  Smallest scratch file:      {all_scratches_sorted[0]['file']} ({all_scratches_sorted[0]['area_pct']:.4f}%)")
        print(f"  Largest scratch file:       {all_scratches_sorted[-1]['file']} ({all_scratches_sorted[-1]['area_pct']:.4f}%)")
    else:
        print("  No scratches in entire dataset.")
        
    print(f"  Class Imbalance Ratio:      {total_zero_scratches/total_images*100:.1f}% clean vs {(total_images-total_zero_scratches)/total_images*100:.1f}% scratched")
    print("=" * 70)

if __name__ == "__main__":
    main()
