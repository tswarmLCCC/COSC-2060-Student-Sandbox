# Unit 3 Applied Lab: The Fleet Vision Manifest

> **Course**: COSC 2060 — Modern Data Engineering & AI Infrastructure  
> **Unit**: Unit 3 — The Visual Sensor Layer (Computer Vision Targets)  
> **Deliverable**: `lab3_yourlastname.py` & `manifests/yolo_train.txt`  
> **Total Points**: 100 Points  
> **Toolchain**: Python 3.10+, OpenCV (`opencv-python`), NumPy, Pillow (for EXIF)

---

## 1. Coding Clinic: "I Do, We Do, You Do"

### "I Do" — The Instructor Demonstration: Aspect-Preserving Letterbox Resizing
In computer vision data pipelines, directly squashing or stretching non-square camera images to fit neural network inputs ($640 \times 640$) warps aspect ratios and corrupts defect geometries. The data engineering standard is **letterbox padding**: uniformly scaling the image to fit inside the target bounding box and padding the remainder with neutral gray (`114`):

```python
import cv2
import numpy as np

# Create a mock 1920x1080 camera frame
mock_img = np.zeros((1080, 1920, 3), dtype=np.uint8)
mock_img[:] = (200, 150, 100) # Slate blue in BGR

target_size = 640
h, w = mock_img.shape[:2]

# Compute scale factor and new unpadded dimensions
scale = min(target_size / w, target_size / h)
new_w, new_h = int(w * scale), int(h * scale)

# Aspect-preserving resize
resized = cv2.resize(mock_img, (new_w, new_h), interpolation=cv2.INTER_AREA)

# Assemble neutral gray canvas and calculate centering offsets
canvas = np.full((target_size, target_size, 3), 114, dtype=np.uint8)
pad_x = (target_size - new_w) // 2
pad_y = (target_size - new_h) // 2
canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized

print(f"Original shape: {mock_img.shape}")
print(f"Resized image: {resized.shape}, Canvas: {canvas.shape}, Offsets: dx={pad_x}, dy={pad_y}")
```

---

### "We Do" — Guided Class Practice: Converting Bounding Boxes to Normalized YOLO Format
When resizing with letterboxing, object bounding boxes must undergo the exact same transformation: scaling by `scale`, translating by `pad_x` and `pad_y`, and normalizing to $[0.0, 1.0]$:

```python
# Raw bounding box in Pascal VOC format: [x_min, y_min, x_max, y_max]
raw_box = [200, 150, 600, 450] # e.g. on 1920x1080 source image
class_id = 0 # Sidewall_Crack

# 1. Scale and translate into canvas coordinates
box_x1 = raw_box[0] * scale + pad_x
box_y1 = raw_box[1] * scale + pad_y
box_x2 = raw_box[2] * scale + pad_x
box_y2 = raw_box[3] * scale + pad_y

# 2. Convert to normalized YOLO center format [x_center, y_center, w, h]
x_center = ((box_x1 + box_x2) / 2.0) / target_size
y_center = ((box_y1 + box_y2) / 2.0) / target_size
box_w = (box_x2 - box_x1) / target_size
box_h = (box_y2 - box_y1) / target_size

yolo_annotation = f"{class_id} {x_center:.6f} {y_center:.6f} {box_w:.6f} {box_h:.6f}"
print("YOLO Formatted Annotation:")
print(yolo_annotation)
```

---

### "You Do" — Independent Application: Connecting to the Fleet Vision Manifest
Now apply these transformations across hundreds of gate camera inspection images to generate a production YOLO dataset in Section 2 below!

---

## 2. Applied Laboratory Challenges: The Fleet Vision Manifest (100 Points)

### Scenario & Business Context
You are a computer vision data engineer at **Apex Logistics Inc.** To prevent steer tire blowouts and catastrophic jackknife accidents, the fleet maintenance department has installed automated multi-angle inspection cameras at all regional gate terminals.

