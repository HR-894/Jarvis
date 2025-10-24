from resemblyzer import VoiceEncoder
import sounddevice as sd
import numpy as np
import time
import json
import os

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

config = load_config()
encoder = VoiceEncoder()
SAMPLE_RATE = 16000 # Resemblyzer ke liye 16kHz zaroori hai

# File ka poora path config se lo
embed_path = os.path.expanduser(config['SPEAKER_EMBED_PATH'])

try:
    print(f"\nReady {config['USER_NAME']}. Kripya 5 second tak kuch bolein.")
    print("Example: 'Hello Jarvis, mera naam [aapka naam] hai aur main system ko authorize kar raha hoon.'")
    print("\n3...")
    time.sleep(1)
    print("2...")
    time.sleep(1)
    print("1...")
    time.sleep(1)
    print("Recording shuru...")

    # 5 second ki recording
    duration = 5
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait() # Recording complete hone ka wait karein

    print("Recording poori hui. Voiceprint process kar raha hoon...")

    # --- YEH HAI CORRECT CODE ---
    # Voiceprint generate karein
    audio_data = audio.flatten()
    embedding = encoder.embed_utterance(audio_data)
    # ---------------------------

    # Save karein
    np.save(embed_path, embedding)
    print(f"\nSuccess! Voiceprint saved to {embed_path}")

except Exception as e:
    print(f"Ek error hua: {e}")
