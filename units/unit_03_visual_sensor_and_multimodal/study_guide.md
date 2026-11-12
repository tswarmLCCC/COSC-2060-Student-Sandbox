# Unit 3: Required Readings, Concepts & Video Lectures

Welcome to the core instructional lecture and study hub for **Unit 3: The Visual Sensor Layer & Computer Vision Targets**. This page organizes all weekly learning materials into four structured chapters:

1. **Instructor Lecture & Conceptual Deep Dive:** Master the target YOLO manifest and 3D tensor shapes, visual camera source systems, 3D NumPy array layouts (Height, Width, Channels), OpenCV BGR vs. RGB conventions, the "Stretched Photograph" mental model, aspect-ratio preserving letterboxing, and the Bounding Box Rosetta Stone (VOC, COCO, YOLO).
2. **Required Readings & Authoritative Tutorial Guides:** Study curated official documentation from OpenCV, Ultralytics YOLO, PyTorch Vision, and Albumentations.
3. **Required Micro-Video Lectures (Embedded):** Watch high-definition video chapters with verified timestamp navigation to observe image tensor manipulations and coordinate transforms in live Python environments.
4. **Institutional Video Lecture Embeds:** Access campus-specific video recordings and announcements uploaded by your instructor.

*Work through each section in sequence as part of your 150-minute asynchronous self-study allocation before starting the applied laboratory assignment.*

---

## 1. Instructor Lecture & Conceptual Deep Dive

### Preprocessing Unstructured Imagery: Letterboxing, Color Spaces & YOLO Manifests

#### 1. Unit Overview & Objectives
In Units 1 and 2, we mastered structured tabular data. We engineered leak-free feature matrices in DuckDB and processed 1,000,000 transactional rows in Polars.

In **Unit 3**, we step outside the neat boundaries of rows and columns and enter the chaotic world of **unstructured visual sensor data**.

In modern AI engineering, computer vision models (such as YOLO, Faster R-CNN, or Vision Transformers) inspect real-world physical assets: detecting structural cracks on commercial aircraft wings, spotting sidewall bulges on freight truck tires, or reading shipping container barcodes in rail yards.

However, an AI model cannot ingest a messy directory of raw camera photos directly. Images arrive from different cameras with erratic resolutions (4032 &times; 3024 phone photos, 1920 &times; 1080 dashcam frames, 640 &times; 480 security sensors), mixed orientations, stripped EXIF metadata, and arbitrary bounding box coordinate formats.

As a data engineer, your job is to build the **visual preprocessing pipeline**: resizing without aspect-ratio distortion, normalizing pixel tensors, extracting sensor metadata, and formatting standardized training manifests (such as YOLO format). We will start by examining the exact output tensors and manifests we are building and the camera systems that produce the raw data, then study a real-world computer vision failure, the geometry of letterboxing, coordinate conversions, and a step-by-step NumPy and OpenCV code ramp-up.

**Measurable Learning Objectives:**
* **Deconstruct** digital images into 3D NumPy arrays / tensors `(Height, Width, Channels)` and navigate OpenCV's default `BGR` vs. standard `RGB` color space conventions.
* **Implement** letterbox padding algorithms that resize arbitrary real-world photos to standard model dimensions (e.g., 640 &times; 640) while strictly preserving aspect ratio.
* **Convert** between major computer vision annotation schemas: Pascal VOC (absolute `[x_min, y_min, x_max, y_max]`), COCO (`[x_min, y_min, width, height]`), and YOLO normalized center coordinates (`[x_center, y_center, width, height]`).
* **Recalculate** bounding box coordinates accurately after uniform scaling and symmetric letterbox padding.
* **Extract and Validate** embedded camera metadata and filter out corrupted or pitch-black frames using Python.
* **Construct** an automated, batch-processing Python pipeline that ingests truck inspection images and outputs a verified YOLO training manifest.

---

#### 2. What Our Output Looks Like and Where the Data Comes From

##### The Purpose
Our goal in Unit 3 is to build a **Standardized Computer Vision Training Package** consisting of:
1. Uniform **640 &times; 640 RGB/BGR image tensors** resized with letterbox padding so zero geometric distortion occurs.
2. A **YOLO Annotation Manifest** (`manifest.parquet` and `.txt` label rows) where every defect bounding box is recalculated for the padded 640 &times; 640 canvas and normalized to `[0.0, 1.0]` floating-point coordinates.