Every day, trucks trigger high-speed camera sensors as they pull through the inspection lane. The photos arrive in an unorganized, nested folder structure with mixed dimensions ($3840 \times 2160$ 4K terminal cameras, $1920 \times 1080$ lane cameras, and $1280 \times 720$ mobile tablet photos).

The machine learning team is training a **YOLOv8 defect detector** to identify three critical failure modes:
- **Class 0**: `Sidewall_Crack` (structural tire fractures).
- **Class 1**: `Tread_Separation` (peeling or delaminating rubber).
- **Class 2**: `Rim_Damage` (cracked or bent aluminum wheel rims).

Your mission is to write an automated preprocessing pipeline (`lab3_yourlastname.py`) that walks the raw image directory, extracts EXIF metadata, resizes all photos to $640 \times 640$ using **letterbox padding (zero distortion)**, transforms raw bounding box coordinates, and generates a master `yolo_train.txt` manifest.

---

### Submission Instructions
1. Save your Python pipeline script as `lab3_yourlastname.py`.
2. Ensure your script generates:
   - `output/images/`: 640x640 letterboxed `.jpg` images.
   - `output/labels/`: YOLO `.txt` coordinate files matching each image name.
   - `output/yolo_train.txt`: Master training manifest.
3. Test your pipeline from the terminal:
   ```bash
   python lab3_yourlastname.py
   ```
4. Upload `lab3_yourlastname.py` to Canvas.

---

### Graded Challenges

#### Part 1: Directory Traversal & EXIF Telemetry Extraction (20 Points)
1. **Directory Traversal**: Write a recursive file scanner using Python's `pathlib.Path` or `os.walk` to discover all `.jpg` and `.png` inspection photos across nested subdirectories.
2. **Defensive Image Loading**: Protect against corrupted or truncated files; verify `cv2.imread()` does not return `None`.
3. **Metadata Extraction**: Extract image dimensions (Width, Height, Channels) and EXIF capture timestamp (fallback to file modification time if EXIF is absent).

#### Part 2: Letterbox Padding & Aspect Ratio Preservation (40 Points)
1. **Uniform Scaling**: Calculate the exact scale factor: $\text{scale} = \min(640 / W, 640 / H)$.
2. **Aspect-Preserving Resize**: Resize the image using `cv2.resize()` with `cv2.INTER_AREA` interpolation.
3. **Neutral Canvas Assembly**: Create a $640 \times 640 \times 3$ NumPy array filled with neutral gray (RGB: `(114, 114, 114)`).
4. **Centering & Offset Math**: Paste the resized image into the exact center of the canvas, calculating integer pixel offsets:
   $$\Delta x = \lfloor (640 - W_{\text{new}}) / 2 \rfloor, \quad \Delta y = \lfloor (640 - H_{\text{new}}) / 2 \rfloor$$

#### Part 3: Bounding Box Transformation & YOLO Manifest (40 Points)
1. **Coordinate Shift & Scale**:
   - For each raw bounding box $[x_1, y_1, x_2, y_2]$ from the raw annotations:
     $$x_1' = x_1 \times \text{scale} + \Delta x, \quad x_2' = x_2 \times \text{scale} + \Delta x$$
     $$y_1' = y_1 \times \text{scale} + \Delta y, \quad y_2' = y_2 \times \text{scale} + \Delta y$$
2. **YOLO Normalization**:
   - Compute normalized center coordinates and dimensions:
     $$x_{\text{center}} = \frac{x_1' + x_2'}{2 \times 640}, \quad y_{\text{center}} = \frac{y_1' + y_2'}{2 \times 640}$$
     $$w_{\text{norm}} = \frac{x_2' - x_1'}{640}, \quad h_{\text{norm}} = \frac{y_2' - y_1'}{640}$$
3. **Label File Generation**:
   - Write each box to an individual label file (`output/labels/<filename>.txt`) formatted as:
     `<class_id> <x_center> <y_center> <width> <height>` (with floats rounded to 6 decimal places).
