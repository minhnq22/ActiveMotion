
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import sqlite3
import os
import json
import uuid
from typing import Dict, List, Optional, Tuple, Set
from datetime import datetime, timezone
import asyncio
import threading

# --- Configuration ---
app = FastAPI(title="Android Security Agent API")

# --- WebSocket Connection Manager ---
class ConnectionManager:
    """Manages WebSocket connections for live updates."""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """Accept a new WebSocket connection."""
        await websocket.accept()
        self.active_connections.add(websocket)
        print(f"✅ WebSocket client connected. Total connections: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove a WebSocket connection."""
        self.active_connections.discard(websocket)
        print(f"❌ WebSocket client disconnected. Total connections: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """Broadcast a message to all connected clients."""
        if not self.active_connections:
            return
        
        disconnected = set()
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
                print(f"📤 Sent message to client: {message}")
            except Exception as e:
                print(f"⚠️  Error sending message to client: {e}")
                disconnected.add(connection)
        
        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

# Global connection manager instance
manager = ConnectionManager()
# Server event loop reference (set on app startup) so sync code can schedule
# broadcasts onto the running loop safely.
SERVER_LOOP: Optional[asyncio.AbstractEventLoop] = None

def broadcast_update(message: dict):
    """Helper function to broadcast updates from sync contexts."""
    # If the server event loop is available, schedule the coroutine thread-safely
    # on that loop. This avoids sending on WebSocket objects from a different loop
    # (which raises exceptions). Fall back to spinning a short-lived loop in a
    # background thread if the server loop isn't set (best-effort).
    global SERVER_LOOP
    if SERVER_LOOP is not None and SERVER_LOOP.is_running():
        try:
            asyncio.run_coroutine_threadsafe(manager.broadcast(message), SERVER_LOOP)
            return
        except Exception as e:
            print(f"⚠️  Error scheduling broadcast on server loop: {e}")

    # Fallback: run broadcast in a new event loop inside a thread
    def _thread_broadcast():
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(manager.broadcast(message))
            loop.close()
        except Exception as e:
            print(f"⚠️  Error broadcasting update (fallback): {e}")

    thread = threading.Thread(target=_thread_broadcast, daemon=True)
    thread.start()


# Global variable to store background task and shutdown event
adb_monitor_task = None
shutdown_event = asyncio.Event()

async def monitor_adb_connection():
    """
    Background task that monitors ADB connection status and broadcasts changes.
    Checks connection every 2-3 seconds and only broadcasts when status changes.
    Now broadcasts full status details including unauthorized, offline, adb_missing states.
    """
    try:
        from .adb_controller import get_adb_controller
    except ImportError:
        from adb_controller import get_adb_controller
    
    adb = get_adb_controller()
    previous_status = None
    
    print("🔍 Starting ADB connection monitor...")
    
    while not shutdown_event.is_set():
        try:
            # Get full status information (not just connected/disconnected)
            status_info = adb.get_status()
            current_status = status_info["status"]
            
            # Only broadcast if status has changed
            if previous_status is not None and current_status != previous_status:
                print(f"📱 ADB status changed: {previous_status} -> {current_status}")
                
                # Broadcast full status details to all WebSocket clients
                await manager.broadcast({
                    "type": "adb_status",
                    "connected": status_info["status"] == "connected",
                    "status": status_info["status"],        # connected | disconnected | unauthorized | offline | adb_missing | error
                    "message": status_info["message"],      # Human-readable message
                    "device": status_info["device"]         # Device serial or None
                })
            
            previous_status = current_status
            
        except Exception as e:
            print(f"⚠️  Error in ADB monitor: {e}")
        
        # Wait 2.5 seconds before next check (unless shutdown requested)
        try:
            await asyncio.wait_for(shutdown_event.wait(), timeout=2.5)
            break  # Shutdown requested
        except asyncio.TimeoutError:
            continue  # Normal timeout, continue monitoring

@app.on_event("startup")
async def _set_server_loop():
    """
    Initialize server components at startup:
    1. Store the running event loop for broadcasts
    2. Pre-initialize VisionEngine singleton (loads ML models)
    3. Start ADB connection monitor background task
    """
    global SERVER_LOOP, adb_monitor_task, shutdown_event
    
    print("=" * 60)
    print("🚀 Starting Android Security Agent API")
    print("=" * 60)
    
    try:
        # 1. Store event loop for WebSocket broadcasts
        SERVER_LOOP = asyncio.get_running_loop()
        print(f"🔁 Server event loop set for broadcasts")
        
        # 2. Pre-initialize VisionEngine singleton
        # This loads ML models at startup rather than on first request
        print("\n📦 Pre-loading Vision Engine models...")
        try:
            from .vision_engine import get_vision_engine
        except ImportError:
            from vision_engine import get_vision_engine
        
        # Initialize in a thread pool to not block the event loop
        loop = asyncio.get_running_loop()
        vision_engine = await loop.run_in_executor(None, get_vision_engine)
        
        # Log Vision Engine status
        status = vision_engine.get_status()
        if status["ready"]:
            print(f"✅ Vision Engine ready on {status['device'].upper()}")
            if status['device'] == 'mps':
                print("   🍎 Apple Silicon (MPS) acceleration enabled")
        else:
            print(f"⚠️  Vision Engine not ready: {status.get('error', 'Unknown error')}")
        
        # 3. Start ADB monitoring background task
        shutdown_event.clear()
        adb_monitor_task = asyncio.create_task(monitor_adb_connection())
        print("\n✅ ADB connection monitor started")
        
        print("=" * 60)
        print("🎉 Server initialization complete!")
        print("=" * 60)
        
    except RuntimeError:
        # No running loop available (unlikely during FastAPI startup)
        SERVER_LOOP = None
        print("⚠️  Server event loop not available")

@app.on_event("shutdown")
async def _shutdown_tasks():
    """Clean shutdown of background tasks."""
    global adb_monitor_task, shutdown_event
    
    print("🛑 Shutting down background tasks...")
    shutdown_event.set()
    
    if adb_monitor_task and not adb_monitor_task.done():
        adb_monitor_task.cancel()
        try:
            await adb_monitor_task
        except asyncio.CancelledError:
            print("✅ ADB monitor task cancelled")
        except Exception as e:
            print(f"⚠️  Error cancelling ADB monitor: {e}")

# CORS configuration (Required for Frontend React to call the API)
origins = [
    "http://localhost:3000",  # React default
    "http://localhost:5173",  # Vite default
    "http://localhost",       # Docker production
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to data directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(os.path.dirname(BASE_DIR), "Data")
DB_PATH = os.path.join(DATA_DIR, "app_data.db")
SCREENSHOT_DIR = os.path.join(DATA_DIR, "screenshots")
ANNOTATED_SCREENSHOT_DIR = os.path.join(DATA_DIR, "annotated_screenshots")
SERVER_BASE_URL = os.getenv("SERVER_BASE_URL", "http://localhost:8000")

# Automatically create directories if they don't exist
os.makedirs(SCREENSHOT_DIR, exist_ok=True)
os.makedirs(ANNOTATED_SCREENSHOT_DIR, exist_ok=True)

# Mount static directories for Frontend to load images
# Example: http://localhost:8000/screenshots/img1.png
app.mount("/screenshots", StaticFiles(directory=SCREENSHOT_DIR), name="screenshots")
app.mount(
    "/annotated-screenshots",
    StaticFiles(directory=ANNOTATED_SCREENSHOT_DIR),
    name="annotated_screenshots",
)

# --- Database Helper ---
def get_db_connection():
    """Get a database connection with row factory set to return dictionaries."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dictionaries instead of tuples
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
    """Initialize database tables if they don't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Nodes table
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
    
    # Edges table
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
    
    # Traffic Index table
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

    # Parser outputs table
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


# Initialize database on app startup
init_db()

# --- Helper logic ---

def delete_node_and_related(node_id: str) -> None:
    """
    Delete a node and all related data:
    - node row
    - edges where it is source/target
    - traffic_index entries for those edges
    - parser_outputs for that node
    - screenshot and annotated_screenshot files if they exist
    """
    conn = get_db_connection()
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Fetch node to get file paths
    node_row = cursor.execute(
        "SELECT screenshot_path, annotated_screenshot_path FROM nodes WHERE id = ?",
        (node_id,),
    ).fetchone()

    if not node_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Node not found")

    screenshot_path = node_row["screenshot_path"]
    annotated_path = node_row["annotated_screenshot_path"]

    # Find all related edges
    edge_rows = cursor.execute(
        "SELECT id FROM edges WHERE source_node_id = ? OR target_node_id = ?",
        (node_id, node_id),
    ).fetchall()
    edge_ids = [row["id"] for row in edge_rows]

    # Delete traffic entries for those edges
    if edge_ids:
        placeholders = ",".join("?" for _ in edge_ids)
        cursor.execute(
            f"DELETE FROM traffic_index WHERE edge_id IN ({placeholders})",
            edge_ids,
        )

    # Delete parser output for this node
    cursor.execute("DELETE FROM parser_outputs WHERE node_id = ?", (node_id,))

    # Delete the edges themselves
    cursor.execute(
        "DELETE FROM edges WHERE source_node_id = ? OR target_node_id = ?",
        (node_id, node_id),
    )

    # Delete the node
    cursor.execute("DELETE FROM nodes WHERE id = ?", (node_id,))

    conn.commit()
    conn.close()

    # Delete files from disk (best-effort)
    if screenshot_path:
        try:
            full_screenshot_path = os.path.join(SCREENSHOT_DIR, screenshot_path)
            if os.path.exists(full_screenshot_path):
                os.remove(full_screenshot_path)
        except OSError:
            # Do not fail request if file deletion fails
            pass

    if annotated_path:
        try:
            full_annotated_path = os.path.join(ANNOTATED_SCREENSHOT_DIR, annotated_path)
            if os.path.exists(full_annotated_path):
                os.remove(full_annotated_path)
        except OSError:
            # Do not fail request if file deletion fails
            pass


# --- API Endpoints ---

@app.get("/")
def read_root():
    """Root endpoint with system status."""
    try:
        from .vision_engine import get_vision_engine
    except ImportError:
        from vision_engine import get_vision_engine
    
    vision = get_vision_engine()
    vision_status = vision.get_status()
    
    return {
        "status": "Agent is Ready", 
        "burp_connected": False,
        "vision_engine": {
            "ready": vision_status["ready"],
            "device": vision_status["device"],
            "mps_enabled": vision_status["device"] == "mps",
        }
    }


@app.get("/api/vision/status")
def get_vision_status():
    """
    Get detailed Vision Engine status.
    Useful for debugging MPS acceleration and model loading.
    """
    try:
        from .vision_engine import get_vision_engine
    except ImportError:
        from vision_engine import get_vision_engine
    
    vision = get_vision_engine()
    return vision.get_status()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live updates."""
    await manager.connect(websocket)
    
    try:
        # Send initial ADB status immediately upon connection
        try:
            from .adb_controller import get_adb_controller
        except ImportError:
            from adb_controller import get_adb_controller
        
        adb = get_adb_controller()
        status_info = adb.get_status()
        
        await websocket.send_json({
            "type": "adb_status",
            "connected": status_info["status"] == "connected",
            "status": status_info["status"],
            "message": status_info["message"],
            "device": status_info["device"]
        })
        print(f"📤 Sent initial ADB status to new client: {status_info['status']}")
        
        # Keep connection alive and handle incoming messages
        while True:
            # Wait for any message from client (ping/pong or other commands)
            data = await websocket.receive_text()
            # Echo back or handle commands if needed
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"⚠️  WebSocket error: {e}")
        manager.disconnect(websocket)


@app.get("/api/graph")
def get_graph_data():
    """
    API endpoint that returns data formatted for React Flow.
    """
    conn = get_db_connection()
    nodes = conn.execute("SELECT * FROM nodes").fetchall()
    edges = conn.execute("SELECT * FROM edges").fetchall()
    traffic_by_node, traffic_by_edge = load_traffic_maps(conn)
    parser_by_node = load_parser_outputs(conn)
    conn.close()
    
    # Format according to React Flow standard
    formatted_nodes = []
    for node in nodes:
        formatted_nodes.append({
            "id": node["id"],
            "type": "screenshotNode",
            "position": {"x": 0, "y": 0},  # TODO: Add auto-layout logic
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
    node_id = str(uuid.uuid4())
    filename = f"{node_id}.png"
    annotated_filename = f"{node_id}_annotated.png"
    
    try:
        saved_filename = adb.take_screenshot(filename)
    except Exception as e:
        return {"error": f"Failed to take screenshot: {str(e)}"}

    # 3. Analyze Image & Generate Annotated Screenshot
    full_path = os.path.join(SCREENSHOT_DIR, saved_filename)
    annotated_full_path = os.path.join(ANNOTATED_SCREENSHOT_DIR, annotated_filename)
    
    # analyze_image handles both analysis and annotation
    analysis_result = vision.analyze_image(full_path, annotated_output_path=annotated_full_path)
    
    parsed_content_list = analysis_result.get("parsed_content_list", [])
    label_coordinates = analysis_result.get("label_coordinates", {})
    
    print(f"✅ Step complete: Captured {saved_filename}, found {len(parsed_content_list)} elements.")

    # 4. Save to Database
    conn = get_db_connection()
    cursor = conn.cursor()

    # Save Node
    cursor.execute(
        """
        INSERT INTO nodes (id, label, description, screenshot_path, annotated_screenshot_path)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            node_id,
            f"Screen {timestamp}",
            f"Captured at {datetime.fromtimestamp(timestamp).strftime('%H:%M:%S')}",
            saved_filename,
            annotated_filename
        )
    )

    # Save Parser Output
    cursor.execute(
        """
        INSERT INTO parser_outputs (node_id, parsed_content_list, label_coordinates)
        VALUES (?, ?, ?)
        """,
        (
            node_id,
            json.dumps(parsed_content_list),
            json.dumps(label_coordinates),
        )
    )
    
    conn.commit()
    conn.close()

    # 5. Broadcast update to all connected clients
    print(f"📢 Broadcasting update for new node: {node_id}")
    broadcast_update({
        "type": "graph_updated",
        "message": "New node created",
        "nodeId": node_id
    })

    # 6. Return Result
    return {
        "id": node_id,
        "screenshot_url": build_static_url(saved_filename, "/screenshots"),
        "annotated_screenshot_url": build_static_url(annotated_filename, "/annotated-screenshots"),
        "parser": {
            "parsedContentList": parsed_content_list,
            "labelCoordinates": label_coordinates
        }
    }


@app.delete("/api/nodes/{node_id}")
def delete_node(node_id: str):
    """
    Delete a node and all associated data + screenshots.
    """
    delete_node_and_related(node_id)
    
    # Broadcast update to all connected clients
    broadcast_update({
        "type": "graph_updated",
        "message": "Node deleted",
        "nodeId": node_id
    })
    
    return {"status": "deleted", "nodeId": node_id}

# --- Run Server (For Debug) ---
if __name__ == "__main__":
    import uvicorn
    print(f"🚀 Database path: {DB_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=8000)