##### Why Vision Models Need Fixed-Size Tensors and Normalized Labels
Unlike a SQL query that can scan tables of varying lengths, a convolutional neural network (CNN) or Vision Transformer processes images in batches stored as a 4D mathematical block: `(Batch_Size, Height, Width, Channels)`.
* Every single image in a batch **must have the exact same pixel height and width** (for example, `640` pixels high by `640` pixels wide). If one image is `1920 x 1080` and the next is `1280 x 720`, Python cannot stack them into a uniform 4D batch tensor.
* Furthermore, object detection models like YOLO require every bounding box label to be expressed as relative fractions of the canvas width and height (`0.0` to `1.0`) rather than raw pixel integers, keeping neural network loss calculations stable across resolutions.

##### Where the Raw Data Comes From (Source Systems)
In an automated fleet inspection lane, raw visual data originates from three operational sources:
1. **Inspection Lane Gate Cameras (`raw_tires/*.jpg`):** High-speed digital cameras mounted at distribution terminal gates that photograph truck tires, wheel seals, and brake assemblies as trucks roll through at 5 mph. Different terminals frequently use different camera hardware (`3840 x 2160` 4K cameras, `1920 x 1080` HD cameras, or `800 x 1000` handheld mobile tablets).
2. **Human Inspector Annotation Exports (`annotations.json` / Pascal VOC XML / CSV):** When safety specialists label historical tire defects in annotation tools (such as CVAT, LabelImg, or Roboflow), the tool exports bounding box pixel coordinates (`x_min, y_min, x_max, y_max`) measured on the original unscaled image.
3. **Camera Sensor Metadata (EXIF & Gate Logs):** Frame dimensions, capture timestamps, terminal IDs, and average pixel brightness values used to detect dead camera flashes or corrupted zero-byte uploads.

##### Sample Output Dataset (The Target Shape)
For every valid inspection photo, our pipeline produces a distortion-free 3D pixel array of shape `(640, 640, 3)` along with a manifest row containing the recalculated, normalized YOLO coordinates:

| image_id | orig_shape (H &times; W) | target_shape | scale_ratio | pad_x | pad_y | class_id | x_center_norm | y_center_norm | width_norm | height_norm |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **tire_001.jpg** | 1080 &times; 1920 | 640 &times; 640 | 0.3333 | 0 | 140 | `0` (Crack) | **0.5000** | **0.5000** | **0.1000** | **0.1500** |
| **tire_002.jpg** | 720 &times; 1280 | 640 &times; 640 | 0.5000 | 0 | 140 | `1` (Bulge) | **0.3125** | **0.4688** | **0.0938** | **0.1250** |
| **tire_003.jpg** | 1000 &times; 800 | 640 &times; 640 | 0.6400 | 64 | 0 | `0` (Crack) | **0.4500** | **0.6000** | **0.0800** | **0.1600** |

---

#### 3. The \$1.2M Tire Blowout Catastrophe (Why Naive Resizing Fails)

Consider an authentic operational failure in freight transportation.

A national trucking carrier sought to automate routine pre-trip vehicle safety inspections. In commercial trucking, federal regulations mandate that drivers inspect truck tires for tread separation, sidewall bulges, and structural cracks before departing. A single steer tire blowout on an interstate highway can result in a fatal rollover, cargo loss, and severe corporate liability.

The company installed high-resolution digital cameras in the inspection lanes at distribution terminals. Every day, 2,000 trucks rolled through the lane, generating 36,000 high-resolution photos of tires and wheel assemblies.

The engineering team hired an outside AI consultant to train an object detection model to flag tire sidewall cracks. The consultant requested 5,000 training images. The junior data engineer wrote a quick Python script:

```python
# NAIVE, DISASTROUS IMAGE RESIZING (DO NOT USE IN PRODUCTION)
import cv2
import glob

for img_path in glob.glob("raw_tires/*.jpg"):
    img = cv2.imread(img_path)
    # Naively squash everything to 640x640:
    resized = cv2.resize(img, (640, 640)) 
    cv2.imwrite(img_path.replace("raw_", "train_"), resized)
```

The consultant trained a YOLOv8 object detector. In validation testing, the model achieved an impressive **94% mAP (mean Average Precision)**. The automated inspection gate went live at the terminal.

