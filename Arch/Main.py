#!/usr/bin/env python3

import os
import sys
import re
import signal
import subprocess
import getpass


# --- Helper to convert hex color codes to ANSI escape sequences ---

def hex_to_ansi(hex_color):
    # Remove the '#' if present

    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return f"\033[38;2;{r};{g};{b}m"


# --- Simplified Colors (using hex codes converted to ANSI) ---

RED = hex_to_ansi("#FF0000")
GREEN = hex_to_ansi("#00FF00")
YELLOW = hex_to_ansi("#FFFF00")
BLUE = hex_to_ansi("#0000FF")
NC = "\033[0m"

MAX_RETRIES = 5

# Global variables (populated during execution)

TARGET_DISK = ""
USERNAME = ""
HOSTNAME = ""
ROOT_PASS = ""
USER_PASS = ""
CRYPT_NAME = "cryptroot"  # Default LUKS mapping name


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

def show_banner():
    os.system("clear")
    banner = r"""
 _______  _______  _______             _       _________ _                           _________ _        _______ _________ _______  _        _        _______  _______ 
(  ___  )(  ____ )(  ____ \|\     /|  ( \      \__   __/( (    /||\     /||\     /|  \__   __/( (    /|(  ____ \\__   __/(  ___  )( \      ( \      (  ____ \(  ____ )
| (   ) || (    )|| (    \/| )   ( |  | (         ) (   |  \  ( || )   ( |( \   / )     ) (   |  \  ( || (    \/   ) (   | (   ) || (      | (      | (    \/| (    )|
| (___) || (____)|| |      | (___) |  | |         | |   |   \ | || |   | | \ (_) /      | |   |   \ | || (_____    | |   | (___) || |      | |      | (__    | (____)|
|  ___  ||     __)| |      |  ___  |  | |         | |   | (\ \) || |   | |  ) _ (       | |   | (\ \) |(_____  )   | |   |  ___  || |      | |      |  __)   |     __)
| (   ) || (\ (   | |      | (   ) |  | |         | |   | | \   || |   | | / ( ) \      | |   | | \   |      ) |   | |   | (   ) || |      | |      | (      | (\ (   
| )   ( || ) \ \__| (____/\| )   ( |  | (____/\___) (___| )  \  || (___) |( /   \ )  ___) (___| )  \  |/\____) |   | |   | )   ( || (____/\| (____/\| (____/\| ) \ \__
|/     \||/   \__/(_______/|/     \|  (_______/\_______/|/    )_)(_______)|/     \|  \_______/|/    )_)\_______)   )_(   |/     \|(_______/(_______/(_______/|/   \__/
"""
    print(f"{GREEN}{banner}{NC}")
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


# --- Prepare Disk Function ---

def prepare_disk(target_disk, mapping_name):
    print(f"\n{BLUE}=== Disk Preparation ==={NC}")
    print(f"\n{YELLOW}Available disks:{NC}")
    run_cmd(["lsblk", "-d", "-o", "NAME,SIZE"])

    os.makedirs("/mnt/boot/efi", exist_ok=True)

    # Partition the disk.

    run_cmd(["parted", "-s", target_disk, "mklabel", "gpt"])
    run_cmd(["parted", "-s", target_disk, "mkpart", "ESP", "fat32", "1MiB", "513MiB"])
    run_cmd(["parted", "-s", target_disk, "set", "1", "esp", "on"])
    run_cmd(["parted", "-s", target_disk, "mkpart", "primary", "513MiB", "100%"])

    # Format the EFI partition.

    efi_partition = target_disk + "p1"
    run_cmd(["mkfs.fat", "-F32", efi_partition])

    # Set up LUKS2 on the second partition.

    luks_partition = target_disk + "p2"
    print(f"{YELLOW}Setting up LUKS2 on {luks_partition}{NC}")

    run_cmd([
        "cryptsetup", "luksFormat", "--type", "luks2", "--hash", "sha512",
        "--key-size", "512", "--iter-time", "5000", "--pbkdf", "pbkdf2",
        "--verify-passphrase", luks_partition
    ])

    run_cmd(["cryptsetup", "open", luks_partition, mapping_name])

    # Create Btrfs filesystem.

    run_cmd(["mkfs.btrfs", "-L", "TwixyOS", f"/dev/mapper/{mapping_name}"])
    run_cmd(["mount", f"/dev/mapper/{mapping_name}", "/mnt"])

    # Create subvolumes.

    subvolumes = ["@", "@home", "@snapshots", "@boot", "@var_log"]
    for sv in subvolumes:
        run_cmd(["btrfs", "subvolume", "create", f"/mnt/{sv}"])

    run_cmd(["umount", "/mnt"])

    # Mount subvolumes.

    run_cmd(["mount", "-o", "noatime,compress=zstd:3,subvol=@", f"/dev/mapper/{mapping_name}", "/mnt"])
    os.makedirs("/mnt/boot", exist_ok=True)
    os.makedirs("/mnt/home", exist_ok=True)
    os.makedirs("/mnt/.snapshots", exist_ok=True)
    os.makedirs("/mnt/var/log", exist_ok=True)
    run_cmd(["mount", "-o", "noatime,compress=zstd:3,subvol=@boot", f"/dev/mapper/{mapping_name}", "/mnt/boot"])
    run_cmd(["mount", "-o", "noatime,compress=zstd:3,subvol=@home", f"/dev/mapper/{mapping_name}", "/mnt/home"])
    run_cmd(
        ["mount", "-o", "noatime,compress=zstd:3,subvol=@snapshots", f"/dev/mapper/{mapping_name}", "/mnt/.snapshots"])
    run_cmd(["mount", "-o", "noatime,compress=zstd:3,subvol=@var_log", f"/dev/mapper/{mapping_name}", "/mnt/var/log"])

    # Mount EFI partition.

    os.makedirs("/mnt/boot/efi", exist_ok=True)
    run_cmd(["mount", efi_partition, "/mnt/boot/efi"])

    print(f"{GREEN}Disk preparation completed.{NC}")


