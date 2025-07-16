#!/usr/bin/env python3
import argparse
import base64
from PIL import Image
import io
from util.omniparser import Omniparser

# MODIFY paths according to your setup/location of models
DEFAULT_CONFIG = {
    'som_model_path': 'weights/icon_detect/model.pt',
    'caption_model_name': 'florence',  # or 'blip2' if using a different one
    'caption_model_path': 'weights/icon_caption_florence',
    'BOX_TRESHOLD': 0.3
}

def image_to_base64(image_path):
    with open(image_path, "rb") as imgf:
        encoded = base64.b64encode(imgf.read()).decode('ascii')
    return encoded

def main(image_path, config=DEFAULT_CONFIG):
    img_base64 = image_to_base64(image_path)
    parser = Omniparser(config)
    _, parsed_content_list = parser.parse(img_base64)
    if isinstance(parsed_content_list, list):
        prompt = "\n".join(str(item) for item in parsed_content_list)
    else:
        prompt = str(parsed_content_list)
    print("Prompt for LLM:\n")
    print(prompt)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Screenshot-to-LLM Prompt using OmniParser vision-based UI understanding")
    parser.add_argument("image", help="Path to screenshot file (PNG/JPG)")
    args = parser.parse_args()
    main(args.image)