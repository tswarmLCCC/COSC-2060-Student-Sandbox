"""
====================================================================
COSC 2060: Modern Data Engineering & AI Infrastructure
Unit 3 Synchronous Coding Clinic ("I Do, We Do, You Do")
Topic: The Visual Sensor Layer & YOLO Coordinate Math
====================================================================
Run this script from the terminal to execute the live class walkthrough
demonstrations:
    python units/unit_03_visual_sensor_and_multimodal/coding_clinic.py
====================================================================
"""


# ====================================================================
# PART 0: BASICS WARM-UP — 3D NUMPY IMAGE ARRAYS & COLOR CHANNELS
# ====================================================================
print("\n>>> Executing PART 0: BASICS WARM-UP (3D Image Arrays from Scratch)...")
import cv2
import numpy as np

# 1. Create a tiny 100x200 color image array (Height=100, Width=200, Channels=3)
warmup_img = np.zeros((100, 200, 3), dtype=np.uint8)
warmup_img[:] = (255, 0, 0)  # Pure Blue in OpenCV's BGR channel order
h_warm, w_warm, c_warm = warmup_img.shape
rgb_warm = cv2.cvtColor(warmup_img, cv2.COLOR_BGR2RGB)
print(f"Part 0 Warm-Up — Array shape (H, W, C): ({h_warm}, {w_warm}, {c_warm})")
print(f"Top-left pixel in BGR: {warmup_img[0, 0].tolist()} -> Converted to RGB: {rgb_warm[0, 0].tolist()}")


# ====================================================================
# PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION
# ====================================================================
print("\n>>> Executing PART 1: 'I DO' — INSTRUCTOR DEMONSTRATION...")

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


# ====================================================================
# PART 2: 'WE DO' — GUIDED CLASS PRACTICE
# ====================================================================
print("\n>>> Executing PART 2: 'WE DO' — GUIDED CLASS PRACTICE...")
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

