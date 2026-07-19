# Roboflow Annotation Guidelines — Scratch Detection

## Quick Reference Card

Send this to your friend who will annotate the images on Roboflow.

---

## ✅ Setup

1. Go to [roboflow.com](https://roboflow.com) → Sign in
2. **Create Project**:
   - Name: `Can Scratch Detection`
   - Type: **Instance Segmentation**
3. Upload all images (scratch + no-scratch)

---

## 🏷️ Annotation Rules

### Class
Create exactly **ONE** class: `scratch`

### Tool
Use **Polygon Tool** only (NOT bounding box)

### How to Annotate

| Scenario | Action |
|----------|--------|
| Image has a scratch | Draw a polygon tightly around it |
| Image has multiple scratches | Draw **separate** polygon for each |
| Image has NO scratch | **Leave completely unannotated** |

### ✅ DO
- Zoom in before annotating
- Follow the scratch boundary closely
- Close every polygon properly
- Annotate each scratch separately

### ❌ DON'T
- Don't use bounding boxes
- Don't include large background areas in the polygon
- Don't merge separate scratches into one polygon
- Don't annotate clean images
- Don't create multiple classes

---

## 📐 Polygon Drawing Tips

```
Good ✅ (tight)          Bad ❌ (too loose)

  x---x                 x-----------x
  |   |                 |           |
  x---x                 |  scratch  |
                        |           |
                        x-----------x
```

1. Click around the scratch edge
2. Use 8–20 points per scratch
3. Click the first point to close
4. Review: does the polygon match the scratch shape?

---

## 📊 Dataset Split

After annotating, set the split:

| Split | Percentage |
|-------|-----------|
| Training | 70% |
| Validation | 20% |
| Test | 10% |

Roboflow can do this automatically.

---

## 📤 Export Settings

1. Click **Generate** → Choose version settings:
   - Preprocessing: Auto-Orient, Resize to **640×640**
   - Augmentation: Horizontal Flip, Rotation ±15°
2. Click **Export**
3. Format: **YOLOv8 Segmentation**
4. Download the ZIP

---

## 📁 Expected Export Structure

```
dataset/
├── train/
│   ├── images/    (*.jpg)
│   └── labels/    (*.txt)
├── valid/
│   ├── images/
│   └── labels/
├── test/
│   ├── images/
│   └── labels/
└── data.yaml
```

---

## ✅ Final Checklist

- [ ] Only one class: `scratch`
- [ ] All scratches annotated with polygons
- [ ] Clean images have NO annotations
- [ ] Polygons are tight around scratches
- [ ] Separate scratches have separate polygons
- [ ] All polygons are closed
- [ ] Dataset split: 70/20/10
- [ ] Exported as YOLOv8 Segmentation
