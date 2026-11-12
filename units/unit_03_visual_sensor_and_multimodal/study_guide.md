# Unit 3: Required Readings, Concepts & Video Lectures

Welcome to the instructional reading and study guide for **Unit 3: Visual Sensor Data & Image Preprocessing**. This page organizes the week's learning materials into four sections:

1. **Instructor Lecture & Conceptual Deep Dive:** Learn how digital images are stored as 3D NumPy arrays, what our target YOLO dataset manifest looks like, why stretching images breaks object detectors, how to resize images with letterbox padding, and how to convert bounding box coordinates step by step.
2. **Required Readings & Tutorial Guides:** Explore official documentation from OpenCV, Ultralytics YOLO, PyTorch Vision, and Albumentations.
3. **Required Micro-Video Lectures (Embedded):** Watch focused video tutorials covering image tensors, OpenCV in Python, and bounding box preprocessing.
4. **Institutional Video Lecture Embeds:** Access instructor announcements and lab walkthrough recordings.

*Work through each section in sequence as part of your 150-minute self-study block before starting the applied lab.*

---

## 1. Instructor Lecture & Conceptual Deep Dive

### Working with Camera Data and Image Tensors

In Units 1 and 2, all of our data lived in rows and columns inside Parquet tables. In **Unit 3**, we expand our pipelines to handle **visual sensor data**—photos and video frames captured by industrial cameras.

In modern logistics, manufacturing, and agriculture, cameras act as automated sensors. Computer vision models (such as YOLO object detectors) inspect camera feeds to spot structural cracks on commercial truck tires, read shipping container numbers at rail gates, or detect damaged boxes on warehouse conveyors.

However, a computer vision model cannot read a messy folder of raw JPEG files directly from different cameras. Raw camera photos arrive in different resolutions (such as 1920 &times; 1080 dashcam frames or 4032 &times; 3024 phone photos), different color channel orders, and different bounding-box label formats. As a data engineer, your job is to build the preprocessing pipeline that converts raw camera files into uniform, distortion-free image arrays and standardized label manifests.

#### Measurable Learning Objectives
* **Explain** how a digital color image is represented in memory as a 3D NumPy array `(Height, Width, Channels)` and convert between OpenCV's `BGR` order and standard `RGB` order.
* **Implement** aspect-ratio-preserving **letterbox padding** so images of any camera resolution fit a square model input (such as 640 &times; 640) without stretching or squishing objects.
* **Translate** bounding box coordinates between **Pascal VOC** (`[x_min, y_min, x_max, y_max]` in pixels), **COCO** (`[x_min, y_min, width, height]` in pixels), and **YOLO** (`[x_center, y_center, width, height]` normalized from `0.0` to `1.0`).
* **Recalculate** bounding box coordinates accurately after scaling and padding an image.
* **Build** a batch image preprocessing pipeline in Python using `numpy` and `cv2` (OpenCV).

---

### What Our Output Looks Like and Where the Data Comes From

#### The Purpose
Our goal in Unit 3 is to build a **Standardized Computer Vision Training Package**consisting of:
1. Uniform **640 &times; 640 RGB/BGR image tensors** resized with letterbox padding so zero geometric distortion occurs.
2. A **YOLO Annotation Manifest** (`manifest.parquet` / `.txt` label rows) where every defect bounding box is recalculated for the padded 640 &times; 640 canvas and normalized to `[0.0, 1.0]` floating-point coordinates.

#### Why Vision Models Need Fixed-Size Tensors and Normalized Labels
Unlike a SQL query that can scan tables of any width, a convolutional neural network (CNN) or Vision Transformer processes images in batches stored as a 4D mathematical block: `(Batch_Size, Height, Width, Channels)`.
* Every single image in a batch **must have the exact same pixel height and width** (for example, `640` pixels high by `640` pixels wide). If one image is `1920 x 1080` and the next is `1280 x 720`, Python cannot stack them into a batch tensor.
* Furthermore, object detection models like YOLO require every bounding box label to be expressed as percentages of the image width and height (`0.0` to `1.0`) rather than raw pixel numbers, so the neural network's output math stays stable across different resolutions.

