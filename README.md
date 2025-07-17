# ActiveMotion: Your Phone's Personal Security Intern 🕵️‍♂️

Tired of manually tapping through every single screen of an app just to see what it does? Wish you could just unleash a smart agent to explore an Android app, map out its features, and even sniff its network traffic for security holes? Well, you've stumbled into the right corner of the internet.

**ActiveMotion** is an automated exploration tool for Android applications. It connects to your device via ADB, intelligently navigates through an app using AI, and figures out what the app is all about. Think of it as a super-curious, slightly mischievous intern you can assign to any app.

## What's the Big Idea? 🤔

This project is the love child of two brilliant ideas:

1.  **Seeing the screen like a human:** Inspired by [Microsoft's OmniParser](https://github.com/microsoft/OmniParser), ActiveMotion uses computer vision to understand UI elements without needing any of that boring developer stuff like view hierarchies. It just *looks* at the screen and gets it.
2.  **Automating tasks with a brain:** Taking a cue from [VisionTasker](https://github.com/AkimotoAyako/VisionTasker), ActiveMotion uses an online Large Language Model (LLM) to decide what to do next. It's like having a tiny, super-smart robot brain living in your project folder.

Combine them, and you get a system that can autonomously explore an Android app, creating a complete summary of its features. No manual labor required!

## How the Magic Happens ✨

1.  **Connect & Screenshot:** ActiveMotion connects to your Android device over ADB and takes a screenshot of the current screen.
2.  **Parse & Understand:** The image is fed to a vision model that identifies all the interactive elements – buttons, text boxes, etc.
3.  **Think & Decide:** This structured data is sent to an online LLM, which decides the next best action to take to continue exploring the app.
4.  **Translate & Execute:** The action (e.g., "tap the 'Login' button") is translated into an ADB command and sent to your device.
5.  **Loop & Learn:** The process loops over and over, creating a map of the application's features.
6.  **Summarize:** Once the exploration is complete, ActiveMotion generates a summary of all the features it discovered.

## Installation Guide 🚀

Ready to unleash the beast? Here's how to get started.

**Prerequisites:**

*   An Android device with USB debugging enabled.
*   Python 3.8 or higher.

**Step-by-step installation:**

1.  **Clone the repo (duh):**
    ```bash
    git clone https://github.com/your-username/ActiveMotion.git
    cd ActiveMotion
    ```

2.  **Create a cozy virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the goodies from `requirements.txt`:**
    ```bash
    pip install -r requirements.txt
    ```

## Quickstart ⚡

To run the main script and start exploring, use the following command:

```bash
python main.py --app "com.example.appname"
```

**Disclaimer:** May occasionally get stuck in a settings menu for an eternity. It's learning, be patient.

## The Future is Now (Almost) 🔮

This is where it gets *really* interesting. The next major step for ActiveMotion is to become a powerful tool for security researchers.

**The Grand Plan:**

*   **Traffic Logging:** While the agent is exploring, it will also capture all network traffic (requests and responses).
*   **Action-Traffic Mapping:** Each captured request will be automatically matched to the specific action that triggered it (e.g., this API call happened when the "Add to Cart" button was tapped).
*   **Automated Security Analysis:** The final output will be a detailed report: a full feature map of the app, complete with the corresponding network traffic for each feature. This will allow security researchers to instantly pinpoint interesting areas, analyze potential attack vectors, and find vulnerabilities without the tedious manual work.

---

**Happy automating!** And if your phone starts trying to hack the planet, well, you know who to thank.