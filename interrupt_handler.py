import sounddevice as sd
import webrtcvad
import numpy as np
import time
import threading
from tts import speak # Hum apne 'tts.py' script ko import kar rahe hain
import subprocess
# --- VAD Setup ---
vad = webrtcvad.Vad()
vad.set_mode(3) # Mode 3 sabse aggressive hai (turant speech pakadta hai)
SAMPLE_RATE = 16000 # VAD ke liye 16kHz zaroori hai
FRAME_DURATION_MS = 30  # 30ms VAD ke liye zaroori hai
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)

# --- Global Flags (Jo threads ke beech baat karengi) ---

# Yeh Event batata hai ki TTS bolna band kare
stop_tts_event = threading.Event()

# Yeh Event batata hai ki user ne interrupt kar diya hai
user_interrupted_event = threading.Event()

# --- Functions ---

def play_tts_interruptible(text_to_speak):
    """TTS ko ek alag thread mein play karta hai, taaki hum ise rok sakein."""

    print(f"TTS Thread: Bolna shuru kar raha hoon... '{text_to_speak}'")

    # NOTE: Humara 'tts.py' script (jo file banakar 'aplay' karta hai)
    # poora command ek baar mein chalata hai.
    # Asli interrupt ke liye, humein audio stream ko Python mein hi
    # play karna hota.

    # Abhi ke Makkhan Mode ke liye, hum simulate karenge:
    # Hum 'speak' function ko call karenge,
    # aur check karenge ki kya VAD ne humein roka.

    # Ek naya thread banao jo 'speak' function ko chalayega
    tts_thread = threading.Thread(target=speak, args=(text_to_speak,))
    tts_thread.start()

    # Main thread yahaan wait karega, ya toh tts khatam hone ka,
    # ya interrupt hone ka.
    while tts_thread.is_alive():
        if stop_tts_event.is_set():
            print("TTS Thread: Interrupt signal mila! TTS rokne ki koshish...")
            # Asliyat mein, humein yahaan 'aplay' process ko kill karna hoga.
            # Abhi ke liye, hum bas event set kar rahe hain.
            # Humara 'tts.py' script 'aplay' ko kill nahi kar sakta.
            # Yeh ek limitation hai.

            # Hum 'kill' command simulate karenge
            subprocess.run(["killall", "aplay"], capture_output=True, text=True)
            user_interrupted_event.set() # Main loop ko batao ki interrupt hua
            break
        time.sleep(0.1)

    print("TTS Thread: Playback poora hua.")

def vad_listener():
    """
    Hamesha mic sunta rehta hai aur speech detect hone par 'stop_tts_event' set karta hai.
    """
    print("VAD Thread: Mic sunna shuru...")

    def callback(indata, frames, time, status):
        if status:
            print(status, flush=True)
        try:
            # Data ko 16-bit PCM mein convert karo
            audio_data = (indata * 32767).astype(np.int16).tobytes()

            # VAD ko check karne ke liye correct frame size mein baanto
            for i in range(0, len(audio_data), FRAME_SIZE * 2): # 2 bytes per sample
                frame = audio_data[i:i + FRAME_SIZE * 2]
                if len(frame) == FRAME_SIZE * 2:
                    if vad.is_speech(frame, SAMPLE_RATE):
                        print("\n[VAD Detected Speech!] -> STOP TTS!")
                        stop_tts_event.set() # TTS ko rokne ka signal bhejo
                        return # Callback se nikal jao
        except Exception as e:
            print(f"VAD callback error: {e}")

    # Mic stream shuru karo
    stream = sd.InputStream(
        samplerate=SAMPLE_RATE,
        blocksize=FRAME_SIZE,
        channels=1,
        dtype='float32',
        callback=callback
    )
    with stream:
        # Yeh thread tab tak chalta rahega jab tak 'stop_tts_event' set nahi hota
        while not stop_tts_event.is_set():
            time.sleep(0.5)

    print("VAD Thread: Listener band ho gaya.")

# --- Test Karne Ke Liye ---
if __name__ == "__main__":
    print("--- Interrupt Handler Test ---")

    # Ek lamba sa text jo 5-10 second tak bolega
    long_text = "Sir, yeh ek lamba test hai. Main bolta rahunga taaki aap mujhe beech mein interrupt kar sakein. Kripya main jab bol raha hoon, tab kuch bolne ki koshish karein."

    # 1. VAD listener ko ek background thread mein shuru karo
    stop_tts_event.clear()
    user_interrupted_event.clear()

    listener_thread = threading.Thread(target=vad_listener, daemon=True)
    listener_thread.start()

    time.sleep(1) # Listener ko setup hone do

    # 2. TTS ko main thread mein play karo
    play_tts_interruptible(long_text)

    if user_interrupted_event.is_set():
        print("\nTest Result: SUCCESS! User ne successfully interrupt kiya.")
    else:
        print("\nTest Result: TTS poora ho gaya (koi interrupt nahi hua).")

    # Script ko poori tarah band karne ke liye VAD thread ko signal do
    stop_tts_event.set()
    print("Test finished.")
