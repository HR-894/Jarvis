#!/usr/bin/env python3
# whisper_wrapper.py
# Hinglish: safe wrapper for whisper.cpp (whisper-cli). Copy-paste this file to ~/jarvis/
# Use karein to call whisper-cli reliably, capture stdout/stderr, fallback and detect blank audio.

import subprocess
import shlex
import os
import sys

WHISPER_CLI = os.path.expanduser("~/jarvis/whisper.cpp/build/bin/whisper-cli")
MODEL_MULTI = os.path.expanduser("~/jarvis/whisper.cpp/models/ggml-tiny.bin")
MODEL_EN = os.path.expanduser("~/jarvis/whisper.cpp/models/ggml-tiny.en.bin")

def run_whisper(model_path, wav_path, threads=1, lang="auto", extra_flags=None):
    extra_flags = extra_flags or []
    cmd = [WHISPER_CLI, "-m", model_path, "-f", wav_path, "-t", str(threads), "-l", lang] + extra_flags
    print(f"[whisper_wrapper] Running: {' '.join(shlex.quote(x) for x in cmd)}")
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    print(f"[whisper_wrapper] returncode={p.returncode}")
    if p.stdout:
        print("[whisper_wrapper] STDOUT (head):")
        print(p.stdout.strip()[:2000])
    if p.stderr:
        print("[whisper_wrapper] STDERR (head):")
        print(p.stderr.strip()[:4000])
    return p.returncode, p.stdout, p.stderr

def detect_blank(stdout_text):
    if stdout_text is None:
        return True
    s = stdout_text.strip().lower()
    if not s:
        return True
    if "[blank_audio]" in s or "blank_audio" in s or "no speech" in s:
        return True
    return False

def transcribe_safe(wav_path):
    # Try multilingual model first if present
    if os.path.exists(MODEL_MULTI):
        rc, out, err = run_whisper(MODEL_MULTI, wav_path, threads=1, lang="auto", extra_flags=["-otxt"])
        if rc == 0 and not detect_blank(out):
            return out
    # Then try english-only model
    if os.path.exists(MODEL_EN):
        rc, out, err = run_whisper(MODEL_EN, wav_path, threads=1, lang="en", extra_flags=["-otxt"])
        if rc == 0 and not detect_blank(out):
            return out
    # Final attempt with default model (show diagnostics)
    model = MODEL_MULTI if os.path.exists(MODEL_MULTI) else MODEL_EN
    rc, out, err = run_whisper(model, wav_path, threads=1, lang="auto")
    if rc != 0:
        print("[whisper_wrapper] WARNING: whisper-cli returned non-zero. See STDERR above.")
    if detect_blank(out):
        print("[whisper_wrapper] Detected blank audio / no transcription.")
        print("[whisper_wrapper] Suggestions:")
        print("  - Ensure the WAV has clear speech (play it with aplay).")
        print("  - Length >= 0.5s (prefer >1s).")
        print("  - If you speak Hindi/Hinglish, use ggml-tiny.bin (multilingual).")
    return out

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: whisper_wrapper.py <wav-path>")
        sys.exit(1)
    print(transcribe_safe(sys.argv[1]))
