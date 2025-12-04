"""
Vision Engine for OmniParser Analysis

Optimized for Apple Silicon (M1/M2/M3/M4) with MPS acceleration.
Implements thread-safe Singleton pattern for efficient resource management.
"""

import os
import io
import gc
import base64
import json
import threading
import numpy as np
from PIL import Image
from typing import List, Dict, Any, Optional
from pathlib import Path

# Import dependencies - fail gracefully if models not available
try:
    import torch
    # Support both package and local execution (FastAPI vs standalone script)
    try:
        # When running as a package: `python -m app.main`
        from app.util.utils import (
            check_ocr_box,
            get_yolo_model,
            get_caption_model_processor,
            get_som_labeled_img,
            get_optimal_device,
            get_optimal_dtype,
        )
    except ImportError:
        # When running from within Backend/app directly (like test.py) or during development
        from util.utils import (
            check_ocr_box,
            get_yolo_model,
            get_caption_model_processor,
            get_som_labeled_img,
            get_optimal_device,
            get_optimal_dtype,
        )
    MODELS_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  WARNING: OmniParser dependencies not available: {e}")
    print("   Vision Engine will run in fallback mode (no real analysis).")
    MODELS_AVAILABLE = False
    torch = None
    check_ocr_box = None
    get_yolo_model = None
    get_caption_model_processor = None
    get_som_labeled_img = None
    get_optimal_device = lambda: "cpu"
    get_optimal_dtype = lambda x: None

# Configuration
BASE_DIR = Path(__file__).parent
WEIGHTS_DIR = BASE_DIR / "weights"

# Performance tuning constants for Apple Silicon
MAX_IMAGE_WIDTH = 1080  # Maximum width for inference (saves memory bandwidth)
MPS_BATCH_SIZE = 64     # Optimized batch size for M-series chips
CPU_BATCH_SIZE = 32     # Smaller batch size for CPU fallback


class VisionEngineMeta(type):
    """
    Thread-safe Singleton metaclass.
    Ensures only one instance of VisionEngine exists across all threads.
    """
    _instances: Dict[type, Any] = {}
    _lock: threading.Lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            with cls._lock:
                # Double-check locking pattern
                if cls not in cls._instances:
                    instance = super().__call__(*args, **kwargs)
                    cls._instances[cls] = instance
        return cls._instances[cls]


