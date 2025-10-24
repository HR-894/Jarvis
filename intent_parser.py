import re # Humne Regular Expressions ko import kiya

# Yeh file STT ke text (Hinglish) ko hamare whitelist commands se map karega

# Yahan hum define karte hain ki kis command ke liye kya keywords ho sakte hain
# Key: 'whitelist.yml' mein likha 'name' (jaise 'check_date')
# Value: Keywords ki list
INTENT_MAP = {
    "check_date": [
        "date", "tareekh", "tarik", "dinank", "din kya hai", "aaj kya din hai"
    ],
    "check_ram": [
        "ram", "memory", "system memory", "kitni ram"
    ],
    "check_disk": [
        "disk", "storage", "hard drive", "kitni jagah hai"
    ],
    "update_system": [
        "update", "system update", "update kardo"
    ],
    "reboot_system": [
        "reboot", "restart", "band karke chalu"
    ]
}

def parse_intent(text):
    """
    User ke bolay gaye text ko parse karke intent (command name) nikalta hai.
    """
    text_lower = text.lower() # Sab kuch lowercase mein check karenge

    for intent_name, keywords in INTENT_MAP.items():
        for keyword in keywords:

            # --- YEH HAI NAYA LOGIC ---
            # Hum check kar rahe hain ki keyword ek poora shabd hai ya nahi
            # \b ka matlab hai 'word boundary' (space, comma, ya line ka end)
            # re.escape() keyword ko safe banata hai (agar usme special char ho)
            if re.search(r"\b" + re.escape(keyword) + r"\b", text_lower):
            # ---------------------------

                # Jaise hi pehla match milta hai, hum command ka naam return kar denge
                print(f"[Intent Parser] Match mila: '{keyword}' -> {intent_name}")
                return intent_name

    # Agar koi bhi keyword match nahi hua
    print("[Intent Parser] Koi bhi command match nahi hua.")
    return None

# --- Test Karne Ke Liye ---
if __name__ == "__main__":
    print("--- Intent Parser Test ---")

    test1 = "Jarvis aaj ki tareekh kya hai"
    print(f"\nText: '{test1}' -> Intent: {parse_intent(test1)}")

    test2 = "system memory check karo"
    print(f"\nText: '{test2}' -> Intent: {parse_intent(test2)}")

    test3 = "please update kardo system ko"
    print(f"\nText: '{test3}' -> Intent: {parse_intent(test3)}")

    test4 = "mausam kaisa hai" # Yeh hamare map mein nahi hai
    print(f"\nText: '{test4}' -> Intent: {parse_intent(test4)}")

    print("\n--- Test Complete ---")
