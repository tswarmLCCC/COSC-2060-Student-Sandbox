# Unit 3 Lab Grading Rubric: The Visual Sensor Layer & YOLO Coordinate Math

> **Course**: COSC 2060 — Modern Data Engineering & AI Infrastructure  
> **Assessment**: Unit 3 Applied Engineering Lab (`lab3_yourlastname.py`)  
> **Total Points**: 100 Points (Canvas SpeedGrader)

---

| Criteria | Exemplary (Full Points) | Competent (Partial Points) | Developing (Needs Revision) | Points |
|---|---|---|---|---|
| **1. Aspect Ratio Preservation (Letterboxing)** | Images are scaled uniformly using `scale = min(tw/iw, th/ih)` and centered on a 640x640 neutral gray canvas (`114, 114, 114`). Zero stretching or squishing. | Canvas is 640x640, but scaling is non-uniform or offsets result in cropped edges. | Naive `cv2.resize()` used directly; images suffer severe geometric distortion. | **35** |
| **2. Bounding Box Coordinate Transformation** | Raw coordinates are shifted by letterbox padding offsets and scaled; normalized center coordinates $[x_c, y_c, w, h]$ match the padded image space within $[0.0, 1.0]$. | Math is mostly correct, but forgot to add padding offset `dy`, causing box vertical shift. | Coordinate math is inverted or coordinates exceed 1.0 bound. | **35** |
| **3. Automated Batch Processing & Manifest Output** | Pipeline programmatically traverses directory tree, creates individual `.txt` label files, and writes absolute paths to `yolo_train.txt`. | Files processed, but requires hardcoded filenames or manifest contains relative paths that break in training. | Script crashes on missing files or fails to write label files. | **15** |
| **4. Defensive Image & Coordinate Validation** | Code defensively checks for `NoneType` loads from `cv2.imread()` and asserts bounding box coordinate bounds. | Code runs, but lacks validation checks for corrupt images. | Unhandled exceptions on empty files or corrupt headers. | **15** |
| **5. Code Quality & Standards** | Modular, well-documented functions, descriptive variable names, and clear docstrings. | Minor style issues (mixed variable casing, minimal comments). | Monolithic unformatted code block. | **10** |
| **Total** | | | | **100** |
