
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sqlite3
import os
import json
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone

# --- Cấu hình ---
app = FastAPI(title="Android Security Agent API")

# Cấu hình CORS (Quan trọng để Frontend React gọi được)
origins = [
    "http://localhost:3000", # React mặc định
    "http://localhost:5173", # Vite mặc định
    "http://localhost",      # Docker production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Đường dẫn đến thư mục data
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "Data") # Changed to match existing directory case
DB_PATH = os.path.join(DATA_DIR, "app_data.db")
SCREENSHOT_DIR = os.path.join(DATA_DIR, "screenshots")
ANNOTATED_SCREENSHOT_DIR = os.path.join(DATA_DIR, "annotated_screenshots")
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://localhost:8000")

# Tự động tạo folder nếu chưa có
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(ANNOTATED_SCREENSHOT_DIR, exist_ok=True)

# Mount thư mục ảnh tĩnh để Frontend load được ảnh: http://localhost:8000/screenshots/img1.png
app.mount("/screenshots", StaticFiles(directory=SCREENSHOT_DIR), name="screenshots")
app.mount(
    "/annotated-screenshots",
    StaticFiles(directory=ANNOTATED_SCREENSHOT_DIR),
    name="annotated_screenshots",
)

# --- Database Helper ---
def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Để trả về dạng dictionary thay vì tuple
    return conn


def build_static_url(filename: Optional[str], mount_path: str) -> Optional[str]:
    """Return absolute URL for static assets if filename is present."""
    if not filename:
        return None
    return f"{SERVER_BASE_URL}{mount_path}/{filename}"


def format_capture_metadata(timestamp_value: Optional[float]) -> Tuple[Optional[str], Optional[str]]:
    """Convert a numeric timestamp into ISO string + human readable age."""
    if timestamp_value is None:
        return None, None
    try:
        ts_float = float(timestamp_value)
    except (TypeError, ValueError):
        return None, None

    captured_at = datetime.fromtimestamp(ts_float, timezone.utc).isoformat()
    age_seconds = int((datetime.now(timezone.utc) - datetime.fromtimestamp(ts_float, timezone.utc)).total_seconds())

    if age_seconds <= 0:
        human_label = "just now"
    elif age_seconds < 60:
        human_label = f"{age_seconds}s ago"
    elif age_seconds < 3600:
        human_label = f"{age_seconds // 60}m ago"
    elif age_seconds < 86400:
        human_label = f"{age_seconds // 3600}h ago"
    else:
        human_label = f"{age_seconds // 86400}d ago"

    return captured_at, human_label


def load_traffic_maps(conn: sqlite3.Connection) -> Tuple[Dict[str, List[Dict]], Dict[str, List[Dict]]]:
    """
    Load traffic entries and organize them by node and edge for quick lookups.
    Traffic is associated with the source node of each edge (action origin).
    """
    rows = conn.execute(
        """
        SELECT ti.*, e.source_node_id, e.target_node_id
        FROM traffic_index ti
        LEFT JOIN edges e ON ti.edge_id = e.id
        """
    ).fetchall()

    traffic_by_node: Dict[str, List[Dict]] = {}
    traffic_by_edge: Dict[str, List[Dict]] = {}

    for row in rows:
        captured_at, human_age = format_capture_metadata(row["timestamp_start"])
        entry = {
            "id": row["id"],
            "edgeId": row["edge_id"],
            "burpRefId": row["burp_ref_id"],
            "method": row["method"],
            "url": row["url"],
            "status": int(row["status_code"]) if row["status_code"] is not None else None,
            "timestamp": float(row["timestamp_start"]) if row["timestamp_start"] is not None else None,
            "capturedAt": captured_at,
            "duration": human_age or "just now",
        }

        if row["edge_id"]:
            traffic_by_edge.setdefault(row["edge_id"], []).append(entry)

        source_node = row["source_node_id"]
        if source_node:
            traffic_by_node.setdefault(source_node, []).append(entry)

    # Sort each bucket by most recent first
    for bucket in traffic_by_node.values():
        bucket.sort(key=lambda item: item.get("capturedAt") or "", reverse=True)
    for bucket in traffic_by_edge.values():
        bucket.sort(key=lambda item: item.get("capturedAt") or "", reverse=True)

    return traffic_by_node, traffic_by_edge


def load_parser_outputs(conn: sqlite3.Connection) -> Dict[str, Dict]:
    """Load parser metadata for each node."""
    rows = conn.execute("SELECT * FROM parser_outputs").fetchall()
    parser_by_node: Dict[str, Dict] = {}
    for row in rows:
        parsed_list_raw = row["parsed_content_list"]
        label_coords_raw = row["label_coordinates"]
        parser_by_node[row["node_id"]] = {
            "parsedContentList": json.loads(parsed_list_raw) if parsed_list_raw else [],
            "labelCoordinates": json.loads(label_coords_raw) if label_coords_raw else {},
        }
    return parser_by_node

def ensure_column(cursor: sqlite3.Cursor, table: str, column: str, definition: str) -> None:
    """Add missing column without failing if it already exists."""
    cursor.execute(f"PRAGMA table_info({table})")
    existing_columns = {row["name"] for row in cursor.fetchall()}
    if column not in existing_columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {definition}")