#### Where the Raw Data Comes From (Source Systems)
In an automated fleet inspection lane, raw visual data comes from three sources:
1. **Inspection Lane Gate Cameras (`raw_images/*.jpg`):** High-speed cameras mounted at terminal gates that photograph truck tires, brakes, and trailers as vehicles roll through at 5 mph. Different terminals often have different camera models (`1920 x 1080`, `1280 x 720`, or vertical mobile inspection photos).
2. **Human Inspector Annotation Tool (`annotations.json` or CSV):** When human safety inspectors label historical tire defects using a tool like CVAT, LabelImg, or Roboflow, the tool saves pixel coordinates of each defect rectangle (`x_min, y_min, x_max, y_max`) measured on the original raw photo.
3. **Camera Hardware Metadata (EXIF / Gate Logs):** Timestamp, terminal ID, and lighting brightness values logged when the photo was captured.

#### Sample Output Dataset (The Target Shape)
For every processed image, our pipeline produces a 3D pixel array of shape `(640, 640, 3)` along with a manifest row containing the normalized YOLO coordinates:

| image_id | orig_shape (H &times; W) | target_shape | scale_ratio | pad_x | pad_y | class_id | x_center_norm | y_center_norm | width_norm | height_norm |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **tire_001.jpg** | 1080 &times; 1920 | 640 &times; 640 | 0.3333 | 0 | 140 | `0` (Crack) | **0.5000** | **0.5000** | **0.1000** | **0.1500** |
| **tire_002.jpg** | 720 &times; 1280 | 640 &times; 640 | 0.5000 | 0 | 140 | `1` (Bulge) | **0.3125** | **0.4688** | **0.0938** | **0.1250** |
| **tire_003.jpg** | 1000 &times; 800 | 640 &times; 640 | 0.6400 | 64 | 0 | `0` (Crack) | **0.4500** | **0.6000** | **0.0800** | **0.1600** |

---

### How Squashing Images Ruined a Tire Inspection Model

Why can't we just call `cv2.resize(img, (640, 640))` on every camera photo and call it a day? Let's look at a real computer vision engineering mistake.

A freight carrier installed cameras in its terminal inspection lanes to spot sidewall cracks on semi-truck tires before trucks entered the highway. The engineering team collected 5,000 widescreen photos (`1920` pixels wide by `1080` pixels tall) and wrote a four-line script to prepare them for a YOLO detector:

```python
# PROBLEMATIC SCRIPT: Forces a wide 1920x1080 photo into a 640x640 square!
import cv2

img = cv2.imread("tire_photo_1920x1080.jpg")
squashed_img = cv2.resize(img, (640, 640))
```

Look at what `cv2.resize(img, (640, 640))` does to a `1920 x 1080` widescreen photo:
* The width (`1920` &rarr; `640`) is squeezed by a factor of **3.0x**.
* The height (`1080` &rarr; `640`) is squeezed by a factor of only **1.68x**.

```
GEOMETRIC DISTORTION FROM NAIVE RESIZING:
Original Widescreen Photo (1920 x 1080):
- A round tire looks like a true circle.
- A narrow vertical stress crack is tall and thin.

After Naive cv2.resize(img, (640, 640)):
- Because width was compressed 3x while height was compressed 1.68x,
  the round tire is squished horizontally into a tall oval!
- Diagonal and vertical cracks change their angles and proportions.
```

When a second terminal installed cameras with a different aspect ratio (`4:3` instead of `16:9`), the squishing ratio changed, and the model failed to recognize real sidewall cracks.

In computer vision, **shape and geometry are the signal**. If your pipeline stretches or squashes images unevenly, you distort the very shapes the model is trying to learn.

---

### Preserving Geometry with Letterbox Padding

To resize any image into a `640 x 640` square without stretching it, we use **letterboxing**—the exact same technique used to display a widescreen movie on a square television screen by adding bars at the top and bottom.

Here is the three-step process:

