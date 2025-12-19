# 🧠 Knowledge Pipeline

**A local-first AI pipeline that turns voice notes and text into structured Obsidian knowledge using offline Whisper and Open WebUI. Features deep offline LLM analysis of notes. 100% Private & Self-Hosted.**

---

## 📖 Table of Contents
1. [Overview & Features](#-overview--features)
2. [How It Works](#-the-workflow-from-voice-to-knowledge)
3. [Prerequisites](#-part-1-prerequisites-before-you-begin)
4. [Installation & Setup](#-part-2-setup-pipeline)
5. [Running the Application](#-part-3-running-the-application)
6. [Optional Integrations](#-part-4-optional-integrations)
7. [Disclaimer & Legal](#-disclaimer--legal)

---

## 🌟 Overview & Features

**Knowledge Pipeline** is your personal, **Local-First** archivist designed for **Maximum Privacy**. It bridges the gap between your raw thoughts (voice recordings, rough notes) and a structured, searchable Second Brain (like Obsidian or Open WebUI).

Unlike cloud-based services, this pipeline runs locally on your machine. Your voice and thoughts are processed by **Local AI**, ensuring that your private journal entries and sensitive meeting notes never leave your control.

### ✨ Key Highlights
* **🔒 Maximum Privacy:** All audio processing happens offline using FFmpeg and Whisper. No third-party servers listen to your recordings.
* **🗣️ Voice-to-Knowledge:** Turns messy voice memos into structured, formatted Markdown notes automatically.
* **🤖 Local AI Intelligence:** Your self-hosted AI (Open WebUI) automatically generates Titles, Summaries, lists of Characters, and detects Emotions.
* **📂 Auto-Sorting:** Classifies your notes (e.g., "Personal Diary" vs. "Work Meeting") based on detection keywords you define.
* **🔄 Live Sync:** Edits made in your local folder are instantly updated in your self-hosted Chatbot's vector database.
* **🎯 Focus Mode:** Mark specific files with `focus: true` to create a temporary "Chat Context" across different topics.

---

## 🔄 The Workflow: From Voice to Knowledge

### 1. The Input
You record a voice note or write a text file.
* **Audio:** Copy `.mp3`, `.wav`, or `.m4a` files into the `Input Audio` folder.
* **Text:** Copy `.txt` or `.md` files into the `Input Text` folder.
* *Tip:* You can use keywords while recording (e.g., "Hashtag Urgent") to automatically tag files.

### 2. Local Processing
* **Transcription:** The offline Whisper engine converts speech to text.
* **Metadata:** The system extracts dates from filenames (e.g., `20251027.m4a`) or spoken dates (e.g., "Date: October 27th").

### 3. AI Enrichment
The text is sent to your local Open WebUI instance to:
* Classify the content type (e.g., Meeting vs. Diary).
* Generate a summary and title.
* Run deep analysis (e.g., "Extract Action Items") based on your custom prompts.

### 4. Storage & Sync
* The final file is saved as Markdown in your **Knowledge Folder**.
* It is simultaneously uploaded to an **Open WebUI Collection** so you can chat with it immediately.

---

## 🛠️ Part 1: Prerequisites (Before you begin)

Before installing the main application, you need **Open WebUI** (the AI brain) installed on your computer.

### 1. Install Open WebUI
This is the interface where your AI lives.
* **Step A: Install Docker**
    * Download and install **Docker Desktop** from [docker.com](https://www.docker.com/products/docker-desktop/).
    * Run Docker Desktop and let it start up.
* **Step B: Install Open WebUI**
    1.  Open your Command Prompt (Press `Windows Key + R`, type `cmd`, press Enter).
    2.  Copy and paste this command and press Enter:
        `docker run -d -p 3000:8080 -v open-webui:/app/backend/data --name open-webui ghcr.io/open-webui/open-webui:main`
    3.  Once finished, open your web browser and go to: `http://localhost:3000`

### 2. Setup Your AI Model
1.  Open **Open WebUI** in your browser (`http://localhost:3000`).
2.  Go to **Settings** > **Models**.
3.  In the "Pull a model" section, type `llama3.1:8b` (the default recommendation) and click the download button. Wait for it to complete.

### 3. Create a Knowledge Collection
This is the "folder" inside the AI where your files will be stored.
1.  In Open WebUI, go to **Workspace** -> **Knowledge**.
2.  Click **+ Create Knowledge Base**.
3.  Name it (e.g., "My Journal") and save it.
4.  **Crucial Step:** Look at the URL in your browser address bar. It will look something like this:
    `http://localhost:3000/workspace/knowledge/7e9d0e83-0f8f-80ed-aa3b-4a8edd5ebd04`
5.  Copy that long code (the UUID) at the end. You will need this for the setup below.

---

## ⚙️ Part 2: Setup Pipeline

Now that the prerequisites are ready, let's configure the main application.

1.  **Extract Files:**
    * Unzip the release file to a folder of your choice (e.g., `C:\MyApps\Knowledge`).
2.  **Run the Configuration Tool:**
    * Navigate to the **`config`** folder.
    * Double-click **`Setup_Knowledge_Pipeline.exe`**.
    * *Note:* If you are running from source code, you can run `python configure.py` instead.
3.  **Configure Your Settings (GUI):**
    Use the tabs in the setup tool to configure the app easily:
    * **Folders & Paths:** Select your "Base Directory" (where you want your files stored).
    * **Credentials:** Enter your `API Key` (from Open WebUI Settings) and `URL` (usually `http://localhost:3000`).
    * **Content Types:** Here you define how the app sorts your files. You can create types like "Dream Journal" or "Meeting", set their detection keywords (e.g., "dream", "sleep"), and paste the Collection UUID you copied in Part 1.
4.  **Finish:**
    * Click **"SAVE ALL SETTINGS"** at the bottom.
    * Close the setup tool.

---

## 🚀 Part 3: Running the Application

1.  Navigate to your application folder.
2.  Double-click `KnowledgePipeline.exe` (or run `python main.py` if running from source).
3.  A black window (console) will appear.
    * **First Run Note:** It might take a few minutes to download the Whisper AI model (approx 500MB - 1.5GB). **Do not close it** if it looks stuck.
4.  Minimize the window and let it run in the background.
5.  **To Stop:** Simply close the black window.

---

## 🔄 Part 4: Optional Integrations

### Auto-Sync from Phone (Syncthing)
To automatically transfer voice recordings and text notes from your phone to this application without cables:
1.  **Install Syncthing:** Download from [syncthing.net](https://syncthing.net/) (PC) and install the app on your phone.
2.  **Connect Devices:** Add your PC as a "Device" on your phone by scanning the QR code.
3.  **Sync Folders:**
    * Create a folder sync on your phone (e.g., your Voice Recorder folder).
    * Share it with your PC.
    * On your PC, map this folder to the **`Input Audio`** folder inside your Knowledge Pipeline directory.

### View with Obsidian
For the best experience viewing your sorted files:
1.  Download **Obsidian** from [obsidian.md](https://obsidian.md).
2.  Click **"Open folder as vault"**.
3.  Select your `Knowledge` folder (defined in your settings).
4.  You can now browse your automatically sorted and AI-analyzed files beautifully!

---

## ⚖️ Disclaimer & Legal

### Liability
-   **AI Accuracy:** This application uses Large Language Models (LLMs) and Speech-to-Text AI. These models can "hallucinate" or generate inaccurate information. Always review critical summaries (like action items) manually.
-   **Data Privacy:** This application is designed to run locally. However, if you configure it to use remote endpoints or cloud APIs, your data will leave your machine. You are responsible for securing your own API keys and network.
-   **No Warranty:** This software is provided "as is," without warranty of any kind. The authors are not liable for any data loss or damages arising from its use.

### Acknowledgments
* **Gemini (Google DeepMind):** For generating the core Python scripts and architecture.
* **OpenAI Whisper:** For the incredible speech-to-text engine.
* **Open WebUI:** For the powerful interface and local AI orchestration.
* **FFmpeg:** For handling audio processing.

### License
This project is licensed under the MIT License. See the `LICENSE` file for details.