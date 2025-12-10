"""
LLM Engine for ActiveMotion - Debugging Version

Focused on debugging the decision-making process.
Sends merged screen data (content + coordinates) to Claude for spatial context.

Usage:
    cd Backend
    python -m app.llm_engine
"""

import os
import re
import json
from typing import Dict, List, Any, Optional

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

# OpenAI client (compatible with OpenRouter API)
from openai import OpenAI


# =============================================================================
# Configuration
# =============================================================================

OPENROUTE_API_KEY = os.getenv("OPENROUTE_API_KEY", "")
OPENROUTE_BASE_URL = os.getenv("OPENROUTE_BASE_URL", "https://openrouter.ai/api/v1")
LLM_MODEL = "anthropic/claude-3-5-sonnet"


# =============================================================================
# System Prompt
# =============================================================================

SYSTEM_PROMPT = """You are an Android automation brain. Receive screen data and user instruction. Output JSON only."""


# =============================================================================
# LLM Engine Class
# =============================================================================

class LLMEngine:
    """
    The Brain of ActiveMotion - Debugging Version.
    
    Merges parser_content_list and label_coordinates into rich screen data
    for spatial context awareness.
    """
    
    def __init__(self):
        """Initialize the LLM Engine with OpenRouter configuration."""
        print("=" * 60)
        print("🧠 LLM Engine Initializing (Debug Mode)")
        print("=" * 60)
        
        self.api_key = OPENROUTE_API_KEY
        self.base_url = OPENROUTE_BASE_URL
        self.model = LLM_MODEL
        
        if not self.api_key or self.api_key == "your_api_key_here":
            print("⚠️  WARNING: OPENROUTE_API_KEY not set!")
            print("   Set it in Backend/.env file")
        
        # Initialize OpenAI client with OpenRouter endpoint
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
        )
        
        print(f"   📡 Base URL: {self.base_url}")
        print(f"   🤖 Model: {self.model}")
        print("=" * 60)
    
    def _merge_screen_data(
        self, 
        parser_content_list: List[str], 
        label_coordinates: Dict[str, List[float]]
    ) -> List[Dict[str, Any]]:
        """
        Merge parser_content_list and label_coordinates into a single detailed list.
        
        The index of parser_content_list maps to the keys in label_coordinates.
        
        Args:
            parser_content_list: List of strings like:
                - "Text Box ID 0: Settings"
                - "Icon Box ID 1: gear icon"
            label_coordinates: Dict with string keys like:
                - {"0": [x, y, w, h], "1": [x, y, w, h]}
                
        Returns:
            Merged list with format:
            [
                {"id": 0, "type": "text", "content": "...", "bbox": [x, y, w, h]},
                {"id": 1, "type": "icon", "content": "...", "bbox": [x, y, w, h]}
            ]
        """
        merged_data = []
        
        for idx, content_str in enumerate(parser_content_list):
            # Parse the content string to extract type and content
            # Format: "Text Box ID X: content" or "Icon Box ID X: content"
            elem_type = "unknown"
            content = content_str
            
            if content_str.startswith("Text Box ID"):
                elem_type = "text"
                # Extract content after the colon
                parts = content_str.split(":", 1)
                if len(parts) > 1:
                    content = parts[1].strip()
            elif content_str.startswith("Icon Box ID"):
                elem_type = "icon"
                # Extract content after the colon
                parts = content_str.split(":", 1)
                if len(parts) > 1:
                    content = parts[1].strip()
            
            # Get bounding box from label_coordinates using string key
            bbox = label_coordinates.get(str(idx), [0, 0, 0, 0])
            
            # Convert numpy arrays to lists if needed
            if hasattr(bbox, 'tolist'):
                bbox = bbox.tolist()
            
            merged_data.append({
                "id": idx,
                "type": elem_type,
                "content": content,
                "bbox": bbox
            })
        
        return merged_data
    
    def analyze_screen(
        self, 
        user_instruction: str, 
        parser_content_list: List[str], 
        label_coordinates: Dict[str, List[float]]
    ) -> Dict[str, Any]:
        """
        Analyze the current screen state and determine the next action.
        
        This method:
        1. Merges parser_content_list and label_coordinates into rich JSON
        2. Builds the prompt with full spatial context
        3. PRINTS the prompt for debugging
        4. Calls the LLM
        5. PRINTS the raw response for debugging
        6. Returns the parsed JSON action
        
        Args:
            user_instruction: What the user wants to achieve (e.g., "Open Settings")
            parser_content_list: List of parsed content strings from VisionEngine
            label_coordinates: Dict of bounding boxes from VisionEngine
            
        Returns:
            Parsed action dict: {"action": "...", "element_id": ..., "reasoning": "..."}
        """
        print("\n" + "=" * 60)
        print("🧠 [LLM ENGINE] analyze_screen() called")
        print("=" * 60)
        
        # =====================================================================
        # Step 1: Merge screen data
        # =====================================================================
        merged_screen_data = self._merge_screen_data(parser_content_list, label_coordinates)
        formatted_screen_data = json.dumps(merged_screen_data, indent=2)
        
        print(f"\n📊 Merged Screen Data ({len(merged_screen_data)} elements):")
        print("-" * 40)
        print(formatted_screen_data)
        print("-" * 40)
        
        # =====================================================================
        # Step 2: Build the prompt
        # =====================================================================
        user_prompt = f"""User Instruction: {user_instruction}

Screen Data (JSON):
{formatted_screen_data}

Respond with valid JSON: {{"action": "...", "element_id": ..., "reasoning": "..."}}"""
        
        print("\n📝 PROMPT BEING SENT TO LLM:")
        print("=" * 60)
        print(f"[SYSTEM PROMPT]\n{SYSTEM_PROMPT}")
        print("-" * 60)
        print(f"[USER PROMPT]\n{user_prompt}")
        print("=" * 60)
        
        # =====================================================================
        # Step 3: Call the LLM
        # =====================================================================
        if not self.api_key or self.api_key == "your_api_key_here":
            print("\n❌ Cannot call API: OPENROUTE_API_KEY not configured!")
            return {
                "action": "error",
                "element_id": None,
                "reasoning": "API key not configured",
                "error": True
            }
        
        print("\n🚀 Calling OpenRouter API...")
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=1024,
                temperature=0.3,  # Lower temperature for more deterministic output
            )
            
            raw_response = response.choices[0].message.content
            
            # =====================================================================
            # Step 4: Print raw response for debugging
            # =====================================================================
            print("\n📥 RAW RESPONSE FROM OPENROUTER:")
            print("=" * 60)
            print(raw_response)
            print("=" * 60)
            
            # =====================================================================
            # Step 5: Parse the response
            # =====================================================================
            parsed_action = self._parse_response(raw_response)
            
            print("\n✅ PARSED ACTION:")
            print(json.dumps(parsed_action, indent=2))
            
            return parsed_action
            
        except Exception as e:
            print(f"\n❌ API call failed: {e}")
            return {
                "action": "error",
                "element_id": None,
                "reasoning": str(e),
                "error": True
            }
    
    def _parse_response(self, raw_response: str) -> Dict[str, Any]:
        """
        Parse the LLM response into a structured action dict.
        
        Handles:
        - Markdown code blocks (```json ... ```)
        - Extra whitespace
        - Malformed JSON
        """
        cleaned = raw_response.strip()
        
        # Remove markdown code blocks if present
        json_block_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
        match = re.search(json_block_pattern, cleaned)
        if match:
            cleaned = match.group(1).strip()
        
        # Find JSON object boundaries
        start_idx = cleaned.find('{')
        end_idx = cleaned.rfind('}')
        
        if start_idx == -1 or end_idx == -1:
            return {
                "action": "error",
                "element_id": None,
                "reasoning": f"No JSON found in response: {raw_response[:100]}",
                "error": True
            }
        
        json_str = cleaned[start_idx:end_idx + 1]
        
        try:
            parsed = json.loads(json_str)
            return parsed
        except json.JSONDecodeError as e:
            return {
                "action": "error",
                "element_id": None,
                "reasoning": f"JSON parse error: {e}",
                "error": True
            }
    
    def get_status(self) -> Dict[str, Any]:
        """Get the current status of the LLM Engine."""
        api_key_set = bool(self.api_key and self.api_key != "your_api_key_here")
        return {
            "ready": api_key_set,
            "model": self.model,
            "base_url": self.base_url,
            "api_key_configured": api_key_set,
        }


