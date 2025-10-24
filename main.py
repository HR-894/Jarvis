import argparse
import json
import os
import subprocess
import threading
import time
import shutil

# --- Configuration (moved up so self-test can use paths) ---
CONFIG_PATH = os.path.join(os.path.expanduser('~/jarvis'), 'config.json')
JARVIS_DIR = os.path.expanduser('~/jarvis')

# Audio Recording settings
STT_SAMPLE_RATE = 16000 # Whisper ke liye 16kHz
VAD_SAMPLE_RATE = 16000 # VAD ke liye 16kHz
VAD_FRAME_MS = 30
VAD_FRAME_SIZE = int(VAD_SAMPLE_RATE * VAD_FRAME_MS / 1000)

# Paths to our C++ tools
WHISPER_CPP_PATH = os.path.join(JARVIS_DIR, 'whisper.cpp', 'build', 'bin', 'main')
WHISPER_MODEL_PATH = os.path.join(JARVIS_DIR, 'whisper.cpp', 'models', 'ggml-tiny.en.bin')
LLAMA_CPP_PATH = os.path.join(JARVIS_DIR, 'llama.cpp', 'build', 'bin', 'llama-cli')
LLAMA_MODEL_PATH = os.path.join(JARVIS_DIR, 'llama.cpp', 'models', 'mistral-7b-openhermes.Q4_K_M.gguf')
PIPER_BINARY = os.path.join(JARVIS_DIR, 'piper', 'piper')

