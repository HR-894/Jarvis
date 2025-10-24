import yaml
import subprocess
import os

WHITELIST_FILE = os.path.join(os.path.expanduser('~/jarvis'), 'whitelist.yml')

def load_whitelist():
    with open(WHITELIST_FILE, 'r') as f:
        return yaml.safe_load(f)

class SafeRunner:
    def __init__(self):
        self.commands = {}
        try:
            whitelist = load_whitelist()
            for cmd in whitelist.get('safe_commands', []):
                self.commands[cmd['name']] = cmd
            for cmd in whitelist.get('danger_commands', []):
                self.commands[cmd['name']] = cmd
        except FileNotFoundError:
            print(f"Error: {WHITELIST_FILE} nahi mila!")
        except Exception as e:
            print(f"Whitelist load karne mein error: {e}")

    def get_command_details(self, command_name):
        return self.commands.get(command_name)

    def execute(self, command_name, is_authenticated=False):
        """
        Command ko execute karta hai.
        Returns (status, message_or_output)
        """
        cmd = self.get_command_details(command_name)

        if not cmd:
            return ("error", "Command not found in whitelist.")

        # Step 1: Check Auth for danger commands
        if cmd.get('requires_auth', False) and not is_authenticated:
            return ("auth_required", "Yeh command highly sensitive hai. Pehle authentication zaroori hai.")

        # Step 2: Check for confirmation (Yeh hum main script mein handle karenge)
        if cmd.get('confirm_prompt'):
            return ("confirm_required", cmd['confirm_prompt'])

        # Step 3: Execute the command
        full_command = [cmd['script']] + cmd.get('args', [])

        try:
            print(f"Running: {' '.join(full_command)}")

            # IMPORTANT: shell=False hamesha rakhein (Security ke liye)
            result = subprocess.run(
                full_command,
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
                shell=False 
            )

            output = result.stdout.strip()
            message = cmd.get('message', "Command safaltapoorvak chala:")

            # Output ko ek line mein clean karo
            clean_output = " ".join(output.splitlines())
            return ("success", f"{message} {clean_output}")

        except subprocess.CalledProcessError as e:
            return ("error", f"Command fail ho gaya: {e.stderr}")
        except Exception as e:
            return ("error", f"Ek error hua: {e}")

# --- Test Karne Ke Liye ---
if __name__ == "__main__":
    print("--- Safe Runner Test ---")
    runner = SafeRunner()

    print("\n--- Test 1: Safe Command (Date) ---")
    status, msg = runner.execute("check_date")
    print(f"Status: {status}\n{msg}")

    print("\n--- Test 2: Safe Command (Disk) ---")
    status, msg = runner.execute("check_disk")
    print(f"Status: {status}\n{msg}")

    print("\n--- Test 3: Danger Command (Not Authenticated) ---")
    status, msg = runner.execute("update_system", is_authenticated=False)
    print(f"Status: {status}\n{msg}")

    print("\n--- Test 4: Danger Command (Authenticated) ---")
    # Yeh confirmation maangega
    status, msg = runner.execute("update_system", is_authenticated=True)
    print(f"Status: {status}\n{msg}")

    print("\n--- Test 5: Unknown Command ---")
    status, msg = runner.execute("delete_everything")
    print(f"Status: {status}\n{msg}")

    print("\n--- Test Complete ---")
