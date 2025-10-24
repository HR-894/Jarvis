import json
import re
import os

CONFIG_FILE = 'config.json'

# config.json ka poora path
CONFIG_PATH = os.path.join(os.path.expanduser('~/jarvis'), CONFIG_FILE)

def load_config():
    if not os.path.exists(CONFIG_PATH):
        print(f"Error: {CONFIG_PATH} nahi mila!")
        return {}
    with open(CONFIG_PATH, 'r') as f:
        return json.load(f)

def save_config(data):
    with open(CONFIG_PATH, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Config saved: {data}")

def handle_rename_command(stt_text):
    """
    STT (voice-to-text) ke text ko parse karke naam badalta hai.
    """
    config = load_config()
    if not config:
        return None

    new_name = None
    response = None
    stt_text = stt_text.lower() # Sab lowercase mein check karo

    # Pattern 1: Change Jarvis's name
    # "change your name to Friday" | "tumhara naam badal kar Friday kar do"
    match_jarvis = re.search(r'(change|badlo|set) (your|tumhara) name to (.*)', stt_text)
    if match_jarvis:
        new_name = match_jarvis.group(3).strip()
        config['JARVIS_NAME'] = new_name
        response = f"Theek hai, abse mera naam {new_name} hai."

    # Pattern 2: Change User's name
    # "change my name to Boss" | "mera naam badal kar Boss kar do"
    match_user = re.search(r'(change|badlo|set) (my|mera) name to (.*)', stt_text)
    if match_user:
        new_name = match_user.group(3).strip()
        config['USER_NAME'] = new_name
        response = f"Noted, abse main aapko {new_name} kahunga."

    if response:
        save_config(config)
        return response # Yeh response hum TTS se bulwayenge
    else:
        return None # Matlab yeh rename command nahi tha

# --- Test Karne Ke Liye ---
if __name__ == "__main__":
    print("--- Name Manager Test ---")

    test_text_1 = "jarvis change your name to friday"
    print(f"\nIN: {test_text_1}")
    print(f"OUT: {handle_rename_command(test_text_1)}")

    test_text_2 = "mera naam badal kar boss kar do"
    print(f"\nIN: {test_text_2}")
    print(f"OUT: {handle_rename_command(test_text_2)}")

    test_text_3 = "aaj mausam kaisa hai"
    print(f"\nIN: {test_text_3}")
    print(f"OUT: {handle_rename_command(test_text_3)}")

    print("\n--- Test Complete ---")
