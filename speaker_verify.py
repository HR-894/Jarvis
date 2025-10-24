from resemblyzer import VoiceEncoder
import sounddevice as sd
import numpy as np
import json
import os

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

config = load_config()
encoder = VoiceEncoder()
SAMPLE_RATE = 16000
VERIFICATION_THRESHOLD = 0.80 # Humara 'pass mark'

# Saved voiceprint load karein
embed_path = os.path.expanduser(config['SPEAKER_EMBED_PATH'])
try:
    saved_embedding = np.load(embed_path)
    print("Saved voiceprint loaded.")
except FileNotFoundError:
    print(f"Error: Voiceprint file nahi mila: {embed_path}")
    print("Pehle 'python3 speaker_enroll.py' chalakar voice register karein.")
    exit()

def cosine_similarity(embed1, embed2):
    return np.dot(embed1, embed2) / (np.linalg.norm(embed1) * np.linalg.norm(embed2))

try:
    print("\nVerification: Kripya 3 second tak kuch bolein (kuch bhi)...")
    print("Recording...")

    duration = 3
    audio = sd.rec(int(duration * SAMPLE_RATE), samplerate=SAMPLE_RATE, channels=1, dtype='float32')
    sd.wait()

    print("Got it. Verifying...")

    # --- YEH HAI CORRECT CODE ---
    # Naya embedding banayein
    current_audio = audio.flatten()
    current_embedding = encoder.embed_utterance(current_audio)
    # ---------------------------

    # Compare karein
    similarity = cosine_similarity(saved_embedding, current_embedding)

    print(f"Similarity Score: {similarity:.2f}")

    if similarity > VERIFICATION_THRESHOLD:
        print(f"STATUS: VERIFIED. Welcome, {config['USER_NAME']}.")
    else:
        print("STATUS: FAILED. Aap authorized nahi hain.")

except Exception as e:
    print(f"Ek error hua: {e}")