1. **Find the Single Uniform Scale Ratio (`r`):**
   Divide the target width by the original width, and the target height by the original height, and pick the **smaller** of the two numbers so the whole image fits inside the canvas:
   <p style="text-align: center; font-weight: 600; background: #f8fafc; padding: 0.6rem; border-radius: 4px;">
     <i>r</i> = min( <i>W</i><sub>target</sub> / <i>W</i><sub>orig</sub> , &nbsp; <i>H</i><sub>target</sub> / <i>H</i><sub>orig</sub> )
   </p>
   For example, with a `1920` (W) &times; `1080` (H) photo and a `640` &times; `640` target:
   `r = min(640 / 1920, 640 / 1080) = min(0.3333, 0.5926) = 0.3333`.
2. **Resize Both Width and Height by That Exact Same Ratio (`r`):**
   * `new_w = round(1920 * 0.3333) = 640`
   * `new_h = round(1080 * 0.3333) = 360`
   Because both width and height were multiplied by `0.3333`, every circle stays a true circle!
3. **Center the Resized Image on a Neutral Gray `(114, 114, 114)` Canvas:**
   We create a blank `640 x 640` image filled with neutral gray (`114` for Blue, Green, and Red) and paste our `640 x 360` resized image into the center. The leftover `280` vertical pixels are split evenly: `pad_y = 140` pixels on top and `140` pixels on the bottom (`pad_x = 0` on left and right).

```
LETTERBOX PADDING (1920 x 1080  -->  640 x 640):
┌──────────────────────────────────────┐
│      Neutral Gray Padding (140px)    │  <-- pad_y = 140
├──────────────────────────────────────┤
│                                      │
│     Uniformly Scaled Image           │  <-- 640px wide x 360px tall
│     (100% True Proportions!)         │
│                                      │
├──────────────────────────────────────┤
│      Neutral Gray Padding (140px)    │
└──────────────────────────────────────┘
Total Canvas Size: 640 x 640
```

---

### Understanding Bounding Box Formats: VOC, COCO, and YOLO

When an inspector draws a rectangle around a tire crack, how do we store that rectangle's location as numbers? Computer vision tools use three standard coordinate systems:

| Format Name | 4 Numbers Stored | Meaning of the 4 Numbers | Units |
| :--- | :--- | :--- | :--- |
| **Pascal VOC** | `[x_min, y_min, x_max, y_max]` | Top-left corner `(x_min, y_min)` and bottom-right corner `(x_max, y_max)` | Raw Pixels (e.g., `100` to `1920`) |
| **COCO** | `[x_min, y_min, box_w, box_h]` | Top-left corner `(x_min, y_min)` plus box width and height | Raw Pixels |
| **YOLO** | `[x_center, y_center, box_w, box_h]` | Center of the box `(x_center, y_center)` plus width and height, **divided by image width and height** | Normalized Decimals (`0.0` to `1.0`) |

#### How to Update a Bounding Box After Letterboxing and Convert to YOLO
Suppose an original `1920 x 1080` photo has a Pascal VOC box `[x_min, y_min, x_max, y_max]`. When we letterbox the photo by scale ratio `r` and add padding `(pad_x, pad_y)` onto a `640 x 640` canvas, the box moves and shrinks along with the photo!

Here is the step-by-step arithmetic:
1. **Shift the pixel corners onto the padded 640 &times; 640 canvas:**
   * `new_x_min = (x_min * r) + pad_x`
   * `new_x_max = (x_max * r) + pad_x`
   * `new_y_min = (y_min * r) + pad_y`
   * `new_y_max = (y_max * r) + pad_y`
2. **Calculate the box center, width, and height in pixels on the 640 &times; 640 canvas:**
   * `box_w_px = new_x_max - new_x_min`
   * `box_h_px = new_y_max - new_y_min`
   * `center_x_px = new_x_min + (box_w_px / 2.0)`
   * `center_y_px = new_y_min + (box_h_px / 2.0)`
3. **Normalize by dividing by the target canvas dimensions (`640.0`):**
   * `x_center_norm = center_x_px / 640.0`
   * `y_center_norm = center_y_px / 640.0`
   * `width_norm = box_w_px / 640.0`
   * `height_norm = box_h_px / 640.0`

Every normalized YOLO coordinate is guaranteed to be between `0.0` and `1.0`!

---

### Step-by-Step Code Ramp-Up: NumPy Arrays and OpenCV from the Ground Up