# =============================================================================
# Singleton Accessor
# =============================================================================

_llm_engine_instance: Optional[LLMEngine] = None


def get_llm_engine() -> LLMEngine:
    """Get or create the singleton LLM Engine instance."""
    global _llm_engine_instance
    if _llm_engine_instance is None:
        _llm_engine_instance = LLMEngine()
    return _llm_engine_instance


# =============================================================================
# Test Block - Paste Your Real Data Here!
# =============================================================================

if __name__ == "__main__":
    """
    Test the LLM Engine with real or dummy data.
    
    Usage:
        cd Backend
        python -m app.llm_engine
    
    Instructions:
        1. Replace the dummy data below with your real VisionEngine output
        2. Run the script to see what prompt is sent and what response comes back
    """
    print("\n" + "=" * 70)
    print("🧪 LLM ENGINE TEST - Debugging Mode")
    print("=" * 70)
    
    # Initialize engine
    engine = LLMEngine()
    print(f"\n📋 Engine Status: {engine.get_status()}")
    
    # =========================================================================
    # 📝 PASTE YOUR REAL DATA BELOW
    # =========================================================================
    
    # Example instruction
    test_instruction = "Open the Settings app"
    
    # Example parser_content_list (from VisionEngine.analyze_image())
    # Replace with your real data!
    test_parser_content_list = [
        "Text Box ID 0: Messages",
        "Text Box ID 1: Phone",
        "Text Box ID 2: Contacts",
        "Icon Box ID 3: Settings - A gear icon for system settings",
        "Text Box ID 4: Camera",
        "Text Box ID 5: Gallery",
        "Text Box ID 6: Play Store",
        "Icon Box ID 7: Chrome - Browser application",
        "Text Box ID 8: Calendar",
        "Text Box ID 9: Clock",
    ]
    
    # Example label_coordinates (from VisionEngine.analyze_image())
    # Format: {"index_as_string": [x, y, width, height]} (normalized 0-1)
    # Replace with your real data!
    test_label_coordinates = {
        "0": [0.10, 0.20, 0.20, 0.05],
        "1": [0.35, 0.20, 0.20, 0.05],
        "2": [0.60, 0.20, 0.20, 0.05],
        "3": [0.10, 0.30, 0.20, 0.05],
        "4": [0.35, 0.30, 0.20, 0.05],
        "5": [0.60, 0.30, 0.20, 0.05],
        "6": [0.10, 0.40, 0.20, 0.05],
        "7": [0.35, 0.40, 0.20, 0.05],
        "8": [0.60, 0.40, 0.20, 0.05],
        "9": [0.10, 0.50, 0.20, 0.05],
    }
    
    # =========================================================================
    # Run the analysis
    # =========================================================================
    
    print("\n🎯 Test Input:")
    print(f"   Instruction: {test_instruction}")
    print(f"   Elements: {len(test_parser_content_list)} items")
    print(f"   Coordinates: {len(test_label_coordinates)} entries")
    
    result = engine.analyze_screen(
        user_instruction=test_instruction,
        parser_content_list=test_parser_content_list,
        label_coordinates=test_label_coordinates
    )
    
    print("\n" + "=" * 70)
    print("🏁 FINAL RESULT:")
    print("=" * 70)
    print(json.dumps(result, indent=2))
    
    print("\n" + "=" * 70)
    print("🧪 TEST COMPLETE")
    print("=" * 70)
