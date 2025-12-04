# Active Motion

### What is this?

This is an autonomous AI agent designed to navigate Android applications, analyze user interfaces, and correlate on-screen actions with network traffic.

Think of it as a relentless digital QA tester that never sleeps, captures every packet via Burp Suite, and draws a pretty node-based graph of your application's logic. It uses computer vision to see buttons, LLMs to decide what to click, and ADB to physically (well, virtually) poke the screen.

### The Architecture

* **Brain:** Python (FastAPI) handling logic and ADB commands.
* **Eyes:** Microsoft OmniParser + LLMs (OpenRoute) to detect UI elements.
* **Memory:** SQLite with metadata caching (because storing raw HTML bodies is a bad time).
* **Face:** Node.js + React Flow for a Figma-like interactive dashboard.
* **Network:** Burp Suite Professional for capturing the dirty work happening under the hood.

### Status: "It works on my machine"

This project is currently under heavy development.

**Important Note:** This is entirely built and maintained by **one person**. If you find a bug, a missing feature, or a variable named `temp_fix_final_v2`, please be patient. I am likely refactoring the database schema for the third time this week.

---

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+ with npm
- For ADB features: Android Debug Bridge (adb)

### Step 1: Backend Setup

```bash
cd Backend
pip install -r requirements.txt
```

### Step 2: Frontend Setup

```bash
cd Frontend
npm install
```

### Step 3: Run Backend

```bash
cd Backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`

### Step 4: Run Frontend

In a new terminal:

```bash
cd Frontend
npm run dev
```

The UI will open at `http://localhost:5173`

### Troubleshooting

**Blank frontend screen?**
- Ensure backend is running at `http://localhost:8000`
- Check browser console (F12) for errors
- The frontend will show an error message if the backend isn't accessible

**Backend import errors?**
- Make sure all dependencies in `requirements.txt` are installed
- Some dependencies (torch, transformers) are large - first install may take time

**Port already in use?**
- Frontend: Vite will try port 5173, then 5174, etc.
- Backend: Change port with `--port 9000` in uvicorn command

### Author

Built by the **guyintheclouds.com**. Visit the site for more projects or to send coffee.
