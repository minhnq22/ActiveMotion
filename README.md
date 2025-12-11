# Active Motion

### What is this?

This is an autonomous AI agent designed to navigate Android applications, analyze user interfaces, and correlate on-screen actions with network traffic.

Think of it as a relentless digital QA tester that never sleeps, captures every packet via Burp Suite, and draws a pretty node-based graph of your application's logic. It uses computer vision to see buttons, LLMs to decide what to click, and ADB to physically (well, virtually) poke the screen.

### The Architecture

* **Brain:** Python (FastAPI) handling logic and ADB commands.
* **Eyes:** **Vision Engine** using OmniParser (YOLO + Florence-2) optimized for Apple Silicon (MPS).
* **Memory:** SQLite with metadata caching (because storing raw HTML bodies is a bad time).
* **Face:** Node.js + React Flow for a Figma-like interactive dashboard.
* **Network:** Burp Suite Professional for capturing the dirty work happening under the hood.

### Status: "It works on my machine"

This project is currently under heavy development.

**Important Note:** This is entirely built and maintained by **one person**. If you find a bug, a missing feature, or a variable named `temp_fix_final_v2`, please be patient. I am likely refactoring the database schema for the third time this week.

---

## Quick Start

### Prerequisites
- **OS**: macOS (optimized for Apple Silicon) or Linux.
- **Python**: 3.10+
- **Node.js**: 18+ with npm
- **ADB**: Android Debug Bridge must be installed and accessible in your PATH.
- **Device**: An Android device or emulator connected via ADB.

### 🚀 One-Click Start

We have a magical script that does everything for you (creates venv, installs dependencies, starts servers):

```bash
./start.sh
```

The script will launch:
- **Frontend**: http://localhost:5173
- **Backend**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

### 🛠 Manual Setup (The "Hard" Way)

If you prefer to type more commands:

#### 1. Backend Setup
```bash
cd Backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 2. Frontend Setup
```bash
cd Frontend
npm install
npm run dev
```

### Troubleshooting

**Vision Engine not loading?**
- This project uses **OmniParser** (YOLO detection + Florence-2 captioning).
- On **macOS**, it automatically uses **MPS** (Metal Performance Shaders) for GPU acceleration.
- Ensure you have a working internet connection on first run to download the model weights (unless they are already in `Backend/app/weights`).

**ADB not found?**
- Make sure you can run `adb devices` in your terminal.
- If not, install via Homebrew: `brew install android-platform-tools`.

**Port usage?**
- Backend defaults to `8000`.
- Frontend defaults to `5173`.

### Author

Built by the **guyintheclouds.com**. Visit the site for more projects or to send coffee.