##### The Catastrophic Failure
Three weeks later, Truck #804 cleared the automated inspection gate with zero warnings. Forty miles down Interstate 80, the right front steer tire suffered a catastrophic sidewall blowout at 70 mph. The truck jackknifed, destroying \$1.2 million in pharmaceutical cargo and shutting down the interstate for six hours.

When safety investigators examined the high-resolution photo taken at the terminal gate 50 minutes prior to the crash, a **3-inch vertical stress fracture** was clearly visible on the tire sidewall.

Why did the 94% accurate AI model miss it?

```
THE DISTORTION DISASTER:
Original Image (Wide Aspect 16:9 - 3840 x 2160):
[ ─────────────────── (Vertical Crack: Narrow & Tall) ─────────────────── ]

Naive cv2.resize(img, (640, 640)) [FORCED SQUASH]:
Horizontally compressed by 600%! 
Vertically compressed by 337%!
Result: The vertical crack was squished into a wide, shallow diagonal smear!
```

Because the naive data pipeline forced a wide 16:9 rectangular photo into a square 640 &times; 640 matrix without preserving the aspect ratio, the geometric properties of the cracks were severely distorted. The model had learned to look for squished, distorted cracks. When real-world images from a newly installed 4:3 camera arrived, the crack geometry looked completely different, and the model remained completely blind.

**The Lesson:** In computer vision data engineering, **geometry is data**. If your preprocessing pipeline distorts aspect ratios or mishandles coordinate scaling, you corrupt the ground truth.

---

#### 4. "The Stretched Photograph" & Letterbox Padding

To prevent geometric distortion, modern computer vision pipelines use **Letterboxing** (the same technique film directors use to show widescreen movies on a standard TV).

Instead of squashing an image to fit a square 640 &times; 640 target:
1. **Compute Uniform Scale Factor (`r`):** Find the scale ratio that fits the longest dimension into 640 while maintaining the original width-to-height ratio:
   <p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.6rem; border-radius: 4px;">
     <i>r</i> = min( <i>W</i><sub>target</sub> / <i>W</i><sub>orig</sub> , &nbsp; <i>H</i><sub>target</sub> / <i>H</i><sub>orig</sub> )
   </p>
2. **Resize Uniformly:** Scale both width and height by that exact same ratio <i>r</i> (`new_w = round(W_orig * r)`, `new_h = round(H_orig * r)`).
3. **Pad Remaining Pixels with Neutral Gray `(114, 114, 114)`:** Center the scaled image inside the 640 &times; 640 canvas and pad the borders with neutral gray. (In neural networks, neutral gray `114` corresponds to near-zero activation after mean subtraction, avoiding artificial edge artifacts).

```
LETTERBOXING TRANSFORMATION:
Original (1920 x 1080) ──> Scale factor r = 640 / 1920 = 0.333
Scaled Image (640 x 360) ──> Preserve 100% of physical circle/crack geometry!
Add Gray Padding (140px top, 140px bottom):
┌──────────────────────────────────────┐
│       [Neutral Gray Padding]         │ (140px)
├──────────────────────────────────────┤
│                                      │
│        Scaled Tire Image             │ (360px)
│                                      │
├──────────────────────────────────────┤
│       [Neutral Gray Padding]         │ (140px)
└──────────────────────────────────────┘
Final Dimension: 640 x 640 (Zero Distortion!)
```

---

#### 5. The Coordinate System Rosetta Stone: VOC vs. COCO vs. YOLO

When preprocessing object detection datasets, you will encounter three competing bounding box coordinate schemas:

| Schema | Coordinate Format | Example Values (1920 &times; 1080 Image) | Characteristics |
| :--- | :--- | :--- | :--- |
| **Pascal VOC** | `[x_min, y_min, x_max, y_max]` | `[100, 200, 500, 600]` | Absolute pixel integers (Top-Left and Bottom-Right corners). |
| **COCO** | `[x_min, y_min, width, height]` | `[100, 200, 400, 400]` | Absolute pixel integers (Top-Left corner + box dimensions). |
| **YOLO** | `[x_center, y_center, width, height]` | `[0.156, 0.370, 0.208, 0.370]` | **Normalized floats** relative to image dimensions (`[0.0, 1.0]`). |

