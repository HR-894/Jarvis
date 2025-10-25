# Makkhan Mode Jarvis 🧈

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)

**A lightweight, offline-first, Hinglish voice assistant optimized for low-resource Linux environments, including WSL2.**

This project provides a foundational voice assistant capable of hotword detection, speech-to-text, intent recognition, command execution, and text-to-speech, prioritizing minimal resource consumption and offline functionality.

---

## Motivation

Modern voice assistants often rely heavily on cloud processing and substantial hardware resources. **Makkhan Mode Jarvis** explores the feasibility of creating a responsive and useful voice assistant on constrained hardware (e.g., older laptops, single-board computers) by leveraging efficient, locally-run, open-source tools. The focus is on **offline operation**, **low latency for basic commands**, and **minimal background load**.

---

## ✨ Features

* **Offline Core Functionality:** Designed to run without internet connectivity for core features.
* **Low Resource Usage:** Optimized C++ backends (`whisper.cpp`, `llama.cpp`, `piper`) for minimal CPU/RAM footprint.
* **Hotword Detection:** Reliable wake-word detection using PicoVoice Porcupine (Free Tier).
* **Bilingual TTS:** Natural speech synthesis via `piper-tts` supporting:
    * Hindi (Male - `rohan` model)
    * British English (Male - `alan` model)
    * British English (Female - `alba` model)
* **Fast STT:** Offline speech-to-text using quantized `whisper.cpp` models (e.g., `tiny.en`).
* **Rule-Based Intent Parsing:** Quick recognition of predefined commands using keyword matching (`intent_parser.py`).
* **Optional LLM Integration:** Supports `llama.cpp` for handling more complex queries (resource-intensive, best for "high-power" mode).
* **Safe Command Execution:** Whitelisted command execution via `safe_runner.py` prevents unauthorized actions.
* **Basic Interrupt Handling:** Allows interrupting TTS playback via VAD.
* **Configurable:** Easy setup and modification through `config.json`.

---

## 🏗️ Architecture Overview

The assistant operates in a sequential loop:

1.  **Listen for Hotword:** `pvporcupine` continuously monitors the microphone input via `sounddevice`.
2.  **(Optional) Verify Speaker:** `resemblyzer` compares a short audio sample against a pre-enrolled voiceprint (disabled by default).
3.  **Record Command:** `webrtcvad` detects speech onset and silence to capture the user's command via `sounddevice`.
4.  **Speech-to-Text:** The recorded audio (`.wav`) is optionally amplified using `ffmpeg` and then transcribed by `whisper.cpp`.
5.  **Process Command:**
    * The transcribed text is checked for special commands (e.g., renaming via `jarvis_name_manager.py`).
    * If not a special command, `intent_parser.py` attempts to match keywords to predefined actions in `whitelist.yml`.
    * If no intent is matched and LLM is enabled (`balanced` or `high-power` mode), the text is passed as a prompt to `llama.cpp`.
6.  **Execute Action:** If an intent is found, `safe_runner.py` executes the corresponding whitelisted command.
7.  **Text-to-Speech:** The resulting text response (from command execution or LLM) is synthesized into speech using `piper-tts` (`tts.py`).
8.  **Loop:** The system returns to listening for the hotword.

---

## 💻 System Requirements

### Hardware
* **CPU:** Modern dual-core processor (e.g., Ryzen 3, Intel i3 or equivalent).
* **RAM:** **Minimum 8GB** (primarily for OS and base models). 16GB+ highly recommended if using the 7B LLM.
* **Storage:** ~10-15 GB free space (OS + Code + Models).
* **Microphone:** Standard system microphone.

### Software
* **OS:** Linux (Ubuntu 22.04 recommended) or WSL2 on Windows 10/11.
* **Core Dependencies:** `git`, `build-essential`, `cmake`, `pkg-config`, `python3.10+`, `pip`, `venv`.
* **Audio/Utils:** `alsa-utils`, `ffmpeg`, `psmisc`, `git-lfs`, `libsndfile1`.
* **Python Packages:** See `requirements.txt`.

---

## 🚀 Installation Guide

**(Run these commands within your Linux/WSL Ubuntu terminal)**

