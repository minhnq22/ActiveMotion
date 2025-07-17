#!/usr/bin/env python3
import argparse
import base64
from pathlib import Path
from util.omniparser import Omniparser

DEFAULT_CONFIG = {
    'som_model_path': 'weights/icon_detect/model.pt',
    'caption_model_name': 'florence2',
    'caption_model_path': 'weights/icon_caption_florence',
    'BOX_TRESHOLD': 0.3
}

def image_to_base64(image_path: str) -> str:
    """Convert image file to base64 string."""
    with open(image_path, "rb") as imgf:
        return base64.b64encode(imgf.read()).decode('ascii')

def main(image_path: str, config: dict = DEFAULT_CONFIG) -> None:
    """Process image and print LLM prompt, save annotated image."""
    img_base64 = image_to_base64(image_path)
    omniparser = Omniparser(config)
    annotated_img_b64, parsed_content_list = omniparser.parse(img_base64)
    if isinstance(parsed_content_list, list):
        prompt = "\n".join(str(item) for item in parsed_content_list)
    else:
        prompt = str(parsed_content_list)
    print("Prompt for LLM:\n")
    print(prompt)

    # Ensure output directory exists
    output_dir = Path("imgs")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "output.png"

    # Decode and save the image
    img_data = base64.b64decode(annotated_img_b64)
    with open(output_path, "wb") as f:
        f.write(img_data)
    print(f"Annotated image saved to {output_path}")

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description="Screenshot-to-LLM Prompt using OmniParser vision-based UI understanding"
    )
    arg_parser.add_argument("image", help="Path to screenshot file (PNG/JPG)")
    args = arg_parser.parse_args()
    main(args.image)