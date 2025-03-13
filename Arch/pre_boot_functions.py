from dependencies import *

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