# Runtime tunables (can be overridden in config.json)
DEFAULT_WHISPER_THREADS = max(1, (os.cpu_count() or 1) // 2)
DEFAULT_LLAMA_THREADS = max(1, (os.cpu_count() or 1) - 1)
DEFAULT_LLAMA_N = 64
DEFAULT_LLAMA_TIMEOUT = 30


# --- Quick self-test (runs before importing heavy audio/ML libs) ---
def quick_self_test():
    checks = []
    def ok(msg):
        checks.append((True, msg))
    def fail(msg):
        checks.append((False, msg))

    # Config
    if os.path.exists(CONFIG_PATH):
        ok(f"Config file found: {CONFIG_PATH}")
    else:
        fail(f"Config file MISSING: {CONFIG_PATH}")

    # Binaries and models
    for name, path in [
        ("Whisper binary", WHISPER_CPP_PATH),
        ("Whisper model", WHISPER_MODEL_PATH),
        ("Llama binary", LLAMA_CPP_PATH),
        ("Llama model", LLAMA_MODEL_PATH),
        ("Piper binary", os.path.join(os.path.expanduser('~/jarvis'), 'piper', 'piper')),
    ]:
        if os.path.exists(path):
            ok(f"{name} found: {path}")
        else:
            fail(f"{name} NOT found: {path}")

    # ffmpeg
    ffmpeg_path = shutil.which('ffmpeg')
    if ffmpeg_path:
        ok(f"ffmpeg found: {ffmpeg_path}")
    else:
        fail("ffmpeg NOT found in PATH")

    # Report
    print("--- Self-test report ---")
    for status, msg in checks:
        print(("OK ", "FAIL")[not status], " - ", msg)
    missing = [m for s, m in checks if not s]
    if missing:
        print("\nActionable fixes:")
        for m in missing:
            if 'Whisper binary' in m:
                print(" - Build whisper.cpp: cd ~/jarvis/whisper.cpp && make or follow project docs")
            if 'Llama binary' in m:
                print(" - Build llama.cpp: cd ~/jarvis/llama.cpp && cmake -S . -B build && cmake --build build -j$(nproc)")
            if 'Piper binary' in m:
                print(" - Ensure piper binary exists in ~/jarvis/piper/")
            if 'ffmpeg' in m:
                print(" - Install ffmpeg (e.g., apt install ffmpeg)")
            if 'Config file' in m:
                print(" - Create a valid config.json in ~/jarvis with PICOVOICE and model paths")
    else:
        print("All critical files present. You may still need Python deps (numpy, sounddevice, etc.).")

# If user requested a quick self-test, run it and exit before importing heavy modules
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('--self-test', action='store_true', help='Run quick environment checks and exit')
args, _ = parser.parse_known_args()
if args.self_test:
    quick_self_test()
    raise SystemExit(0)

# Defer heavy imports until after self-test
import numpy as np
import sounddevice as sd
import pvporcupine
import webrtcvad
try:
    from resemblyzer import VoiceEncoder
except Exception:
    VoiceEncoder = None
    print("Notice: 'resemblyzer' not installed. Speaker verification will be disabled.")
import soundfile as sf # Hum Scipy ki jagah yeh use karenge

# Hamare apne banaye hue scripts
from tts import speak
from intent_parser import parse_intent
from safe_runner import SafeRunner
from jarvis_name_manager import handle_rename_command

# --- Configuration ---
CONFIG_PATH = os.path.join(os.path.expanduser('~/jarvis'), 'config.json')
JARVIS_DIR = os.path.expanduser('~/jarvis')

# Audio Recording settings
STT_SAMPLE_RATE = 16000 # Whisper ke liye 16kHz
VAD_SAMPLE_RATE = 16000 # VAD ke liye 16kHz
VAD_FRAME_MS = 30
VAD_FRAME_SIZE = int(VAD_SAMPLE_RATE * VAD_FRAME_MS / 1000)

# Paths to our C++ tools
WHISPER_CPP_PATH = os.path.join(JARVIS_DIR, 'whisper.cpp', 'build', 'bin', 'main')
WHISPER_MODEL_PATH = os.path.join(JARVIS_DIR, 'whisper.cpp', 'models', 'ggml-tiny.en.bin')
# --- YEH HAI CORRECT LLAMA PATH ---
LLAMA_CPP_PATH = os.path.join(JARVIS_DIR, 'llama.cpp', 'build', 'bin', 'llama-cli')
LLAMA_MODEL_PATH = os.path.join(JARVIS_DIR, 'llama.cpp', 'models', 'mistral-7b-openhermes.Q4_K_M.gguf')
PIPER_BINARY = os.path.join(JARVIS_DIR, 'piper', 'piper')

# --- Global Objects ---
config = {}
porcupine = None
vad = webrtcvad.Vad()
vad.set_mode(3) # Aggressive
speaker_encoder = None
saved_speaker_embedding = None
safe_runner = SafeRunner()

# --- Helper Functions ---

def load_all():
    """Saari settings aur models ko memory mein load karta hai."""
    global config, porcupine, saved_speaker_embedding
    print("Jarvis ko start kar raha hoon... components load ho rahe hain...")
    try:
        with open(CONFIG_PATH, 'r') as f:
            config = json.load(f)
        print(f"Config loaded. Welcome, {config['USER_NAME']}.")
    except Exception as e:
        print(f"FATAL: config.json load nahi kar paaya! {e}")
        return False
    # Populate runtime tunables with defaults if not set
    config.setdefault('WHISPER_THREADS', DEFAULT_WHISPER_THREADS)
    config.setdefault('LLAMA_THREADS', DEFAULT_LLAMA_THREADS)
    config.setdefault('LLAMA_N_PREDICT', DEFAULT_LLAMA_N)
    config.setdefault('LLAMA_TIMEOUT', DEFAULT_LLAMA_TIMEOUT)
    try:
        key_path = os.path.expanduser(config['PICOVOICE_KEYWORD_PATH'])
        # Allow tuning Porcupine sensitivity via config (0.0-1.0). Higher = more sensitive.
        sensitivity = float(config.get('PICOVOICE_SENSITIVITY', 0.75))
        print(f"Porcupine sensitivity set to {sensitivity}")
        porcupine = pvporcupine.create(
            access_key=config['PICOVOICE_ACCESS_KEY'],
            keyword_paths=[key_path],
            sensitivities=[sensitivity]
        )
        print("Hotword engine loaded (Porcupine).")
    except Exception as e:
        print(f"FATAL: Porcupine load nahi kar paaya! {e}")
        return False
    try:
        embed_path = os.path.expanduser(config['SPEAKER_EMBED_PATH'])
        saved_speaker_embedding = np.load(embed_path)
        print("Speaker voiceprint loaded.")
    except Exception as e:
        print(f"WARNING: Speaker voiceprint nahi mila. 'python3 speaker_enroll.py' chala lein.")
        pass
    print("--- Jarvis is Ready (Makkhan Mode) ---")
    # Speak may fail if piper/aplay not configured; wrap it so load_all still returns True
    try:
        speak(f"Jarvis is ready, {config['USER_NAME']}.", lang='en_m')
    except Exception as e:
        print(f"Non-fatal: TTS failed during startup: {e}")
    return True

def listen_for_hotword():
    """Mic stream kholta hai aur sirf hotword sunta hai."""
    print(f"\nHotword sun raha hoon... ('{config['JARVIS_NAME']}')")
    hotword_event = threading.Event()

    def audio_callback(indata, frames, time, status):
        if status:
            print(status)
        try:
            # Log a tiny bit of audio level info for debugging
            try:
                peak = float(np.max(np.abs(indata))) * 32767.0
                rms = float(np.sqrt(np.mean(indata.astype(np.float64) ** 2)))
                rms_db = 20.0 * np.log10(rms + 1e-9)
                print(f"[HOTWORD AUDIO] peak={peak:.0f} rms_db={rms_db:.1f} dB")
            except Exception:
                pass
            audio_frame = (indata * 32767).astype(np.int16).flatten()
            keyword_index = porcupine.process(audio_frame)
            if keyword_index >= 0:
                print(f"\n[Hotword Detected!] -> {config['JARVIS_NAME']}")
                hotword_event.set()
                raise sd.CallbackStop # Ab yeh 'except' mein nahi phansega
        except sd.CallbackStop:
            raise # CallbackStop ko aage jaane do
        except Exception as e: 
            print(f"Hotword processing error: {e}")

    try:
        with sd.InputStream(
            channels=1,
            samplerate=porcupine.sample_rate,
            blocksize=porcupine.frame_length,
            dtype='float32',
            callback=audio_callback
        ):
            hotword_event.wait(timeout=30.0)
    except sd.CallbackStop:
        return True # Hotword mila
    except Exception as e:
        print(f"Hotword stream error: {e}")
        return False

    if not hotword_event.is_set():
        print("Hotword timeout... (30s)")
        return False
    return True

def verify_speaker(duration=3):
    """3 second ke liye record karke speaker ko verify karta hai."""
    if saved_speaker_embedding is None:
        print("Verification skipped (no voiceprint).")
        return True
    print(f"Verifying {config['USER_NAME']}... 3 sec tak bolein...")
    speak("Please verify.", lang='en_m')
    try:
        audio = sd.rec(int(duration * STT_SAMPLE_RATE), samplerate=STT_SAMPLE_RATE, channels=1, dtype='float32')
        sd.wait()
        current_audio = audio.flatten()
        current_embedding = speaker_encoder.embed_utterance(current_audio)
        similarity = np.dot(saved_speaker_embedding, current_embedding) / (np.linalg.norm(saved_speaker_embedding) * np.linalg.norm(current_embedding))
        print(f"Similarity: {similarity:.2f}")
        if similarity > 0.75:
            print("STATUS: VERIFIED.")
            return True
        else:
            print("STATUS: FAILED.")
            return False
    except Exception as e:
        print(f"Speaker verification error: {e}")
        return False

def record_command(timeout=7):
    """User ka command record karta hai jab tak woh chup nahi ho jaate."""
    print("Command sun raha hoon (7s timeout)...")
    speak("Yes sir?", lang='en_m')

    audio_frames = []
    is_speech_started = False
    silence_frames = 0
    max_silence_frames = 25

    def vad_callback(indata, frames, time, status):
        nonlocal is_speech_started, silence_frames
        if status:
            print(status)
        try:
            # Debug: show VAD decisions and level
            audio_data_float = indata.flatten()
            try:
                peak = float(np.max(np.abs(audio_data_float))) * 32767.0
                rms = float(np.sqrt(np.mean(audio_data_float.astype(np.float64) ** 2)))
                rms_db = 20.0 * np.log10(rms + 1e-9)
                print(f"[VAD AUDIO] peak={peak:.0f} rms_db={rms_db:.1f} dB")
            except Exception:
                pass
            audio_data_int16 = (audio_data_float * 32767).astype(np.int16)
            audio_bytes = audio_data_int16.tobytes()
            is_speech = vad.is_speech(audio_bytes[:VAD_FRAME_SIZE*2], VAD_SAMPLE_RATE)
            print(f"[VAD] is_speech={is_speech} is_speech_started={is_speech_started} silence_frames={silence_frames}")

            if is_speech_started:
                audio_frames.append(audio_data_float)
                if not is_speech:
                    silence_frames += 1
                    if silence_frames > max_silence_frames:
                        print("[Silence Detected] -> Recording stopped.")
                        raise sd.CallbackStop # Ab yeh 'except' mein nahi phansega
                else:
                    silence_frames = 0
            elif is_speech:
                print("[Speech Detected] -> Recording started...")
                is_speech_started = True
                audio_frames.append(audio_data_float)
        except sd.CallbackStop:
            raise # CallbackStop ko aage jaane do
        except Exception as e:
            print(f"VAD record error: {e}")

    try:
        with sd.InputStream(
            samplerate=VAD_SAMPLE_RATE,
            blocksize=VAD_FRAME_SIZE,
            channels=1,
            dtype='float32',
            callback=vad_callback
        ):
            sd.sleep(timeout * 1000)

        if not is_speech_started:
            print("Timeout: Kuch bola hi nahi.")
            return None
    except sd.CallbackStop:
        pass # Recording safalta se poori hui
    except Exception as e:
        print(f"Recording stream error: {e}")
        return None

    full_audio = np.concatenate(audio_frames)
    return full_audio

def run_whisper_stt(audio_data):
    """Audio data ko file mein save, amplify, aur fir whisper.cpp se STT chalata hai."""
    print("Transcribing... (Whisper.cpp chal raha hai)")
    try:
        # 1. Audio ko ORIGINAL file mein save karo
        temp_audio_file = os.path.join(JARVIS_DIR, "temp_stt_input.wav")
        sf.write(temp_audio_file, audio_data, STT_SAMPLE_RATE, subtype='PCM_16')

        # --- NAYA STEP: Audio ko FFMPEG se amplify karo ---
        # Hum check karenge ki file silent toh nahi hai
        try:
            # Ek chhota check chalao
            chk_command = ["ffmpeg", "-i", temp_audio_file, "-af", "volumedetect", "-f", "null", "-"]
            # Correctly capture combined stdout and stderr
            result = subprocess.run(chk_command, text=True, capture_output=True)

            # Check both stdout and stderr for the volume info
            output = result.stdout + result.stderr
            if "mean_volume: -inf" in output:
                print("Audio poori tarah silent hai. Skipping.")
                return None
        except Exception as e:
            print(f"FFmpeg check error: {e}") # Agar ffmpeg na ho

        print("Audio ko amplify kar raha hoon (taaki Whisper sun sake)...")
        amplified_audio_file = os.path.join(JARVIS_DIR, "temp_stt_amplified.wav")

        # Audio ko normalize (ek standard loud level par) karo
        ffmpeg_command = [
    "ffmpeg",
    "-i", temp_audio_file,
    "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", # Volume badhao
    "-ar", "16000",                        # 16kHz sample rate par force karo
    "-ac", "1",                            # 1 channel (Mono) par force karo
    "-c:a", "pcm_s16le",                   # 16-bit PCM format par force karo
    "-y",                                  # Puraani file overwrite karo
    "-hide_banner",
    "-loglevel", "error",
    amplified_audio_file
]
        subprocess.run(ffmpeg_command, check=True)
        print("Amplification complete.")
        # --------------------------------------------------

        # 2. whisper.cpp command ko AMPLIFIED file par chalao
        if not os.path.exists(WHISPER_CPP_PATH):
            print(f"ERROR: Whisper binary not found at {WHISPER_CPP_PATH}")
            return None
        whisper_threads = str(int(config.get('WHISPER_THREADS', DEFAULT_WHISPER_THREADS)))
        stt_command = [
            WHISPER_CPP_PATH,
            "-m", WHISPER_MODEL_PATH,
            "-f", amplified_audio_file, # Hum amplified file use kar rahe hain
            "-t", whisper_threads,
            "-l", "auto",
            "-otxt"
        ]
        try:
            proc = subprocess.run(stt_command, check=True, capture_output=True, text=True, timeout=120)
            if proc.stdout:
                print(f"[whisper] stdout (truncated): {proc.stdout.strip()[:1000]}")
            if proc.stderr:
                print(f"[whisper] stderr (truncated): {proc.stderr.strip()[:1000]}")
        except subprocess.CalledProcessError as e:
            print(f"Whisper process failed: returncode={e.returncode} stdout={e.stdout} stderr={e.stderr}")
            return None
        except Exception as e:
            print(f"Whisper subprocess error: {e}")
            return None

        # 3. Output file ko padho
        output_txt_file = amplified_audio_file + ".txt"
        if not os.path.exists(output_txt_file):
            print(f"Whisper output file not found: {output_txt_file}")
            text_result = ""
        else:
            with open(output_txt_file, 'r') as f:
                text_result = f.read().strip()

        # 4. Temp files delete karo
        os.remove(temp_audio_file)
        os.remove(amplified_audio_file)
        if os.path.exists(output_txt_file):
            os.remove(output_txt_file)

        if not text_result:
            print("Whisper ne transcribe kiya, par koi text nahi mila (shayad sirf silence tha).")
            return None

        print(f"STT Result: '{text_result}'")
        return text_result

    except Exception as e:
        print(f"Whisper STT error: {e}")
        return None

def run_llama_llm(prompt_text):
    """LLM ko prompt bhejta hai aur response laata hai."""
    if config.get("MODE", "balanced") == "low-power":
        print("LLM disabled in low-power mode.")
        return "Maaf kijiye, main abhi low-power mode mein hoon."
    print(f"Thinking... (LLM chal raha hai: {prompt_text})")
    speak("Soch raha hoon...", lang='hi')
    full_prompt = f"User: {prompt_text}\nJarvis:"
    try:
        if not os.path.exists(LLAMA_CPP_PATH):
            print(f"ERROR: Llama binary not found at {LLAMA_CPP_PATH}")
            return "Maaf kijiye, LLM binary missing."
        llm_command = [
            LLAMA_CPP_PATH,
            "-m", LLAMA_MODEL_PATH,
            "-p", full_prompt,
            "-n", "128",
            "-t", "3",
            "--temp", "0.7",
            "-e"
        ]
        try:
            llama_threads = str(int(config.get('LLAMA_THREADS', DEFAULT_LLAMA_THREADS)))
            n_pred = str(int(config.get('LLAMA_N_PREDICT', DEFAULT_LLAMA_N)))
            timeout_val = int(config.get('LLAMA_TIMEOUT', DEFAULT_LLAMA_TIMEOUT))
            # Inject threads and n_predict into command (respect overrides)
            # Replace -t and -n entries
            for i, v in enumerate(llm_command):
                if v == '-t' and i + 1 < len(llm_command):
                    llm_command[i+1] = llama_threads
                if v in ('-n', '-N', '--n-predict') and i + 1 < len(llm_command):
                    llm_command[i+1] = n_pred

            result = subprocess.run(llm_command, check=True, capture_output=True, text=True, timeout=timeout_val)
        except subprocess.CalledProcessError as e:
            print(f"LLM process failed: returncode={e.returncode} stdout={e.stdout[:1000]} stderr={e.stderr[:1000]}")
            return "Maaf kijiye, LLM process fail hua."
        except Exception as e:
            print(f"LLM subprocess error: {e}")
            return "Maaf kijiye, LLM timeout ya error hua."

        raw_output = result.stdout
        response = raw_output.split(full_prompt, 1)[-1].strip()
        response = response.split("\n")[0].strip()
        print(f"LLM Result: '{response}'")
        return response
    except Exception as e:
        print(f"LLM error: {e}")
        return "Maaf kijiye, sochte waqt ek error aa gaya."

# --- Main Loop (Asli Jarvis Yahaan Hai) ---
def main_loop():
    if not load_all():
        return
    while True:
        if not listen_for_hotword():
            continue
        #if not verify_speaker():
        #    speak("Access Denied.", lang='en_m')
        #    continue
        audio_command = record_command()
        if audio_command is None:
            continue
        text_command = run_whisper_stt(audio_command)
        if not text_command:
            speak("Main sun nahi paaya, Sir.", lang='hi')
            continue

        response = None
        lang_to_speak = 'hi' 
        response = handle_rename_command(text_command)
        if response:
            lang_to_speak = 'hi'
        if not response:
            intent = parse_intent(text_command)
            if intent:
                speak("Executing.", lang='en_m')
                status, msg = safe_runner.execute(intent, is_authenticated=True)
                response = msg
                lang_to_speak = 'en_m'
            else:
                if config.get("MODE", "balanced") != "low-power":
                     response = run_llama_llm(text_command)
                     lang_to_speak = 'en_m'
                else:
                    response = "Yeh command main low power mode mein nahi chala sakta."
                    lang_to_speak = 'hi'
        if response:
            speak(response, lang=lang_to_speak)
        else:
            speak("Uske liye main trained nahi hoon.", lang='hi')

if __name__ == "__main__":
    try:
        main_loop()
    except KeyboardInterrupt:
        print("\nExiting Jarvis... Goodbye!")
        if porcupine:
            porcupine.delete()
    except Exception as e:
        print(f"\n--- FATAL MAIN LOOP ERROR ---")
        print(e)
        if porcupine:
            porcupine.delete()
