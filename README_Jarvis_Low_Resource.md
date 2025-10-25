# Local Jarvis — Low-Resource (Ryzen3, 8GB) — "Makkhan Mode"

Ye guide WSL2 Ubuntu 22.04 ke liye banaya gaya hai. Saari instructions simple Hinglish me hain. Pehle "Quick one-line" commands, phir verbose setup, fir files and tests.

## Quick one-line (fast) install (copy-paste)
```bash
# ek line shortcut — caution: runs lots of installs, read README agar unsure ho
bash -c "$(curl -sSL https://raw.githubusercontent.com/your-repo/placeholder/main/setup_low.sh)" 
# NOTE: above URL placeholder - agar aap local copy use kar rahe ho, run ./setup_low.sh
```

## 1) Prereqs checks (WSL2 + Ubuntu 22.04)
WSL2 pe Ubuntu 22.04 install karne ke liye Windows PowerShell (Admin) me:
```powershell
# Windows PowerShell (Admin) - ek baar run karo
wsl --install -d Ubuntu-22.04
# phir Windows restart karo agar required ho.
# WSL distro start karne ke baad, terminal me:
sudo apt update && sudo apt upgrade -y
# Ensure Python 3.10+:
sudo apt install -y build-essential git curl wget ca-certificates \
    python3.10 python3.10-venv python3.10-dev python3-pip \
    pulseaudio ffmpeg sox tmux unzip p7zip-full
# Optional for audio device forwarding: install pulseaudio in WSL and set X11/Sound appropriately.
```

Notes:
- WSL2 default audio handling thoda tricky hai; Windows 11 recent builds support WSLg audio. Agar WSL me audio problem aaye toh aap `pulseaudio` aur `pavucontrol` use kar sakte ho, ya Windows side pe "microphone" & "speakers" settings check karo.
- Swap tip later section me diya hai.

## 2) Models & download commands (exact)
A. Whisper using whisper.cpp (recommended ggml for low RAM)
- Default: whisper-tiny (fast, ≈45MB)
- Optional: whisper-small (better accuracy, ≈300MB)

Commands (WSL Ubuntu terminal):
```bash
# clone whisper.cpp
git clone https://github.com/ggerganov/whisper.cpp.git
cd whisper.cpp
make -j$(nproc)

# models directory
mkdir -p ~/jarvis_models/whisper
cd ~/jarvis_models/whisper

# download ggml tiny (default) ~45MB
wget -c https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-tiny.bin -O ggml-tiny.bin

# OPTIONAL: whisper-small (slower, ~300MB)
wget -c https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin -O ggml-small.bin
```
Usage (example):
```bash
# realtime demo (CLI)
~/whisper.cpp/main -m ~/jarvis_models/whisper/ggml-tiny.bin -t 1 -l hi
# -t threads, -l language
```

B. Faster-whisper alternative (Python) — optional (heavier CPU)
```bash
python3.10 -m pip install faster-whisper
# usage example in Python scripts (provided), but default hum whisper.cpp recommend karte hain kyunki woh light hota hai.
```

C. LLM: 7B quantized via gpt4all (optional)
- Reason: 7B quantized offline models balance accuracy & resource. llama.cpp + GGUF convert bhi possible but complicated; gpt4all provides permissive offline 7B quantized models ready-to-run.
- Example download (gpt4all-J v1.3 or similar) — yeh example wget aap test kar sakte ho; agar link change ho to official gpt4all releases page se download karo.

Commands:
```bash
mkdir -p ~/jarvis_models/llm
cd ~/jarvis_models/llm

# Example: gpt4all 7B (link may change) - check https://gpt4all.io/models.html for latest
wget -c https://gpt4all.io/models/ggml/gpt4all-lora-quantized.bin -O gpt4all-7b-q.bin

# Install llama.cpp (optional) aur run:
git clone https://github.com/ggerganov/llama.cpp.git
cd llama.cpp
make -j$(nproc)
# run:
./main -m ~/jarvis_models/llm/gpt4all-7b-q.bin -p "Hello"
```
If you cannot run 7B comfortably, use rule-based fallback (no LLM) — included in repo.

D. TTS: espeak-ng (always available) + optional Coqui TTS small model
```bash
# Install espeak-ng
sudo apt install -y espeak-ng

# Optional: Coqui TTS (better natural voices) - lightweight small model
python3.10 -m pip install TTS==0.13.1 torch==2.0.1 --extra-index-url https://download.pytorch.org/whl/cpu
# NOTE: CPU-only torch recommended for WSL
mkdir -p ~/jarvis_models/tts
cd ~/jarvis_models/tts
# Example small model download instructions via Coqui's model list; in script we'll show usage.
```

Estimated sizes:
- whisper-tiny: ~45 MB
- whisper-small: ~300 MB
- gpt4all 7B quantized: ~2.5-4 GB (optional)
- Coqui small TTS model: ~100-300 MB (optional)

## 3) Hotword
Option A (recommended optional): Porcupine (Picovoice) — light CPU, keyword models available (free developer license).
- Installation (optional):
```bash
python3.10 -m pip install pvporcupine
# Or use their native bindings if needed.
```
Minimal Python snippet (included) shows using Porcupine and falling back to STT-first if Porcupine not available.

Option B (fallback): STT-first wake detection — idle short recordings (0.5s) with whisper-tiny to spot phrase pattern (lower CPU by sampling rate and rare polling).

## 4) Interrupt-on-user (Python snippet)
- Uses sounddevice + webrtcvad
- TTS playback via subprocess (aplay) or direct sounddevice stream; we provide a minimal snippet `interrupt_handler.py` that starts TTS and listens — on voice detection it immediately stops playback and returns control.

Files below include implementation.

## 5) Speaker verification
- Uses `resemblyzer` (lightweight) for voice embeddings and cosine similarity.
- Enrollment: record a few seconds, store embedding.
- Verification: compute cosine similarity, compare to threshold (default 0.7 — tune on your data).

Python script `speaker_verify.py` provided.

## 6) Name/alias manager
- `config.json` holds name/alias and voice prefs.
- `jarvis_name_manager.py` updates config on-the-fly and signals running processes via a small UNIX socket or file change.

## 7) Command execution sandbox
- `safe_commands.yaml` whitelist example provided.
- `safe_runner.py` checks YAML whitelist; dangerous commands require voice auth and an explicit "confirm" after assistant repeats the full command.

## 8) jarvisctl
- `jarvisctl` bash script (WSL friendly) uses tmux to start/stop sessions, toggle modes: off, low-power (no LLM, whisper-tiny, espeak), balanced (LLM disabled by default but can enable).
- Also performs encrypted backup of models/config via `gpg` (recommended to setup keys).

## 9) Testing guide — 10 quick tests (with expected outputs)
Provided below in README and in tests section.

## 10) Performance tuning tips
Thread limits, OMP_NUM_THREADS, swappiness, CPU affinity, whisper beam size reduce, disable LLM in low-power, service nice + ionice. Provided in README.

## 11) Uninstall & restore
`uninstall_restore.sh` script provided to cleanup and optional restore from gpg backup.

--- 

Ab main saare code files de raha hoon (copy-paste ready). Har file ke comments Hinglish me hain.