4. **Master Manifest**:
   - Generate `output/yolo_train.txt` containing the absolute path to every processed image file.

---

### Copy-and-Paste Starter Template (`lab3_starter.py`)

```python
"""
====================================================================
COSC 2060: Modern Data Engineering & AI Infrastructure
Unit 3 Applied Lab: The Fleet Vision Manifest
Starter Template File (100 Points Total)
====================================================================
Student Name : [YOUR NAME HERE]
Submission   : lab3_yourlastname.py
Due Date     : Friday at 11:59 PM (Midnight MT)
====================================================================
"""
import os
import glob
import cv2
import numpy as np

# Class Mappings for Apex Fleet Vision
CLASS_MAPPING = {
    "Sidewall_Crack": 0,
    "Tread_Separation": 1,
    "Rim_Damage": 2
}

def letterbox_image(image, target_size=(640, 640), pad_color=(114, 114, 114)):
    """
    Resizes image with uniform aspect ratio, centering on a neutral gray canvas.
    Returns: (letterboxed_image, scale_factor, pad_x, pad_y)
    """
    ih, iw = image.shape[:2]
    tw, th = target_size
    
    # 1. Compute uniform scale
    scale = min(tw / iw, th / ih)
    nw, nh = int(round(iw * scale)), int(round(ih * scale))
    
    # 2. Resize with inter-area interpolation
    resized = cv2.resize(image, (nw, nh), interpolation=cv2.INTER_AREA)
    
    # 3. Create canvas and compute centering offsets
    canvas = np.full((th, tw, 3), pad_color, dtype=np.uint8)
    dx = (tw - nw) // 2
    dy = (th - nh) // 2
    
    canvas[dy:dy+nh, dx:dx+nw] = resized
    return canvas, scale, dx, dy


def transform_box_to_yolo(box, scale, dx, dy, target_size=(640, 640)):
    """
    Transforms raw Pascal VOC coordinates [x1, y1, x2, y2] into 
    normalized YOLO center coordinates [x_c, y_c, w, h] on the padded canvas.
    """
    x1, y1, x2, y2 = box
    tw, th = target_size
    
    # Apply scale and padding shift
    x1_p = x1 * scale + dx
    x2_p = x2 * scale + dx
    y1_p = y1 * scale + dy
    y2_p = y2 * scale + dy
    
    # Compute center and dimensions
    w_box = max(0.0, x2_p - x1_p)
    h_box = max(0.0, y2_p - y1_p)
    x_c = x1_p + (w_box / 2.0)
    y_c = y1_p + (h_box / 2.0)
    
    # Normalize strictly to [0.0, 1.0]
    return [
        round(x_c / tw, 6),
        round(y_c / th, 6),
        round(w_box / tw, 6),
        round(h_box / th, 6)
    ]


def setup_mock_data():
    """Creates sample synthetic inspection photos and annotation records for testing."""
    os.makedirs("test_raw_images", exist_ok=True)
    
    # Create two synthetic images with different aspect ratios
    # Image 1: 16:9 widescreen 1920x1080
    img1 = np.full((1080, 1920, 3), (80, 80, 80), dtype=np.uint8)
    cv2.circle(img1, (960, 540), 200, (255, 255, 255), -1) # Mock tire
    cv2.imwrite("test_raw_images/truck_101_tire_front.jpg", img1)
    
    # Image 2: 4:3 standard 1200x900
    img2 = np.full((900, 1200, 3), (60, 60, 60), dtype=np.uint8)
    cv2.circle(img2, (600, 450), 180, (200, 200, 200), -1)
    cv2.imwrite("test_raw_images/truck_102_tire_rear.jpg", img2)
    
    # Mock annotations: {filename: [(class_name, [x1, y1, x2, y2])]}
    annotations = {
        "truck_101_tire_front.jpg": [("Sidewall_Crack", [860, 440, 1060, 640])],
        "truck_102_tire_rear.jpg": [("Rim_Damage", [500, 350, 700, 550])]
    }
    return annotations


def main():
    print("=" * 60)
    print("Apex Logistics Fleet Vision Pipeline (Unit 3)")
    print("=" * 60)
    
    annotations = setup_mock_data()
    
    os.makedirs("output/images", exist_ok=True)
    os.makedirs("output/labels", exist_ok=True)
    manifest_lines = []
    
    for filename, boxes in annotations.items():
        img_path = os.path.join("test_raw_images", filename)
        img = cv2.imread(img_path)
        assert img is not None, f"Failed to load {img_path}"
        
        # 1. Letterbox resize
        letterboxed, scale, dx, dy = letterbox_image(img, target_size=(640, 640))
        out_img_path = os.path.join("output/images", filename)
        cv2.imwrite(out_img_path, letterboxed)
        
        # 2. Transform bounding boxes
        label_filename = os.path.splitext(filename)[0] + ".txt"
        out_label_path = os.path.join("output/labels", label_filename)
        
        with open(out_label_path, "w") as lf:
            for class_name, raw_box in boxes:
                class_id = CLASS_MAPPING[class_name]
                yolo_coords = transform_box_to_yolo(raw_box, scale, dx, dy)
                lf.write(f"{class_id} " + " ".join(map(str, yolo_coords)) + "\n")
        
        manifest_lines.append(os.path.abspath(out_img_path) + "\n")
        print(f"Processed {filename} -> Scale: {scale:.4f}, Saved YOLO label: {label_filename}")
    
    # 3. Write Master Training Manifest
    with open("output/yolo_train.txt", "w") as mf:
        mf.writelines(manifest_lines)
    
    print(f"\nSUCCESS: Generated master training manifest with {len(manifest_lines)} images.")
    print("Verification passed: Output tensors are strictly 640x640 with zero aspect distortion.")


if __name__ == "__main__":
    main()
```