1.  **Clone the Repository (or create manually):**
    ```bash
    git clone <your-repo-url> makkhan-jarvis
    cd makkhan-jarvis
    # Create the necessary Python files if not cloning
    ```

2.  **Install System Dependencies:**
    ```bash
    sudo apt update && sudo apt upgrade -y
    sudo apt install -y git build-essential cmake pkg-config python3.10-venv python3-pip alsa-utils ffmpeg psmisc git-lfs libsndfile1
    ```

3.  **Set up Python Virtual Environment:**
    ```bash
    python3 -m venv jarvis_env
    source jarvis_env/bin/activate
    # Create requirements.txt from the content provided earlier
    nano requirements.txt
    pip install -r requirements.txt
    ```

4.  **Build `whisper.cpp`:**
    ```bash
    git clone [https://github.com/ggerganov/whisper.cpp.git](https://github.com/ggerganov/whisper.cpp.git)
    cd whisper.cpp
    bash ./models/download-ggml-model.sh tiny.en # Or another preferred model
    make # This compiles the 'main' executable needed
    cd ..
    ```

5.  **Build `llama.cpp` (Optional):**
    ```bash
    git clone [https://github.com/ggerganov/llama.cpp.git](https://github.com/ggerganov/llama.cpp.git)
    cd llama.cpp
    mkdir build && cd build
    cmake .. -DLLAMA_CURL=OFF # Disable network features if not needed
    cmake --build . --config Release
    cd .. # Back to llama.cpp root
    mkdir models
    # Download your desired GGUF model (example below)
    wget -c -O models/mistral-7b-openhermes.Q4_K_M.gguf "[https://huggingface.co/TheBloke/OpenHermes-2.5-Mistral-7B-GGUF/resolve/main/openhermes-2.5-mistral-7b.Q4_K_M.gguf](https://huggingface.co/TheBloke/OpenHermes-2.5-Mistral-7B-GGUF/resolve/main/openhermes-2.5-mistral-7b.Q4_K_M.gguf)"
    cd .. # Back to project root
    ```

6.  **Setup `piper-tts`:**
    ```bash
    # Download Piper binary
    wget "[https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz](https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz)"
    tar -xzf piper_amd64.tar.gz
    rm piper_amd64.tar.gz # Cleanup archive

    # Download Piper voices using Git LFS
    git clone [https://huggingface.co/rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices)
    cd piper-voices
    git lfs pull --include="hi/hi_IN/rohan/medium/*" # Hindi Male
    git lfs pull --include="en/en_GB/alan/medium/*" # British Male
    git lfs pull --include="en/en_GB/alba/medium/*" # British Female
    cd .. # Back to project root

    # Copy downloaded models to Piper's runtime directory
    cp -f piper-voices/hi/hi_IN/rohan/medium/* piper/
    cp -f piper-voices/en/en_GB/alan/medium/* piper/
    cp -f piper-voices/en/en_GB/alba/medium/* piper/
    ```