# --- Configure GRUB Function ---

def configure_grub(target_disk, mapping_name):
    print(f"\n{BLUE}=== GRUB Configuration ==={NC}")
    grub_defaults = "/etc/default/grub"

    try:

        with open(grub_defaults, "r") as f:
            lines = f.readlines()

    except Exception as e:
        print(f"{RED}Error reading {grub_defaults}: {e}{NC}")
        sys.exit(1)

    new_lines = []

    for line in lines:

        if line.startswith("GRUB_ENABLE_CRYPTODISK="):

            new_lines.append("GRUB_ENABLE_CRYPTODISK=y\n")

        elif line.startswith("GRUB_CMDLINE_LINUX="):

            # Get the LUKS UUID from the second partition.

            cmd = ["blkid", "-s", "UUID", "-o", "value", target_disk + "p2"]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            luks_uuid = result.stdout.strip()
            new_line = f'GRUB_CMDLINE_LINUX="cryptdevice=UUID={luks_uuid}:{mapping_name} root=/dev/mapper/{mapping_name} rootflags=subvol=@"\n'
            new_lines.append(new_line)

        else:

            new_lines.append(line)

    try:

        with open(grub_defaults, "w") as f:
            f.writelines(new_lines)

    except Exception as e:

        print(f"{RED}Error writing {grub_defaults}: {e}{NC}")
        sys.exit(1)

    run_cmd(["grub-install", "--target=x86_64-efi", "--efi-directory=/boot/efi", "--bootloader-id=TwixyOS"])
    run_cmd(["grub-mkconfig", "-o", "/boot/grub/grub.cfg"])

    print(f"{GREEN}GRUB configuration completed.{NC}")


# --- Configure mkinitcpio Function ---

def configure_mkinitcpio():
    print(f"\n{BLUE}=== mkinitcpio Configuration ==={NC}")
    mkinitcpio_conf = "/etc/mkinitcpio.conf"

    try:
        with open(mkinitcpio_conf, "r") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"{RED}Error reading {mkinitcpio_conf}: {e}{NC}")
        sys.exit(1)

    new_lines = []

    for line in lines:

        if line.startswith("HOOKS="):

            new_lines.append(
                "HOOKS=(base udev autodetect modconf block encrypt btrfs filesystems keyboard keymap consolefont)\n")

        else:

            new_lines.append(line)

    try:
        with open(mkinitcpio_conf, "w") as f:

            f.writelines(new_lines)

    except Exception as e:

        print(f"{RED}Error writing {mkinitcpio_conf}: {e}{NC}")
        sys.exit(1)

    run_cmd(["mkinitcpio", "-P"])
    print(f"{GREEN}mkinitcpio configuration completed.{NC}")


# --- Main Function ---

def main():
    global TARGET_DISK, HOSTNAME, USERNAME, ROOT_PASS, USER_PASS, CRYPT_NAME

    show_banner()

    # Get validated inputs.
    TARGET_DISK = get_valid_input("Enter target disk (e.g. nvme0n1 or /dev/nvme0n1):", "disk")
    HOSTNAME = get_valid_input("Enter hostname:", "hostname")
    USERNAME = get_valid_input("Enter username:", "username")

    # Ask for LUKS mapping name (allowing empty input to use default)

    CRYPT_NAME = get_valid_input("Enter LUKS mapping name (default: cryptroot):", "cryptname")

    # Securely prompt for passwords.

    ROOT_PASS = getpass.getpass("Enter root password: ")
    USER_PASS = getpass.getpass("Enter user password: ")

    print(f"{BLUE}[INFO] Starting disk preparation...{NC}")
    prepare_disk(TARGET_DISK, CRYPT_NAME)

    print(f"{BLUE}[INFO] Configuring GRUB bootloader...{NC}")
    configure_grub(TARGET_DISK, CRYPT_NAME)

    print(f"{BLUE}[INFO] Configuring mkinitcpio...{NC}")
    configure_mkinitcpio()

    print(f"\n{GREEN}Installation completed successfully!{NC}")


if __name__ == "__main__":
    main()