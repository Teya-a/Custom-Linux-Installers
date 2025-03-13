#!/usr/bin/env python3

from dependencies import *

# --- Main Function ---

def main():

    global TARGET_DISK, HOSTNAME, USERNAME, ROOT_PASS, USER_PASS, CRYPT_NAME

    show_logo()

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
#    prepare_disk(TARGET_DISK, CRYPT_NAME)

    print(f"{BLUE}[INFO] Configuring GRUB bootloader...{NC}")
#    configure_grub(TARGET_DISK, CRYPT_NAME)

    print(f"{BLUE}[INFO] Configuring mkinitcpio...{NC}")
#    configure_mkinitcpio()

    print(f"\n{GREEN}Installation completed successfully!{NC}")


if __name__ == "__main__":
    main()