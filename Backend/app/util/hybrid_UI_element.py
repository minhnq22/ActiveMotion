import json
import re
import xml.etree.ElementTree as ET

def is_contained(outer, inner):
    """
    Check if inner rectangle is strictly contained within or equal to outer rectangle.
    Rect: [x1, y1, x2, y2]
    """
    return (outer[0] <= inner[0] and outer[1] <= inner[1] and 
            outer[2] >= inner[2] and outer[3] >= inner[3])

# ==========================================
# 1. HELPER FUNCTIONS
# ==========================================

def parse_bounds(bounds_str):
    """
    Convert ADB bounds string format '[x1,y1][x2,y2]' to list [x1, y1, x2, y2].
    """
    if not bounds_str:
        return None
    matches = re.findall(r'\d+', bounds_str)
    if len(matches) == 4:
        return list(map(int, matches))
    return None

def convert_omni_bbox(bbox, screen_w, screen_h):
    """
    Convert OmniParser normalized coordinates (0.0 - 1.0) to pixel values (int).
    bbox input: [x1, y1, x2, y2] (normalized)
    """
    return [
        int(bbox[0] * screen_w),
        int(bbox[1] * screen_h),
        int(bbox[2] * screen_w),
        int(bbox[3] * screen_h)
    ]

def calculate_iou(boxA, boxB):
    """
    Calculate Intersection over Union (IoU) score for position matching.
    Returns a value from 0.0 to 1.0.
    """
    # Calculate intersection rectangle coordinates
    xA = max(boxA[0], boxB[0])
    yA = max(boxA[1], boxB[1])
    xB = min(boxA[2], boxB[2])
    yB = min(boxA[3], boxB[3])

    interWidth = max(0, xB - xA)
    interHeight = max(0, yB - yA)
    interArea = interWidth * interHeight

    # Calculate area of each box
    boxAArea = (boxA[2] - boxA[0]) * (boxA[3] - boxA[1])
    boxBArea = (boxB[2] - boxB[0]) * (boxB[3] - boxB[1])

    # Avoid division by zero
    unionArea = float(boxAArea + boxBArea - interArea)
    if unionArea == 0:
        return 0

    return interArea / unionArea

# ==========================================
# 2. SCREEN STATE ANALYSIS
# ==========================================

def analyze_screen_state(xml_str):
    """
    Analyze the raw ADB XML to determine global screen properties.
    
    Args:
        xml_str (str): XML dump content from ADB.
        
    Returns:
        dict: Screen state information containing scrollability status and bounds.
    """
    screen_state = {
        "can_scroll_vertical": False,
        "scrollable_areas": []
    }
    
    try:
        root = ET.fromstring(xml_str)
    except ET.ParseError:
        return screen_state
    
    # Scan all nodes for scrollable elements
    for node in root.iter():
        is_scrollable = node.attrib.get('scrollable') == 'true'
        
        if is_scrollable:
            bounds = parse_bounds(node.attrib.get('bounds'))
            if bounds:
                screen_state["can_scroll_vertical"] = True
                screen_state["scrollable_areas"].append(bounds)
    
    return screen_state

# ==========================================
# 3. CORE LOGIC - VISION FIRST STRATEGY
# ==========================================

def extract_adb_nodes(xml_content):
    """
    Extract list of all visible nodes from XML.
    This creates a searchable pool for Vision-first matching.
    """
    try:
        root = ET.fromstring(xml_content)
    except ET.ParseError:
        return []

    nodes = []
    
    # Recursively iterate through all elements
    for node in root.iter():
        bounds = parse_bounds(node.attrib.get('bounds'))
        if not bounds:
            continue

        # Get important attributes
        text = node.attrib.get('text', "")
        desc = node.attrib.get('content-desc', "")
        resource_id = node.attrib.get('resource-id', "")
        cls = node.attrib.get('class', "")
        
        # Check interactivity
        is_clickable = node.attrib.get('clickable') == 'true'
        is_scrollable = node.attrib.get('scrollable') == 'true'
        is_editable = "EditText" in cls
        is_checked = node.attrib.get('checked') == 'true'
        is_selected = node.attrib.get('selected') == 'true'
        
        # Keep ALL nodes (even empty containers) for Vision matching
        # Filter will happen in the Vision-first loop
        nodes.append({
            "type": "adb",
            "text": text,
            "description": desc,
            "resource_id": resource_id,
            "class": cls,
            "bounds": bounds,
            "actions": {
                "clickable": is_clickable,
                "scrollable": is_scrollable,
                "editable": is_editable,
                "checked": is_checked,
                "enabled": node.attrib.get('enabled') == 'true',
                "selected": is_selected
            }
        })
    return nodes

