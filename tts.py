import subprocess
import os

# --- Paths ---
JARVIS_DIR = os.path.expanduser('~/jarvis')
PIPER_BINARY = os.path.join(JARVIS_DIR, 'piper', 'piper')

# Teeno models ke path
HINDI_MODEL_PATH = os.path.join(JARVIS_DIR, 'piper', 'hi_IN-rohan-medium.onnx')
EN_MALE_MODEL_PATH = os.path.join(JARVIS_DIR, 'piper', 'en_GB-alan-medium.onnx') # Male
EN_FEMALE_MODEL_PATH = os.path.join(JARVIS_DIR, 'piper', 'en_GB-alba-medium.onnx') # Female

TEMP_AUDIO_FILE = os.path.join(JARVIS_DIR, 'temp_tts_output.raw')

def speak(text_to_speak, lang='en_m'):
    """
    Piper TTS ka istemaal karke text ko awaaz mein badalta hai.
    lang='hi' (Hindi)
    lang='en_m' (English Male - Default)
    lang='en_f' (English Female)
    """

    model_path = ""
    if lang == 'hi':
        model_path = HINDI_MODEL_PATH
        if not os.path.exists(model_path):
            print("Error: Hindi model nahi mila!")
            return
    elif lang == 'en_f':
        model_path = EN_FEMALE_MODEL_PATH
        if not os.path.exists(model_path):
            print("Error: English (Female) model nahi mila!")
            return
    else:
        # Default English Male hai
        model_path = EN_MALE_MODEL_PATH
        if not os.path.exists(model_path):
            print("Error: English (Male) model nahi mila!")
            return

    if not os.path.exists(PIPER_BINARY):
        print("Error: Piper binary nahi mila!")
        return

    print(f"Jarvis ({lang}) bol raha hai: {text_to_speak}")

    # Stream Piper output directly to aplay to reduce latency and disk IO
    try:
        # Start piper process that writes raw PCM to stdout
        piper_proc = subprocess.Popen([
            PIPER_BINARY,
            '--model', model_path,
            '--output_raw'
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        # Start aplay to play raw PCM from stdin
        aplay_proc = subprocess.Popen([
            'aplay', '-r', '22050', '-f', 'S16_LE', '-t', 'raw', '-'
        ], stdin=piper_proc.stdout, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Send the text to piper stdin and close to signal EOF
        piper_proc.stdin.write(text_to_speak + '\n')
        piper_proc.stdin.close()

        # Wait for playback to finish
        aplay_proc.wait()
        piper_proc.wait()
    except Exception as e:
        print(f"TTS streaming error: {e}")

# --- Test Karne Ke Liye ---
if __name__ == "__main__":
    print("--- Multilingual TTS Test ---")

    # English Male (Default) test
    speak("Hello Sir. This is the default British male voice.", lang='en_m')

    # English Female test
    speak("This is the British female voice, for your assistance.", lang='en_f')

    # Hindi test
    speak("नमस्ते, मैं जार्विस हूँ। यह हिंदी आवाज़ है।", lang='hi')
