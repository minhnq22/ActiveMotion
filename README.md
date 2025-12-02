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

### Author

Built by the **guyintheclouds.com**. Visit the site for more projects or to send coffee.