##### Converting Pascal VOC to YOLO (Direct & After Letterboxing)
On an unpadded canvas of width <i>W</i><sub>image</sub> and height <i>H</i><sub>image</sub>, converting Pascal VOC corners to normalized YOLO format uses:
<p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.6rem; border-radius: 4px;">
  <i>x</i><sub>center</sub> = (<i>x</i><sub>min</sub> + <i>x</i><sub>max</sub>) / (2 &times; <i>W</i><sub>image</sub>), &nbsp;&nbsp;
  <i>y</i><sub>center</sub> = (<i>y</i><sub>min</sub> + <i>y</i><sub>max</sub>) / (2 &times; <i>H</i><sub>image</sub>)
</p>
<p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.6rem; border-radius: 4px;">
  width = (<i>x</i><sub>max</sub> &minus; <i>x</i><sub>min</sub>) / <i>W</i><sub>image</sub>, &nbsp;&nbsp;
  height = (<i>y</i><sub>max</sub> &minus; <i>y</i><sub>min</sub>) / <i>H</i><sub>image</sub>
</p>

When you **letterbox** the image by scale factor <i>r</i> and add border padding `(pad_x, pad_y)` onto a 640 &times; 640 canvas, you must first scale and shift the pixel corners onto the padded canvas before dividing by `640.0`:
1. `new_x_min = (x_min * r) + pad_x` and `new_x_max = (x_max * r) + pad_x`
2. `new_y_min = (y_min * r) + pad_y` and `new_y_max = (y_max * r) + pad_y`
3. Compute `x_center`, `y_center`, `width`, and `height` from those shifted coordinates and divide by the target canvas size (`640.0`).

---

#### 6. Step-by-Step Code Ramp-Up & Guided Implementation Walkthrough (NumPy + OpenCV)

If you have never manipulated 3D arrays in NumPy or called OpenCV (`cv2`) before, let's build every piece from the ground up, and then run the complete letterboxing and coordinate transformation walkthrough.

##### Step 1: What Is an Image in Python? (A 3D NumPy Array)
To Python, a color image is simply a 3D grid of whole numbers from `0` (black) to `255` (full intensity) with data type `np.uint8` (unsigned 8-bit integer):

```python
import numpy as np

# Create a blank 3D array: 100 pixels tall (Height), 200 pixels wide (Width), 3 color channels
img = np.zeros((100, 200, 3), dtype=np.uint8)

# Unpack the shape: (Height, Width, Channels)
height, width, channels = img.shape
print(f"Height: {height}, Width: {width}, Channels: {channels}")
```

> **Crucial Dimension Order Tip (`Height, Width` vs. `Width, Height`):**
> * In **NumPy** (`img.shape` and `np.zeros((H, W, 3))`), the order is always **`(Height, Width, Channels)`** (rows first, columns second—just like a matrix or spreadsheet).
> * In **OpenCV functions** like `cv2.resize(img, (new_w, new_h))`, OpenCV expects **`(Width, Height)`** (horizontal *x* first, vertical *y* second). Always watch that order carefully!

##### Step 2: BGR vs. RGB Color Channels in OpenCV
By default, OpenCV loads color channels in **Blue, Green, Red (`BGR`)** order rather than Red, Green, Blue (`RGB`). You can swap between `BGR` and `RGB` (or convert to 1-channel Grayscale) using `cv2.cvtColor`:

```python
import cv2
import numpy as np

# Create a 50x50 image filled with pure Blue in BGR order: (Blue=255, Green=0, Red=0)
bgr_img = np.full((50, 50, 3), (255, 0, 0), dtype=np.uint8)

# Convert from BGR to RGB: now Channel 0 is Red (0) and Channel 2 is Blue (255)
rgb_img = cv2.cvtColor(bgr_img, cv2.COLOR_BGR2RGB)
print("BGR top-left pixel:", bgr_img[0, 0])  # [255   0   0]
print("RGB top-left pixel:", rgb_img[0, 0])  # [  0   0 255]
```

##### Step 3: Guided Implementation Walkthrough — OpenCV Letterboxing in Python
Here is how we combine uniform scaling, `cv2.resize`, and 2D array slice assignment (`canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized`) to letterbox any image without distortion:

