import pvporcupine
import sounddevice as sd
import numpy as np
import json
import os

def load_config():
    with open('config.json', 'r') as f:
        return json.load(f)

config = load_config()
porcupine = None

try:
    key_path = os.path.expanduser(config['PICOVOICE_KEYWORD_PATH'])
    if not os.path.exists(key_path):
        print(f"Error: Keyword file nahi mila!")
        print(f"Path check karo: {key_path}")
        exit()

    porcupine = pvporcupine.create(
        access_key=config['PICOVOICE_ACCESS_KEY'],
        keyword_paths=[key_path]
    )

    print(f"Porcupine initialized. Frame length: {porcupine.frame_length}")

    def audio_callback(indata, frames, time, status):
        if status:
            print(status)

        # audio data ko int16 mein convert karo
        audio_frame = (indata * 32767).astype(np.int16).flatten()

        try:
            keyword_index = porcupine.process(audio_frame)
            if keyword_index >= 0:
                print(f"-----> Hotword detected! ({config['JARVIS_NAME']}) <-----")
                # Yahan hum speaker verification aur STT trigger karenge

        except Exception as e:
            print(f"Error processing audio: {e}")

    print(f"\nHotword listener started... Apne mic mein '{config['JARVIS_NAME']}' bolein...")
    with sd.InputStream(
        channels=1,
        samplerate=porcupine.sample_rate,
        blocksize=porcupine.frame_length,
        dtype='float32',
        callback=audio_callback
    ):
        sd.sleep(30000) # 30 sec tak suno

except pvporcupine.PorcupineError as e:
    print(f"\nError setting up Porcupine: {e}")
    print("Please check your AccessKey aur Keyword Path in config.json")
except Exception as e:
    print(f"\nEk anjaan error hua: {e}")
finally:
    if porcupine:
        porcupine.delete()
    print("\nListener stopped.")
