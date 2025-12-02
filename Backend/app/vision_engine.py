"""
Vision Engine Module
Simulates an AI vision model (like OmniParser) to analyze screenshots and detect UI elements.
"""

import os
from typing import List, Dict, Any
from pathlib import Path

try:
    import pytesseract
    from PIL import Image
    HAS_OCR = True
except ImportError:
    HAS_OCR = False
    print("⚠️  pytesseract or PIL not found. OCR disabled.")

class VisionEngine:
    """
    Analyzes screenshots to detect UI elements.
    Currently uses mock data to simulate OmniParser.
    """
    
    def __init__(self):
        print("👁️  Vision Engine Initialized")
    
    def analyze_image(self, image_path: str) -> List[Dict[str, Any]]:
        """
        Analyze the image and return detected UI elements.
        
        Args:
            image_path: Path to the screenshot file
            
        Returns:
            List of detected elements with type, bbox, text, and confidence.
        """
        print(f"🔍 [VISION] Analyzing image: {image_path}")
        
        elements = []
        
        # 1. Try OCR if available (Optional enhancement)
        if HAS_OCR and os.path.exists(image_path):
            try:
                text = pytesseract.image_to_string(Image.open(image_path))
                print(f"📝 [VISION] OCR extracted {len(text)} chars")
            except Exception as e:
                print(f"⚠️  [VISION] OCR failed: {e}")

        # 2. Mock Logic (Simulating OmniParser)
        # In a real implementation, we would load a YOLO/Vision model here.
        # For now, we return hardcoded sample elements to test the pipeline.
        
        # Mock Element 1: Login Button
        login_btn = {
            "type": "button",
            "bbox": [100, 200, 300, 250], # [x1, y1, x2, y2]
            "text": "Login",
            "confidence": 0.95
        }
        elements.append(login_btn)
        print(f"✅ [VISION] Found 'Login' button at {login_btn['bbox']}")
        
        # Mock Element 2: Username Field
        username_field = {
            "type": "text",
            "bbox": [100, 150, 300, 190],
            "text": "Username",
            "confidence": 0.88
        }
        elements.append(username_field)
        print(f"✅ [VISION] Found 'Username' text field at {username_field['bbox']}")
        
        # Mock Element 3: Icon
        icon = {
            "type": "icon",
            "bbox": [50, 50, 90, 90],
            "text": "Menu",
            "confidence": 0.92
        }
        elements.append(icon)
        print(f"✅ [VISION] Found 'Menu' icon at {icon['bbox']}")
        
        print(f"🎉 [VISION] Analysis complete. Found {len(elements)} elements.")
        return elements

# Singleton instance
_vision_engine = None

def get_vision_engine() -> VisionEngine:
    """Get or create the singleton Vision Engine instance."""
    global _vision_engine
    if _vision_engine is None:
        _vision_engine = VisionEngine()
    return _vision_engine