If you have never used OpenCV (`cv2`) or manipulated 3D arrays in NumPy before, let's build every piece from scratch.

#### Step 1: What Is an Image in Python? (A 3D NumPy Array)
To a computer, a digital color image is simply a 3D grid of whole numbers from `0` (pitch black) to `255` (brightest intensity) stored with data type `np.uint8` (unsigned 8-bit integer).

```python
import numpy as np

# Create a blank 3D array: 100 pixels tall, 200 pixels wide, 3 color channels
img = np.zeros((100, 200, 3), dtype=np.uint8)

# Look at the shape: (Height, Width, Channels)
height, width, channels = img.shape
print(f"Height: {height}, Width: {width}, Channels: {channels}")
```

> **Watch Out for Order (`Height, Width` vs. `Width, Height`):**
> * In **NumPy** (`img.shape`), the order is always **`(Height, Width, Channels)`** (rows first, columns second—just like a spreadsheet!).
> * In **OpenCV functions** like `cv2.resize(img, (new_width, new_height))`, OpenCV asks for **`(Width, Height)`** (x first, y second). Always double-check which order you are passing!

#### Step 2: BGR vs. RGB Color Channels in OpenCV
When OpenCV loads a color image, it stores the 3 color channels in **Blue, Green, Red (`BGR`)** order rather than Red, Green, Blue (`RGB`). If you want to convert `BGR` to `RGB` (or to a 1-channel Grayscale image), use `cv2.cvtColor`:

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

#### Step 3: Pasting One Array Inside Another (Array Slicing)
How do we center a resized image inside a `640 x 640` gray canvas? Using NumPy slice indexing `canvas[y_start:y_end, x_start:x_end] = resized`:

```python
import cv2
import numpy as np

def letterbox_image(image: np.ndarray, target_size=(640, 640), fill_color=(114, 114, 114)):
    """
    Resizes an image with uniform scaling and centers it on a neutral gray canvas.
    Returns (padded_canvas, scale_ratio, pad_x, pad_y).
    """
    # 1. Read original Height and Width from the NumPy shape
    h_orig, w_orig = image.shape[:2]
    w_target, h_target = target_size

    # 2. Calculate uniform scale factor r so the longest side fits inside 640
    ratio = min(w_target / w_orig, h_target / h_orig)
    new_w = int(round(w_orig * ratio))
    new_h = int(round(h_orig * ratio))

    # 3. Resize image (remember cv2.resize takes (new_w, new_h)!)
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)

    # 4. Create the 640x640 neutral gray canvas (NumPy shape is (h_target, w_target, 3))
    canvas = np.full((h_target, w_target, 3), fill_color, dtype=np.uint8)

    # 5. Compute top-left padding offsets and paste the resized image into the center
    pad_x = (w_target - new_w) // 2
    pad_y = (h_target - new_h) // 2
    canvas[pad_y : pad_y + new_h, pad_x : pad_x + new_w] = resized

    return canvas, ratio, pad_x, pad_y

# Test with a synthetic 1280x720 (Height=720, Width=1280) image
raw_img = np.zeros((720, 1280, 3), dtype=np.uint8)
padded, r, px, py = letterbox_image(raw_img, target_size=(640, 640))
print(f"Original: {raw_img.shape} -> Letterboxed: {padded.shape} (ratio={r}, pad_x={px}, pad_y={py})")
```

#### Step 4: Converting a Pascal VOC Box into Normalized YOLO Format
Now let's write a clean helper function that takes an original `[x_min, y_min, x_max, y_max]` box, applies `ratio`, `pad_x`, and `pad_y`, and returns the normalized `[x_center, y_center, width, height]` YOLO tuple:

```python
def voc_to_yolo_letterboxed(x_min, y_min, x_max, y_max, ratio, pad_x, pad_y, canvas_w=640, canvas_h=640):
    """Converts raw Pascal VOC pixel coordinates into letterboxed, normalized YOLO coordinates."""
    # 1. Scale and shift corners by the letterbox parameters
    nx_min = (x_min * ratio) + pad_x
    nx_max = (x_max * ratio) + pad_x
    ny_min = (y_min * ratio) + pad_y
    ny_max = (y_max * ratio) + pad_y

    # 2. Compute pixel center, width, and height on the padded canvas
    bw = nx_max - nx_min
    bh = ny_max - ny_min
    cx = nx_min + (bw / 2.0)
    cy = ny_min + (bh / 2.0)

    # 3. Normalize to [0.0, 1.0]
    return (
        round(cx / canvas_w, 6),
        round(cy / canvas_h, 6),
        round(bw / canvas_w, 6),
        round(bh / canvas_h, 6),
    )

print("Normalized YOLO box:", voc_to_yolo_letterboxed(320, 180, 960, 540, ratio=0.5, pad_x=0, pad_y=140))
```

---

### Practice Exercises and Common Questions

Try these three exercises in your GitHub Codespaces sandbox (`units/unit_03_visual_sensor_and_multimodal_layer/`) before starting the graded lab:

1. **Exercise 1 (Tall vs. Wide Images):** Call `letterbox_image` on a tall portrait image of shape `(1600, 800, 3)` (Height=1600, Width=800). Check whether the gray padding appears on the top/bottom (`pad_y > 0`) or on the left/right (`pad_x > 0`).
2. **Exercise 2 (Center Point Check):** If a defect is located dead-center in a `1920 x 1080` image (`x_min=860, y_min=440, x_max=1060, y_max=640`), run `voc_to_yolo_letterboxed` and verify that `x_center` and `y_center` are both exactly `0.5` after letterboxing!
3. **Exercise 3 (Filtering Corrupted Images):** Write a one-line check that detects if an image array is completely black (`np.mean(img) < 5.0`)—a common failure when a gate camera's flash fails at night.

#### Common Questions & Troubleshooting

* **Question 1: Why do we pad with neutral gray `(114, 114, 114)` instead of black `(0, 0, 0)` or white `(255, 255, 255)`?**  
  *Answer:* Before neural networks process an image, they subtract the average pixel brightness (around `114` out of `255`). Filling the border bars with `(114, 114, 114)` means those padded borders become `0.0` after normalization, so they don't trigger false edge activations in the neural network.

* **Question 2: What happens if I letterbox the image, but calculate YOLO coordinates by dividing by the original `1920 x 1080` dimensions without adding `pad_y`?**  
  *Answer:* The bounding box will be shifted off-target! Because the `360`-pixel-tall image now sits inside a `640`-pixel-tall square with `140` pixels of gray padding above it, any box that ignores `pad_y` will float above or below the actual tire crack.

* **Question 3: Why does `cv2` work in GitHub Codespaces even though there is no desktop monitor attached?**  
  *Answer:* Our sandbox installs `opencv-python-headless`, which includes all of OpenCV's math, array resizing, and file-saving tools without requiring a desktop windowing system.

---

## 2. Required Readings & Authoritative Tutorial Guides

Review the following five curated documentation guides and technical references before beginning your applied lab:

1. **[OpenCV Python Repository & Usage Guide](https://github.com/opencv/opencv-python)**
   *Review the official Python bindings for OpenCV, including headless server usage and array manipulation.*

2. **[Ultralytics YOLO: Dataset Format & Manifest Standards](https://docs.ultralytics.com/datasets/)**
   *Study the specifications for YOLO text label files, directory structures, and normalized float coordinate bounds.*

3. **[PyTorch Vision: Transforms & Image Preprocessing](https://pytorch.org/vision/stable/transforms.html)**
   *Learn how deep learning frameworks handle batch image normalization, tensor conversions, and spatial transforms.*

4. **[Roboflow Engineering: Why Image Resizing & Letterboxing Matter](https://blog.roboflow.com/you-might-be-resizing-your-images-incorrectly/)**
   *See visual examples explaining why aspect-ratio distortion lowers object detection accuracy.*

5. **[Albumentations: Computer Vision Preprocessing & Bounding Boxes](https://albumentations.ai/docs/)**
   *Explore how bounding box coordinates transform alongside image resizing and padding.*

---

## 3. Required Micro-Video Lectures (Embedded)

Watch each of the following video chapters to see computer vision data engineering and coordinate systems in action:

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