7.  **Configure PicoVoice Porcupine:**
    * Sign up/in at [PicoVoice Console](https://console.picovoice.ai/).
    * Copy your **AccessKey**.
    * Download the **Porcupine Keyword File (`.ppn`)** for **Linux** (e.g., "Jarvis", "Friday"). Unzip it if necessary.
    * Move the `.ppn` file into the project's root directory (`~/jarvis` or `makkhan-jarvis`). For WSL, use:
        ```bash
        # Replace USERNAME and FILENAME accordingly
        cp /mnt/c/Users/YOUR_WINDOWS_USERNAME/Downloads/PATH_TO_UNZIPPED_FOLDER/YOUR_KEYWORD.ppn .
        ```

8.  **Create and Configure `config.json`:**
    * Create the file: `nano config.json`
    * Paste the configuration template (provided below).
    * Fill in your `PICOVOICE_ACCESS_KEY`.
    * Set the correct path and filename for `PICOVOICE_KEYWORD_PATH`. Ensure it includes your Ubuntu username (e.g., `/home/hr_894/...`).
    * Adjust `JARVIS_NAME` to match your hotword.

9.  **(Optional but Recommended) Enroll Voice:**
    * Adjust your system microphone input level (Windows Settings or Linux equivalent) to be sufficiently loud (80%+).
    * Run the enrollment script: `python3 speaker_enroll.py`
    * Speak clearly for 5 seconds when prompted. This creates `speaker_embed.npy`.
    * *Note: Speaker verification is disabled by default in `main.py` due to sensitivity. Uncomment the relevant lines in `main_loop` if you wish to use it.*

---

## ⚙️ Configuration File (`config.json`)

```json
{
  "PICOVOICE_ACCESS_KEY": "YOUR_PICOVOICE_ACCESS_KEY_HERE",
  "PICOVOICE_KEYWORD_PATH": "/home/YOUR_UBUNTU_USERNAME/jarvis/YOUR_KEYWORD_FILE.ppn",
  "JARVIS_NAME": "Friday",
  "USER_NAME": "Sir",
  "SPEAKER_EMBED_PATH": "/home/YOUR_UBUNTU_USERNAME/jarvis/speaker_embed.npy",
  "MODE": "balanced"
}
Replace placeholders with your actual values.

MODE can be:

low-power: Minimal resource usage, LLM disabled.

balanced: Default, uses intent parser, falls back to LLM if available.

high-power: Reserved for future use (could prioritize LLM).

▶️ Usage
Navigate to Project Directory:

Bash

cd ~/jarvis # Or your project folder name
Activate Python Environment:

Bash

source jarvis_env/bin/activate
Run the Assistant:

Bash

python3 main.py
Wait for the "Jarvis is ready..." startup message.

Say the hotword (e.g., "Friday").

Wait for the "Yes sir?" prompt.

Speak your command.

Press Ctrl+C to exit.

📁 Project Structure
-jarvis/
│
├── jarvis_env/              # Python virtual environment folder (created by 'venv')
│   ├── bin/                 # Contains activation scripts (like 'activate')
│   ├── lib/                 # Stores installed Python packages (via pip)
│   └── ...                  # Other standard venv folders (include, pyvenv.cfg)
│
├── whisper.cpp/             # Cloned repository for whisper.cpp
│   ├── build/               # Directory created by CMake during compilation
│   │   ├── bin/             # Contains the compiled executable programs
│   │   │   └── main         # <<< The main Whisper STT executable we run
│   │   └── ...              # Other CMake build artifacts (Makefiles, object files)
│   ├── models/              # Directory for Whisper models
│   │   └── ggml-tiny.en.bin # <<< The downloaded 'tiny.en' STT model file
│   ├── CMakeLists.txt       # Build configuration for CMake
│   ├── main.cpp             # Source code for the 'main' executable
│   └── ...                  # Other source code files (.h, .cpp), scripts, examples
│
├── llama.cpp/               # Cloned repository for llama.cpp (Optional, for LLM)
│   ├── build/               # Directory created by CMake during compilation
│   │   ├── bin/             # Contains the compiled executable programs
│   │   │   └── main         # <<< The main Llama LLM executable we run
│   │   └── ...              # Other CMake build artifacts
│   ├── models/              # Directory for LLM models
│   │   └── *.gguf           # <<< Your downloaded GGUF model file (e.g., mistral-7b...)
│   ├── CMakeLists.txt       # Build configuration for CMake
│   └── ...                  # Other source code files, examples
│
├── piper/                   # Directory containing the Piper TTS runtime
│   ├── piper                # <<< The Piper TTS executable binary
│   ├── hi_IN-rohan-medium.onnx      # <<< Hindi voice model file
│   ├── hi_IN-rohan-medium.onnx.json # <<< Hindi voice configuration file
│   ├── en_GB-alan-medium.onnx       # <<< British Male voice model file
│   ├── en_GB-alan-medium.onnx.json  # <<< British Male voice configuration file
│   ├── en_GB-alba-medium.onnx       # <<< British Female voice model file
│   ├── en_GB-alba-medium.onnx.json  # <<< British Female voice configuration file
│   └── *.so* # Shared library files needed by Piper runtime
│
├── piper-voices/            # Cloned repository containing all Piper voice models (using Git LFS)
│   ├── hi/                  # Folder structure for Hindi voices
│   │   └── hi_IN/
│   │       └── rohan/
│   │           └── medium/
│   │               ├── hi_IN-rohan-medium.onnx      # Actual LFS file (downloaded)
│   │               └── hi_IN-rohan-medium.onnx.json
│   ├── en/                  # Folder structure for English voices
│   │   └── en_GB/
│   │       ├── alan/
│   │       │   └── medium/  # Contains alan model files
│   │       └── alba/
│   │           └── medium/  # Contains alba model files
│   ├── .git/                # Git repository data
│   ├── .gitattributes       # File specifying which files use Git LFS
│   └── ...                  # Folders for many other languages
│
├── config.json              # <<< Main JSON configuration (API keys, paths, names)
├── whitelist.yml            # <<< YAML file defining allowed commands
├── requirements.txt         # <<< List of Python packages for pip install
│
├── main.py                  # <<< The primary Python script that runs the assistant loop
├── tts.py                   # <<< Python script to handle calling Piper TTS
├── intent_parser.py         # <<< Python script for simple keyword-based intent matching
├── safe_runner.py           # <<< Python script for executing whitelisted commands
├── jarvis_name_manager.py   # <<< Python script to handle name change commands
├── speaker_enroll.py        # <<< Python script to record and save the user's voiceprint
│
├── speaker_embed.npy        # <<< Saved NumPy array containing the user's voiceprint data
├── YOUR_KEYWORD_FILE.ppn    # <<< Your downloaded PicoVoice Porcupine hotword file (e.g., Friday_en_linux_v3_0_0.ppn)
│
├── temp_tts_output.raw      # Temporary raw audio file generated by Piper TTS (overwritten often)
├── temp_stt_input.wav       # Temporary WAV file created from user's speech recording
├── temp_stt_amplified.wav   # Temporary amplified/normalized WAV file processed by ffmpeg
│
└── README.md                # <<< Project documentation file (you are here!)
Key takeaways:

Separation: C++ tools (whisper.cpp, llama.cpp) and the TTS engine (piper) are kept in their own directories.

Models: Models for each tool are generally stored within their respective directories (models/ or directly in piper/).

Configuration: Core settings are centralized in config.json and whitelist.yml.

Python Logic: Your custom Python code (main.py, tts.py, etc.) resides in the main project root.

Environment: Python packages are isolated within jarvis_env/.

Temporary Files: Audio files generated during operation (temp_*.wav, temp_*.raw) are stored in the root but are transient.
🛠️ Customization & Extension
Add Commands: Define new commands in whitelist.yml and add corresponding keywords/logic in intent_parser.py.

Improve Intents: Enhance INTENT_MAP in intent_parser.py with more phrases or use a more sophisticated NLU library for balanced mode.

Change Voices/Languages: Download additional piper models via git lfs pull in the piper-voices directory, copy them to piper/, and update tts.py to support new language codes/paths.

Tune Performance: Adjust thread counts (-t flag) for whisper.cpp and llama.cpp calls in main.py based on your CPU. Modify VAD settings (max_silence_frames) in record_command.

Enable/Tune Verification: Uncomment the verification block in main.py and potentially adjust the similarity > 0.75 threshold.

❓ Troubleshooting
Audio Issues: Restart WSL (wsl --shutdown). Check system audio settings (mute, volume, mic levels). Ensure alsa-utils is installed.

whisper.cpp/llama.cpp Errors (exit status 1 or No such file): Verify the executable exists in the correct build/bin/ path specified in main.py. Ensure the corresponding model file (.bin or .gguf) exists, is not corrupt (re-download if necessary using the official scripts or wget -c), and that ffmpeg correctly processes the audio for Whisper.

Hotword Issues: Check config.json for correct AccessKey and .ppn file path. Test microphone independently.

Model Download Issues (404 or Corrupt Files): Use git lfs pull --include="..." within the piper-voices directory instead of wget for Piper models. For .cpp models, use the official download scripts or wget -c. Delete potentially corrupt files before re-downloading.

🤝 Contributing
Contributions are welcome! Please feel free to submit pull requests or open issues for bugs, feature requests, or improvements.

📜 License
This project is licensed under the MIT License - see the LICENSE file for details (You would need to create a LICENSE file with the MIT license text).

🙏 Acknowledgements
This project heavily relies on the fantastic work of the following open-source projects:

whisper.cpp by Georgi Gerganov

llama.cpp by Georgi Gerganov

piper by Rhasspy

PicoVoice Porcupine

Resemblyzer

And the many Python libraries used.