```python
import cv2
import numpy as np

def letterbox_image(image, target_size=(640, 640), fill_color=(114, 114, 114)):
    """
    Resizes an image using uniform scaling and symmetric padding.
    Guarantees zero aspect-ratio distortion for computer vision models.
    """
    h_orig, w_orig = image.shape[:2]
    w_target, h_target = target_size
    
    # 1. Compute uniform scaling factor
    ratio = min(w_target / w_orig, h_target / h_orig)
    new_w = int(round(w_orig * ratio))
    new_h = int(round(h_orig * ratio))
    
    # 2. Resize with linear interpolation (note cv2.resize takes (new_w, new_h))
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    
    # 3. Create canvas filled with neutral gray (note NumPy takes (h_target, w_target, 3))
    canvas = np.full((h_target, w_target, 3), fill_color, dtype=np.uint8)
    
    # 4. Center the resized image on the canvas using slice assignment
    pad_x = (w_target - new_w) // 2
    pad_y = (h_target - new_h) // 2
    canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized
    
    return canvas, ratio, pad_x, pad_y

# Verification test with synthetic wide image (1280 x 720)
synthetic_image = np.zeros((720, 1280, 3), dtype=np.uint8)
cv2.circle(synthetic_image, (640, 360), 100, (0, 255, 0), -1)  # Perfect circle

processed, scale, px, py = letterbox_image(synthetic_image)
print(f"Original shape: {synthetic_image.shape}")
print(f"Processed shape: {processed.shape}")
print(f"Applied Scale: {scale:.4f}, Padding X: {px}, Padding Y: {py}")
```

##### Step 4: Recalculating Pascal VOC Bounding Boxes into Normalized YOLO Format
Finally, here is how we update a Pascal VOC bounding box `[x_min, y_min, x_max, y_max]` using the `scale`, `px`, and `py` values returned by `letterbox_image()`:

```python
def voc_to_yolo_letterboxed(x_min, y_min, x_max, y_max, ratio, pad_x, pad_y, canvas_w=640, canvas_h=640):
    """Converts raw Pascal VOC pixel coordinates into letterboxed, normalized YOLO coordinates."""
    # 1. Scale original pixel corners and shift by the letterbox border padding
    nx_min = (x_min * ratio) + pad_x
    nx_max = (x_max * ratio) + pad_x
    ny_min = (y_min * ratio) + pad_y
    ny_max = (y_max * ratio) + pad_y

    # 2. Compute box width, height, and center in pixels on the 640x640 canvas
    bw = nx_max - nx_min
    bh = ny_max - ny_min
    cx = nx_min + (bw / 2.0)
    cy = ny_min + (bh / 2.0)

    # 3. Normalize to [0.0, 1.0] relative to the 640x640 canvas
    return (
        round(cx / canvas_w, 6),
        round(cy / canvas_h, 6),
        round(bw / canvas_w, 6),
        round(bh / canvas_h, 6),
    )

yolo_box = voc_to_yolo_letterboxed(540, 260, 740, 460, ratio=scale, pad_x=px, pad_y=py)
print("Normalized YOLO (x_center, y_center, width, height):", yolo_box)
```

---

#### 7. Practice Exercises & Formative Self-Check FAQ

Try these three exercises in your GitHub Codespaces sandbox (`units/unit_03_visual_sensor_and_multimodal_layer/`) before starting the graded lab:

1. **Exercise 1 (Tall vs. Wide Images):** Call `letterbox_image` on a tall portrait image of shape `(1600, 800, 3)` (Height=1600, Width=800). Check whether the gray padding appears on the top/bottom (`pad_y > 0`) or on the left/right (`pad_x > 0`).
2. **Exercise 2 (Center Point Verification):** If a circle is drawn dead-center in a `1280 x 720` image (`x_min=540, y_min=260, x_max=740, y_max=460`), run `voc_to_yolo_letterboxed` and verify that `x_center` and `y_center` are both `0.5` after letterboxing!
3. **Exercise 3 (Filtering Corrupted Dark Frames):** Write a one-line check that detects if an image array is pitch black (`np.mean(img) < 5.0`)—a common failure when a gate camera's strobe flash fails at night.

##### Common Traps & Formative Self-Check FAQ

* **Question 1: Why does OpenCV read images in BGR instead of RGB?**  
  *Answer:* Historical reasons! When OpenCV was created in 1999, BGR was the standard representation used by camera frame grabbers and Windows display adapters. When transferring arrays to Matplotlib, PIL, or PyTorch, you must convert them: `cv2.cvtColor(img, cv2.COLOR_BGR2RGB)`.