def init_db():
    """Khởi tạo bảng nếu chưa có"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Bảng Nodes
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS nodes (
        id TEXT PRIMARY KEY,
        label TEXT,
        description TEXT,
        screenshot_path TEXT,
        annotated_screenshot_path TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')

    ensure_column(
        cursor,
        "nodes",
        "annotated_screenshot_path",
        "annotated_screenshot_path TEXT",
    )
    
    # Bảng Edges
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS edges (
        id TEXT PRIMARY KEY,
        source_node_id TEXT,
        target_node_id TEXT,
        label TEXT,
        animated BOOLEAN DEFAULT 1,
        FOREIGN KEY(source_node_id) REFERENCES nodes(id),
        FOREIGN KEY(target_node_id) REFERENCES nodes(id)
    )
    ''')
    
    # Bảng Traffic Index (Như đã thiết kế)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS traffic_index (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        edge_id TEXT,
        burp_ref_id TEXT, 
        method TEXT,
        url TEXT,
        status_code INTEGER,
        timestamp_start REAL,
        FOREIGN KEY(edge_id) REFERENCES edges(id)
    )
    ''')

    cursor.execute('''
    CREATE TABLE IF NOT EXISTS parser_outputs (
        node_id TEXT PRIMARY KEY,
        parsed_content_list TEXT,
        label_coordinates TEXT,
        FOREIGN KEY(node_id) REFERENCES nodes(id)
    )
    ''')
    
    conn.commit()
    conn.close()

# Chạy init db khi khởi động app
init_db()

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"status": "Agent is Ready", "burp_connected": False}

@app.get("/api/adb/status")
def get_adb_status():
    """
    Check ADB connection status
    """
    try:
        from .adb_controller import get_adb_controller
    except ImportError:
        from adb_controller import get_adb_controller
    
    try:
        adb = get_adb_controller()
        status_info = adb.get_status()
        
        return {
            "connected": status_info["status"] == "connected",
            "status": status_info["status"],
            "message": status_info["message"],
            "device": status_info["device"]
        }
    except Exception as e:
        return {
            "connected": False,
            "status": "error",
            "message": str(e),
            "device": None
        }


@app.get("/api/graph")
def get_graph_data():
    """
    API trả về dữ liệu cho React Flow
    """
    conn = get_db_connection()
    nodes = conn.execute("SELECT * FROM nodes").fetchall()
    edges = conn.execute("SELECT * FROM edges").fetchall()
    traffic_by_node, traffic_by_edge = load_traffic_maps(conn)
    parser_by_node = load_parser_outputs(conn)
    conn.close()
    
    # Format lại theo chuẩn React Flow
    formatted_nodes = []
    for node in nodes:
        formatted_nodes.append({
            "id": node["id"],
            "type": "screenshotNode", # Khớp với Frontend của bạn
            "position": {"x": 0, "y": 0}, # Todo: Logic auto-layout sau này
            "data": {
                "label": node["label"],
                "screenshot": build_static_url(node["screenshot_path"], "/screenshots"),
                "annotatedScreenshot": build_static_url(
                    node["annotated_screenshot_path"], "/annotated-screenshots"
                ),
                "description": node["description"],
                "traffic": traffic_by_node.get(node["id"], []),
                "parser": parser_by_node.get(node["id"]),
            }
        })

    formatted_edges = []
    for edge in edges:
        edge_dict = dict(edge)
        edge_dict["traffic"] = traffic_by_edge.get(edge["id"], [])
        edge_dict.setdefault("source", edge["source_node_id"])
        edge_dict.setdefault("target", edge["target_node_id"])
        formatted_edges.append(edge_dict)

    return {
        "nodes": formatted_nodes,
        "edges": formatted_edges
    }

@app.post("/api/analyze-screen")
def analyze_screen():
    """
    Capture screenshot and analyze it with Vision Engine.
    """
    try:
        from .adb_controller import get_adb_controller
        from .vision_engine import get_vision_engine
    except ImportError:
        from adb_controller import get_adb_controller
        from vision_engine import get_vision_engine
    import time

    # 1. Initialize Controllers
    adb = get_adb_controller()
    vision = get_vision_engine()

    if not adb.is_connected():
        # Auto-connect attempt
        if not adb.connect():
             return {"error": "Device not connected"}

    # 2. Capture Screenshot
    timestamp = int(time.time())
    filename = f"screen_{timestamp}.png"
    try:
        saved_filename = adb.take_screenshot(filename)
    except Exception as e:
        return {"error": f"Failed to take screenshot: {str(e)}"}

    # 3. Analyze Image
    # Full path for vision engine
    full_path = os.path.join(SCREENSHOT_DIR, saved_filename)
    elements = vision.analyze_image(full_path)

    print(f"✅ Step complete: Captured {saved_filename}, found {len(elements)} elements.")

    # 4. Return Result
    return {
        "screenshot_url": f"http://localhost:8000/screenshots/{saved_filename}",
        "elements": elements
    }

# --- Chạy Server (Dành cho Debug) ---
if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Database path: {DB_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