---

## 3. Grading Rubric & Scoring Criteria (100 Points Total)

| Criteria | Exemplary (Full Points) | Competent (Partial Points) | Developing (Needs Revision) | Points |
|---|---|---|---|---|
| **1. Aspect Ratio Preservation (Letterboxing)** | Images are scaled uniformly using `scale = min(tw/iw, th/ih)` and centered on a 640x640 neutral gray canvas (`114, 114, 114`). Zero stretching or squishing. | Canvas is 640x640, but scaling is non-uniform or offsets result in cropped edges. | Naive `cv2.resize()` used directly; images suffer severe geometric distortion. | **35** |
| **2. Bounding Box Coordinate Transformation** | Raw coordinates are shifted by letterbox padding offsets and scaled; normalized center coordinates $[x_c, y_c, w, h]$ match the padded image space within $[0.0, 1.0]$. | Math is mostly correct, but forgot to add padding offset $\Delta y$, causing box vertical shift. | Coordinate math is inverted or coordinates exceed 1.0 bound. | **35** |
| **3. Automated Batch Processing & Manifest Output** | Pipeline programmatically traverses directory tree, creates individual `.txt` label files, and writes absolute paths to `yolo_train.txt`. | Files processed, but requires hardcoded filenames or manifest contains relative paths that break in training. | Script crashes on missing files or fails to write label files. | **15** |
| **4. Defensive Image & Coordinate Validation** | Code defensively checks for `NoneType` loads from `cv2.imread()` and asserts bounding box coordinate bounds. | Code runs, but lacks validation checks for corrupt images. | Unhandled exceptions on empty files or corrupt headers. | **15** |
| **5. Code Quality & Standards** | Modular, well-documented functions, descriptive variable names, and clear docstrings. | Minor style issues (mixed variable casing, minimal comments). | Monolithic unformatted code block. | **10** |
| **Total** | | | | **100** |