* **Question 2: What happens if bounding boxes are not updated after letterbox padding?**  
  *Answer:* If you pad the image with 140 pixels of gray border but fail to adjust the box coordinates (`x_new = x_old * r + pad_x`, `y_new = y_old * r + pad_y`), the bounding box labels will point to empty gray padding or the wrong part of the tire, sabotaging the detector during training.

* **Question 3: Why do we pad with neutral gray `(114, 114, 114)` instead of black `(0, 0, 0)` or white `(255, 255, 255)`?**  
  *Answer:* Before neural networks process an image, they subtract the average dataset pixel intensity (roughly `114` out of `255`). Filling the padded borders with `(114, 114, 114)` means those borders become near `0.0` after normalization, preventing artificial high-contrast edges at the border boundary.

---

## 2. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical specifications before beginning your applied lab:

1. **[OpenCV Official Documentation: Geometric Image Transformations](https://github.com/opencv/opencv-python)**
   *Understand resizing interpolation algorithms (linear, cubic, area), color space conversions, and image affine transformations.*

2. **[Ultralytics YOLO: Dataset Format & Manifest Standards](https://docs.ultralytics.com/datasets/)**
   *Review the authoritative specifications for YOLO text label files, directory structures, and normalized float coordinate bounds.*

3. **[PyTorch Vision: Transforms & Data Augmentation](https://pytorch.org/vision/stable/transforms.html)**
   *Learn how modern deep learning frameworks handle batch image normalization, tensor conversions, and spatial augmentations.*

4. **[Roboflow Engineering: Image Letterboxing vs. Resizing](https://blog.roboflow.com/you-might-be-resizing-your-images-incorrectly/)**
   *A deep dive with visual benchmarks explaining why non-square aspect ratio distortion ruins object detection precision.*

5. **[Albumentations: Fast Computer Vision Preprocessing Library](https://albumentations.ai/docs/)**
   *Study high-performance bounding box transformations and automated spatial adjustments during image pipelines.*

---

## 3. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to observe computer vision data engineering and coordinate systems in action:

### PyTorch in 100 Seconds <span style="font-size: 0.9em; color: #64748b;">(Fireship - 2:15)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="PyTorch in 100 Seconds" src="https://www.youtube.com/embed/ORMx45xqWkA" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=ORMx45xqWkA" target="_blank" rel="noopener">Open video in new tab (2:15)</a></p>

### OpenCV Python: Image Processing & Tensor Manipulation <span style="font-size: 0.9em; color: #64748b;">(Rob Mulla - Core Walkthrough)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="Image Processing with OpenCV and Python" src="https://www.youtube.com/embed/kSqxn6zGE0c" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=kSqxn6zGE0c" target="_blank" rel="noopener">Open video in new tab</a></p>

### What is Image Preprocessing? Aspect Ratios & Bounding Boxes <span style="font-size: 0.9em; color: #64748b;">(Roboflow - Computer Vision Fundamentals)</span>
<div class="dp-embed-wrapper" style="position: relative; padding-bottom: 56.25%; height: 0; overflow: hidden; max-width: 100%; border-radius: 6px; margin-bottom: 0.5rem;">
  <iframe style="position: absolute; top: 0px; left: 0px; width: 100%; height: 100%; border: 0px none currentcolor;" title="What is Image Preprocessing" src="https://www.youtube.com/embed/VMeDbP8gX80" loading="lazy" allowfullscreen="allowfullscreen" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"></iframe>
</div>
<p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;"><a href="https://www.youtube.com/watch?v=VMeDbP8gX80" target="_blank" rel="noopener">Open video in new tab</a></p>

---

## 4. Institutional Video Lecture Embeds

<div style="background: #f8fafc; border-radius: 6px; padding: 1.5rem; margin: 1rem 0px; text-align: center; border: 2px dashed #94a3b8;">
  <p style="font-size: 0.95em; color: #475569; margin-bottom: 1rem;"><strong>Campus Faculty Announcements &amp; Lab Walkthrough Recordings</strong></p>
  <p style="font-size: 0.85em; color: #64748b; margin-top: 0.25rem;">Institutional video lectures and live office hour recordings for Unit 3 will appear in this designated container.</p>
</div>
