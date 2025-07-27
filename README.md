# Dronify

Dronify is an advanced Flask-based REST API for controlling a multirotor drone in the AirSim simulator. It combines traditional text/voice commands with cutting-edge vision-language AI to enable intelligent, context-aware drone control.

## ✨ Key Features

- **🎯 Vision-Guided Control:** Advanced AI analyzes camera feed to plan intelligent actions
- **🗣️ Voice Commands:** Natural speech recognition with audio command processing  
- **📹 Live Video Stream:** Real-time MJPEG camera feed viewable in any browser
- **🧠 Intelligent Command Interpretation:** AI models map natural language to precise drone actions
- **🎮 RESTful API:** Clean HTTP endpoints for text, audio, and vision-guided commands
- **🌐 Web Interface:** Full-featured browser-based control panel
- **🔧 Modular Design:** Decoupled components for easy customization and extension

## 🚀 New: Vision-Language Integration

Dronify now includes **LLaVA-1.5-7B** vision-language model for intelligent scene analysis:

- **Smart Navigation:** "Navigate to the red building" → AI plans safe route
- **Obstacle Avoidance:** "Move forward safely" → AI avoids detected obstacles  
- **Object Search:** "Find people in the area" → AI controls camera and movement
- **Contextual Landing:** "Land in the safest spot" → AI analyzes ground conditions

[📖 Full Vision Guide →](VISION_GUIDE.md)

## Prerequisites

- **Unreal Engine & AirSim:** Running AirSim environment required.
- **Python:** Version 3.8 or newer.
- **pip:** Python package installer.
- **System Requirements:**
  - **RAM:** 8GB minimum (16GB recommended for vision features)
  - **GPU:** NVIDIA GPU with 6GB+ VRAM recommended for vision AI
  - **Storage:** 15GB free space for AI models
- **FFmpeg:** Required for audio file conversion.
  - Ubuntu/Debian: `sudo apt-get install ffmpeg`
  - macOS (Homebrew): `brew install ffmpeg`
  - Windows: Download from [official site](https://ffmpeg.org/) and add to PATH.

## Setup

1. **Clone the repository:**
   ```sh
   git clone https://github.com/yourusername/dronify.git
   cd dronify
   ```

2. **Create a virtual environment (recommended):**
   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```sh
   pip install -r requirements.txt
   ```

4. **Download the Vosk speech recognition model:**
   - [Download model](https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip)
   - Unzip and rename the folder to `model`
   - Place it in the same directory as `app.py`

## Running Dronify

### Option 1: Quick Start (WSL/Linux)

Use the provided startup script that handles WSL detection and network configuration:

```sh
./start_dronify.sh
```

### Option 2: Manual Start

1. **Start the AirSim simulator.**
2. **For WSL users**: Set the Windows host IP (if needed):
   ```sh
   export AIRSIM_HOST="172.20.240.1"  # Replace with your Windows IP
   ```
3. **Run the Flask API server:**
   ```sh
   python app.py
   ```
   The server may take a moment to load speech and language models.

### Web Interface

Open your browser and navigate to [http://localhost:5000](http://localhost:5000) for the web interface that includes:

- Live drone camera feed
- Text command input with quick action buttons
- Voice command recording
- Real-time command log
- AirSim connection status and reconnect functionality

## WSL Setup

If you're running Python in WSL with AirSim on Windows, see the detailed [WSL Setup Guide](WSL_SETUP.md) for:

- Network configuration between WSL and Windows
- Firewall setup instructions
- Troubleshooting connectivity issues
- Advanced configuration options

## API Usage

### 1. Live Video Stream

- **Endpoint:** `GET /video_feed`
- **Usage:** Open [http://127.0.0.1:5000/video_feed](http://127.0.0.1:5000/video_feed) in your browser.

### 2. Text Commands

- **Endpoint:** `POST /command`
- **Body:** JSON with a `command` key.
- **Example:**
  ```sh
  curl -X POST -H "Content-Type: application/json" \
    -d '{"command": "take off"}' \
    http://127.0.0.1:5000/command
  ```

### 3. Audio Commands

- **Endpoint:** `POST /audio_command`
- **Body:** `multipart/form-data` with an audio file (`audio` field).
- **Example:**
  ```sh
  curl -X POST -F "audio=@my_command.wav" http://127.0.0.1:5000/audio_command
  ```
  The API responds with the transcribed text, interpreted command, and execution result.

---

For more details, see the source code and comments in `app.py