def generate_merged_json(xml_str, omni_json_list, screen_w=1080, screen_h=2340):
    """
    **VISION-FIRST STRATEGY**
    Main function to merge ADB and OmniParser data.
    Mimics human behavior: See first (Vision), then understand context (ADB).
    
    Args:
        xml_str (str): XML dump content from ADB.
        omni_json_list (list): List of dictionaries from OmniParser (Vision data).
        screen_w, screen_h (int): Screen resolution (for normalization).
        
    Returns:
        str: JSON string with screen_state and elements array.
    """
    
    # Step 1: Global Screen State Analysis (NEW FEATURE)
    screen_state = analyze_screen_state(xml_str)
    
    # Step 2: Prepare ADB data pool for enrichment
    adb_nodes = extract_adb_nodes(xml_str)
    
    # Mark ADB nodes as unmatched
    for adb in adb_nodes:
        adb['matched'] = False
    
    final_elements = []
    uid_counter = 1

    # Step 3: VISION-FIRST LOOP - Iterate through Vision data as PRIMARY source
    for vision_element in omni_json_list:
        # Convert Vision bbox to pixels
        vision_bounds = convert_omni_bbox(vision_element['bbox'], screen_w, screen_h)
        
        # Initialize element with Vision data
        element = {
            "uid": uid_counter,
            "source": "vision_only",
            "type": vision_element['type'],  # "text" or "icon"
            "content": vision_element['content'],  # OCR or detected label
            "bounds": vision_bounds
        }
        
        # Step 4: Search for matching ADB node to ENRICH Vision data
        best_iou = 0.0
        best_adb_match = None
        
        for adb in adb_nodes:
            if adb['matched']:
                continue  # Skip already matched nodes
            
            iou = calculate_iou(vision_bounds, adb['bounds'])
            
            # IoU threshold: 0.3 is sufficient for spatial matching
            if iou > 0.3 and iou > best_iou:
                best_iou = iou
                best_adb_match = adb
        
        # Step 5: If ADB match found, ENRICH the Vision element
        if best_adb_match:
            best_adb_match['matched'] = True  # Mark as used
            element['source'] = "vision_enriched"
            
            # Get semantic content from ADB
            # Strategy: 1. Direct Text -> 2. Content Desc -> 3. Children Text -> 4. Keep OCR
            
            candidate_text = best_adb_match['text']
            candidate_desc = best_adb_match['description']
            
            # If direct node has no text/desc, try to harvest text from its children
            # (Common pattern: Clickable FrameLayout -> TextView child)
            if not candidate_text and not candidate_desc:
                child_texts = []
                for child in adb_nodes:
                    if child is best_adb_match: 
                        continue
                    # Check if 'child' is spatially inside 'best_adb_match'
                    if is_contained(best_adb_match['bounds'], child['bounds']):
                        txt = child['text'] or child['description']
                        if txt:
                            child_texts.append(txt)
                
                if child_texts:
                    # Join multiple children texts (e.g. "Song Title" + "Artist")
                    candidate_text = " ".join(child_texts)

            # Apply priority
            if candidate_text:
                element['content'] = candidate_text
            elif candidate_desc:
                element['content'] = candidate_desc
            # else: keep original OCR content
            
            # Add ADB-specific attributes (Including raw 'text' now)
            element['adb_attributes'] = {
                "text": best_adb_match['text'],  # Raw ADB text
                "resource_id": best_adb_match['resource_id'],
                "content_desc": best_adb_match['description'],
                "class": best_adb_match['class'],
                "clickable": best_adb_match['actions']['clickable'],
                "scrollable": best_adb_match['actions']['scrollable'],
                "editable": best_adb_match['actions']['editable'],
                "checked": best_adb_match['actions']['checked'],
                "selected": best_adb_match['actions']['selected']
            }
        
        final_elements.append(element)
        uid_counter += 1
    
    # Step 6: Build final output structure
    output = {
        "screen_state": screen_state,
        "elements": final_elements
    }
    
    return json.dumps(output, indent=2, ensure_ascii=False)

# ==========================================
# 3. USAGE EXAMPLE (DEMO)
# ==========================================

if __name__ == "__main__":
    # Simulate input - Vision-First Strategy Demo
    
    sample_xml = """
    <hierarchy rotation="0">
        <node index="0" text="" bounds="[0,0][1080,2340]" class="android.widget.FrameLayout" scrollable="false">
             <node index="0" text="No Surprises" resource-id="com.spotify:id/title" class="android.widget.TextView" clickable="true" bounds="[240,1992][484,2049]" />
             <node index="1" content-desc="Play video" class="android.widget.ImageView" clickable="true" bounds="[936,1977][1080,2121]" />
             <node index="2" text="" class="android.widget.ScrollView" scrollable="true" bounds="[0,200][1080,2000]" />
        </node>
    </hierarchy>
    """
    
    # Vision data comes FIRST (what the AI "sees")
    sample_omni = [
        {"type": "text", "bbox": [0.22, 0.85, 0.45, 0.87], "content": "No Surprses"},  # OCR typo - will be corrected by ADB
        {"type": "icon", "bbox": [0.88, 0.85, 0.98, 0.90], "content": "Play Triangle"},
        {"type": "icon", "bbox": [0.05, 0.10, 0.15, 0.15], "content": "Custom Game Sprite"}  # Vision-only (no ADB match)
    ]

    # Call function with Vision-First strategy
    result = generate_merged_json(sample_xml, sample_omni, 1080, 2340)
    
    print("=== VISION-FIRST STRATEGY OUTPUT ===")
    print(result)
    print("\n[Expected Output]")
    print("- screen_state.can_scroll_vertical: True")
    print("- elements[0].source: vision_enriched (OCR corrected by ADB)")
    print("- elements[2].source: vision_only (Game element, no ADB match)")