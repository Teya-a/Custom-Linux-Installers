from dependencies import *

# --- Signal Handler for Ctrl+C ---

def signal_handler(sig, frame):
    print(f"\n{YELLOW}[INFO] Exited based on user request (Ctrl+C received).{NC}")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)


# --- Run a command and exit on failure ---

def run_cmd(cmd):
    try:
        subprocess.run(cmd, check=True)

    except subprocess.CalledProcessError:

        print(f"{RED}Error executing: {' '.join(cmd)}{NC}")
        sys.exit(1)


# --- Display a Banner ---

def show_logo():
    os.system("clear")
    print(f"{GREEN}{logo}{NC}")
    print(f"{BLUE}Secure Arch Linux Installer v3.0{NC}\n")


# --- Get Validated User Input ---

def get_valid_input(prompt, input_type):
    retries = 0

    while retries < MAX_RETRIES:

        if input_type == "disk":
            print(f"\n{YELLOW}Available disks:{NC}")
            run_cmd(["lsblk", "-d", "-o", "NAME,SIZE"])

        user_input = input(prompt + " ").strip()

        if input_type == "disk":

            if not user_input.startswith("/dev/"):
                user_input = "/dev/" + user_input

            if os.path.exists(user_input) and os.path.exists(f"/sys/block/{os.path.basename(user_input)}"):
                print(f"{GREEN}Disk '{user_input}' is valid.{NC}")
                return user_input

        elif input_type == "hostname":

            if user_input:
                print(f"{GREEN}Hostname '{user_input}' is valid.{NC}")
                return user_input

        elif input_type == "username":

            if re.match(r'^[a-z_][a-z0-9_-]*$', user_input):
                print(f"{GREEN}Username '{user_input}' is valid.{NC}")
                return user_input

        elif input_type == "cryptname":

            # Allow empty input; if empty, use default.
            if not user_input:
                print(f"{GREEN}Using default LUKS mapping name 'cryptroot'.{NC}")
                return "cryptroot"

            # Otherwise, any non-empty string is acceptable.

            print(f"{GREEN}LUKS mapping name '{user_input}' is valid.{NC}")
            return user_input

        print(f"{RED}Invalid input! Attempts left: {MAX_RETRIES - retries - 1}{NC}")
        retries += 1

    print(f"{RED}Maximum invalid attempts reached! Exiting.{NC}")
    sys.exit(1)