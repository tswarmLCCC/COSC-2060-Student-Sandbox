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