class VisionEngine(metaclass=VisionEngineMeta):
    """
    Analyzes screenshots to detect UI elements using OmniParser (YOLO + Florence-2).
    
    Optimized for Apple Silicon (M1/M2/M3/M4) with Metal Performance Shaders (MPS).
    Uses Unified Memory efficiently by:
    - Resizing images before inference
    - Explicit memory cleanup after processing
    - Device-appropriate batch sizes
    
    Thread-safe Singleton: Only one instance is created and shared.
    """
    
    def __init__(self):
        """Initialize the Vision Engine with optimal device detection and model loading."""
        print("=" * 60)
        print("👁️  Vision Engine Initializing...")
        print("=" * 60)
        
        # Detect optimal device for Apple Silicon
        self._detect_device()
        
        # Model references (loaded lazily or eagerly based on configuration)
        self.yolo_model = None
        self.caption_model_processor = None
        self._models_loaded = False
        self._initialization_error: Optional[str] = None
        
        # Load models
        try:
            self._load_models()
            self._models_loaded = True
            print("=" * 60)
            print("✅ Vision Engine Ready!")
            print("=" * 60)
        except Exception as e:
            self._initialization_error = str(e)
            print(f"❌ Vision Engine initialization failed: {e}")
            print("=" * 60)
    
    def _detect_device(self):
        """
        Detect the optimal compute device.
        Prioritizes MPS on Apple Silicon, then CUDA, then CPU.
        """
        if MODELS_AVAILABLE and torch:
            self.device = get_optimal_device()
            self.dtype = get_optimal_dtype(self.device)
        else:
            self.device = "cpu"
            self.dtype = None
        
        # Print device information
        print(f"   🖥️  Platform: macOS (Apple Silicon)")
        print(f"   ⚡ Device: {self.device.upper()}")
        
        if self.device == "mps":
            print("   🍎 Metal Performance Shaders (MPS) enabled")
            print(f"   📊 Data Type: {self.dtype}")
            print(f"   📦 Batch Size: {MPS_BATCH_SIZE} (optimized for Unified Memory)")
        elif self.device == "cuda":
            print("   🎮 NVIDIA CUDA enabled")
            if torch:
                print(f"   📊 GPU: {torch.cuda.get_device_name(0)}")
        else:
            print("   💻 CPU mode (no GPU acceleration)")
            print("   ⚠️  Consider checking MPS availability for better performance")
        
        print()
    
    def _load_models(self):
        """Load YOLO and Caption models with MPS optimization."""
        if not MODELS_AVAILABLE:
            raise RuntimeError(
                "OmniParser dependencies not available. "
                "Check torch / util.utils installation."
            )
        
        # Model paths
        yolo_model_path = WEIGHTS_DIR / 'icon_detect/model.pt'
        caption_model_path = WEIGHTS_DIR / 'icon_caption_florence'
        
        # Validate model files exist
        if not yolo_model_path.exists():
            raise FileNotFoundError(f"YOLO model not found at {yolo_model_path}")

        if not caption_model_path.exists():
            raise FileNotFoundError(f"Caption model not found at {caption_model_path}")

        try:
            # Load YOLO model with MPS optimization
            print("   📦 Loading YOLO model...")
            self.yolo_model = get_yolo_model(
                model_path=str(yolo_model_path), 
                device=self.device
            )
            print(f"      ✓ YOLO loaded on {self.device}")
            
            # Load Florence-2 Caption model with MPS optimization
            print("   📦 Loading Florence-2 Caption model...")
            self.caption_model_processor = get_caption_model_processor(
                model_name="florence2",
                model_name_or_path=str(caption_model_path),
                device=self.device
            )
            print(f"      ✓ Florence-2 loaded on {self.device}")
            
            # Force garbage collection after loading large models
            gc.collect()
            if self.device == "mps" and torch:
                # Clear MPS cache to free up unified memory
                torch.mps.empty_cache()
            
            print("   ✅ All models loaded successfully!")
            
        except Exception as e:
            raise RuntimeError(f"Failed to load VisionEngine models: {e}") from e

    @property
    def is_ready(self) -> bool:
        """Check if the Vision Engine is ready for inference."""
        return self._models_loaded and self.yolo_model is not None

    def _resize_image_for_inference(self, image: Image.Image) -> Image.Image:
        """
        Resize image to optimize memory bandwidth on Apple Silicon.
        
        Maintains aspect ratio while ensuring width doesn't exceed MAX_IMAGE_WIDTH.
        This significantly reduces memory usage on Unified Memory architecture.
        
        Args:
            image: PIL Image to resize
            
        Returns:
            Resized PIL Image (or original if already within limits)
        """
        width, height = image.size
        
        if width <= MAX_IMAGE_WIDTH:
            return image
        
        # Calculate new dimensions maintaining aspect ratio
        new_width = MAX_IMAGE_WIDTH
        new_height = int(height * (MAX_IMAGE_WIDTH / width))
        
        print(f"   📐 Resizing image: {width}x{height} → {new_width}x{new_height}")
        
        # Use LANCZOS for high-quality downscaling
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # Clean up original image reference
        del image
        gc.collect()
        
        return resized

    def convert_to_serializable(self, obj):
        """Convert numpy types to Python native types for JSON serialization."""
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, dict):
            return {
                key: self.convert_to_serializable(value)
                for key, value in obj.items()
            }
        elif isinstance(obj, list):
            return [self.convert_to_serializable(item) for item in obj]
        return obj

    def analyze_image(
        self, 
        image_path: str, 
        annotated_output_path: Optional[str] = None,
        resize_for_inference: bool = True
    ) -> Dict[str, Any]:
        """
        Analyze the image and return detected UI elements.
        
        Args:
            image_path: Path to the screenshot file
            annotated_output_path: Optional path to save the annotated image
            resize_for_inference: If True, resize large images to save memory (default: True)
            
        Returns:
            Dict with:
              - elements: list of detected elements (type, bbox, text, confidence)
              - parsed_content_list: raw OmniParser outputs (strings)
              - label_coordinates: normalized bounding boxes keyed by ID
        """
        print(f"🔍 [VISION] Analyzing image: {image_path}")

        # Strict mode: if models are not available, stop immediately
        if not MODELS_AVAILABLE:
            raise RuntimeError("VisionEngine models unavailable (MODELS_AVAILABLE is False).")

        if not self.is_ready:
            error_msg = self._initialization_error or "Models not loaded"
            raise RuntimeError(f"VisionEngine not ready: {error_msg}")

        try:
            image_input = Image.open(image_path)
            original_size = image_input.size
            print(f"   📷 Original size: {original_size[0]}x{original_size[1]}")
        except Exception as e:
            print(f"❌ Error opening image {image_path}: {e}")
            return {
                "elements": [],
                "parsed_content_list": [],
                "label_coordinates": {},
            }

        # Resize for memory optimization (important for Unified Memory on Apple Silicon)
        if resize_for_inference:
            image_input = self._resize_image_for_inference(image_input)

        # Inference parameters
        box_threshold = 0.05
        iou_threshold = 0.1
        use_paddleocr = False
        imgsz = 640

        # Config for drawing boxes (used by get_som_labeled_img)
        box_overlay_ratio = image_input.size[0] / 3200
        draw_bbox_config = {
            'text_scale': 0.8 * box_overlay_ratio,
            'text_thickness': max(int(2 * box_overlay_ratio), 1),
            'text_padding': max(int(3 * box_overlay_ratio), 1),
            'thickness': max(int(3 * box_overlay_ratio), 1),
        }

        # Set batch size based on device
        batch_size = MPS_BATCH_SIZE if self.device == "mps" else CPU_BATCH_SIZE

        try:
            # 1. OCR (EasyOCR)
            # Note: EasyOCR may fallback to CPU on MPS, which is fine since M4 CPU is fast
            print("   🔤 Running OCR...")
            ocr_bbox_rslt, _ = check_ocr_box(
                image_input, 
                display_img=False, 
                output_bb_format='xyxy', 
                goal_filtering=None, 
                easyocr_args={'paragraph': False, 'text_threshold': 0.9}, 
                use_paddleocr=use_paddleocr
            )
            text, ocr_bbox = ocr_bbox_rslt
            print(f"      ✓ Found {len(text)} text regions")

            # 2. OmniParser (YOLO + Captioning)
            print("   🎯 Running OmniParser (YOLO + Florence-2)...")
            dino_labled_img, label_coordinates, parsed_content_list = get_som_labeled_img(
                image_input, 
                self.yolo_model, 
                BOX_TRESHOLD=box_threshold, 
                output_coord_in_ratio=True, 
                ocr_bbox=ocr_bbox,
                draw_bbox_config=draw_bbox_config, 
                caption_model_processor=self.caption_model_processor, 
                ocr_text=text,
                iou_threshold=iou_threshold, 
                imgsz=imgsz,
                batch_size=batch_size  # Use device-optimized batch size
            )
            print(f"      ✓ Detected {len(parsed_content_list)} UI elements")
            
            # 3. Save Annotated Image
            if annotated_output_path and dino_labled_img:
                try:
                    annotated_image = Image.open(io.BytesIO(base64.b64decode(dino_labled_img)))
                    annotated_image.save(annotated_output_path)
                    print(f"   🖍️  Annotated image saved: {annotated_output_path}")
                    # Clean up
                    del annotated_image
                except Exception as e:
                    print(f"   ❌ Failed to save annotated image: {e}")

            # 4. Format Output
            parsed_content_str = '\n'.join([
                f'icon {i}: {v}' for i, v in enumerate(parsed_content_list)
            ])
            
            # 5. Memory Cleanup (important for Unified Memory)
            self._cleanup_inference_memory(image_input, dino_labled_img)
            
            print(f"🎉 [VISION] Analysis complete. Found {len(parsed_content_list)} elements.")
            
            return {
                "image_path": image_path,
                "annotated_image_path": annotated_output_path,
                "parsed_content": parsed_content_str,
                "parsed_content_list": self.convert_to_serializable(parsed_content_list),
                "label_coordinates": self.convert_to_serializable(label_coordinates),
            }

        except Exception as e:
            print(f"❌ Analysis failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Cleanup on error
            self._cleanup_inference_memory(image_input if 'image_input' in locals() else None, None)
            
            return {
                "image_path": image_path,
                "annotated_image_path": None,
                "parsed_content": "",
                "parsed_content_list": [],
                "label_coordinates": {},
            }

    def _cleanup_inference_memory(self, image: Optional[Image.Image], encoded_img: Optional[str]):
        """
        Clean up memory after inference.
        Important for Apple Silicon's Unified Memory to avoid memory pressure.
        """
        try:
            if image is not None:
                del image
            if encoded_img is not None:
                del encoded_img
            
            # Force garbage collection
            gc.collect()
            
            # Clear MPS cache if using Metal
            if self.device == "mps" and torch:
                torch.mps.empty_cache()
                
        except Exception as e:
            # Don't fail on cleanup errors
            print(f"   ⚠️  Memory cleanup warning: {e}")

    def annotate_image(
        self, 
        image_path: str, 
        output_path: str, 
        elements: List[Dict[str, Any]]
    ) -> str:
        """
        Legacy method. Annotation is now handled inside analyze_image if output path is provided.
        
        If called separately, this assumes the annotated image was already created by analyze_image.
        
        Args:
            image_path: Path to the original image (not used)
            output_path: Path where annotated image should exist
            elements: List of detected elements (not used)
            
        Returns:
            Path to annotated image if it exists, empty string otherwise
        """
        if os.path.exists(output_path):
            return output_path
            
        print(
            "⚠️  annotate_image called but output file doesn't exist. "
            "analyze_image should have created it."
        )
        return ""

    def get_status(self) -> Dict[str, Any]:
        """
        Get the current status of the Vision Engine.
        
        Returns:
            Dict with status information including device, model state, etc.
        """
        return {
            "ready": self.is_ready,
            "device": self.device,
            "dtype": str(self.dtype) if self.dtype else None,
            "models_loaded": self._models_loaded,
            "yolo_loaded": self.yolo_model is not None,
            "caption_loaded": self.caption_model_processor is not None,
            "error": self._initialization_error,
            "max_image_width": MAX_IMAGE_WIDTH,
            "batch_size": MPS_BATCH_SIZE if self.device == "mps" else CPU_BATCH_SIZE,
        }


# ============================================================================
# Module-level singleton accessor
# ============================================================================

# Thread-safe singleton instance (alternative to metaclass approach for compatibility)
_vision_engine_instance: Optional[VisionEngine] = None
_vision_engine_lock = threading.Lock()


def get_vision_engine() -> VisionEngine:
    """
    Get or create the singleton Vision Engine instance.
    
    Thread-safe accessor that ensures only one VisionEngine exists.
    The VisionEngine class itself is also a singleton via metaclass,
    but this function provides backward compatibility.
    
    Returns:
        VisionEngine: The singleton instance
        
    Example:
        >>> engine = get_vision_engine()
        >>> result = engine.analyze_image("/path/to/screenshot.png")
    """
    global _vision_engine_instance
    
    if _vision_engine_instance is None:
        with _vision_engine_lock:
            # Double-check locking pattern
            if _vision_engine_instance is None:
                _vision_engine_instance = VisionEngine()
    
    return _vision_engine_instance


def reset_vision_engine():
    """
    Reset the singleton instance (mainly for testing purposes).
    
    Warning: This will cause models to be reloaded on next access.
    """
    global _vision_engine_instance
    with _vision_engine_lock:
        if _vision_engine_instance is not None:
            # Cleanup
            _vision_engine_instance._cleanup_inference_memory(None, None)
            _vision_engine_instance = None
            
            # Force garbage collection
            gc.collect()
            if torch and torch.backends.mps.is_available():
                torch.mps.empty_cache()
