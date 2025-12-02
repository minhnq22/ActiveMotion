import os
import json
import io
import base64
import numpy as np
from PIL import Image
import torch
from util.utils import check_ocr_box, get_yolo_model, get_caption_model_processor, get_som_labeled_img

# Configuration
SCREENSHOTS_DIR = "screenshots"
OUTPUT_FILE = "output.json"
WEIGHTS_DIR = "weights"

def convert_to_serializable(obj):
    """Convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_serializable(item) for item in obj]
    return obj


def process_image(image_path, yolo_model, caption_model_processor, output_dir="annotated_screenshots"):
    print(f"Processing {image_path}...")
    try:
        image_input = Image.open(image_path)
    except Exception as e:
        print(f"Error opening image {image_path}: {e}")
        return None

    box_threshold = 0.05
    iou_threshold = 0.1
    use_paddleocr = False # Using EasyOCR as installed
    imgsz = 640

    box_overlay_ratio = image_input.size[0] / 3200
    draw_bbox_config = {
        'text_scale': 0.8 * box_overlay_ratio,
        'text_thickness': max(int(2 * box_overlay_ratio), 1),
        'text_padding': max(int(3 * box_overlay_ratio), 1),
        'thickness': max(int(3 * box_overlay_ratio), 1),
    }

    # OCR
    ocr_bbox_rslt, is_goal_filtered = check_ocr_box(
        image_input, 
        display_img=False, 
        output_bb_format='xyxy', 
        goal_filtering=None, 
        easyocr_args={'paragraph': False, 'text_threshold':0.9}, 
        use_paddleocr=use_paddleocr
    )
    text, ocr_bbox = ocr_bbox_rslt

    # OmniParser
    dino_labled_img, label_coordinates, parsed_content_list = get_som_labeled_img(
        image_input, 
        yolo_model, 
        BOX_TRESHOLD=box_threshold, 
        output_coord_in_ratio=True, 
        ocr_bbox=ocr_bbox,
        draw_bbox_config=draw_bbox_config, 
        caption_model_processor=caption_model_processor, 
        ocr_text=text,
        iou_threshold=iou_threshold, 
        imgsz=imgsz
    )
    
    # Save annotated image
    annotated_image = Image.open(io.BytesIO(base64.b64decode(dino_labled_img)))
    filename = os.path.basename(image_path)
    name, ext = os.path.splitext(filename)
    annotated_path = os.path.join(output_dir, f"{name}_annotated{ext}")
    
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    annotated_image.save(annotated_path)
    print(f"  Saved annotated image to: {annotated_path}")
    
    # Format output
    parsed_content_str = '\n'.join([f'icon {i}: ' + str(v) for i,v in enumerate(parsed_content_list)])
    
    return {
        "image_path": image_path,
        "annotated_image_path": annotated_path,
        "parsed_content": parsed_content_str,
        "parsed_content_list": convert_to_serializable(parsed_content_list),
        "label_coordinates": convert_to_serializable(label_coordinates)
    }

def main():
    # Load models
    print("Loading models...")
    yolo_model_path = os.path.join(WEIGHTS_DIR, 'icon_detect/model.pt')
    caption_model_path = os.path.join(WEIGHTS_DIR, 'icon_caption_florence')
    
    if not os.path.exists(yolo_model_path):
        print(f"Error: YOLO model not found at {yolo_model_path}")
        return
    if not os.path.exists(caption_model_path):
        print(f"Error: Caption model not found at {caption_model_path}")
        return

    yolo_model = get_yolo_model(model_path=yolo_model_path)
    caption_model_processor = get_caption_model_processor(model_name="florence2", model_name_or_path=caption_model_path)

    results = []
    
    if not os.path.exists(SCREENSHOTS_DIR):
        print(f"Error: Screenshots directory '{SCREENSHOTS_DIR}' not found.")
        return

    for filename in os.listdir(SCREENSHOTS_DIR):
        if filename.lower().endswith(('.png', '.jpg', '.jpeg')):
            image_path = os.path.join(SCREENSHOTS_DIR, filename)
            result = process_image(image_path, yolo_model, caption_model_processor)
            if result:
                results.append(result)

    with open(OUTPUT_FILE, 'w') as f:
        json.dump(results, f, indent=4)
    
    print(f"Processing complete. Results saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
