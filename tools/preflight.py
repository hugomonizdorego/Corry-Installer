#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only checks. Never format, mount, or modify a disk."""
import argparse
import os
import pathlib
import shutil
import subprocess
import sys
import yaml

REQUIRED = ("mkfs.btrfs", "mkfs.ext4", "mkfs.xfs", "mkfs.fat", "mkswap",
            "unsquashfs", "rsync", "parted", "grub-install", "grub-mkconfig",
            "update-initramfs", "calamares", "modprobe", "sudo", "dpkg")
# GRUB platform files per Debian architecture: (UEFI, BIOS).
GRUB_PLATFORMS = {"amd64": ("x86_64-efi", "i386-pc"), "arm64": ("arm64-efi", None),
                  "i386": ("i386-efi", "i386-pc")}


def image_requirements(efi, arch):
    """Files the installed system needs to boot, as patterns inside the image."""
    platforms = GRUB_PLATFORMS.get(arch, (None, None))
    platform = platforms[0] if efi else platforms[1]
    needed = {"boot/vmlinuz-*": "a Linux kernel",
              "usr/sbin/update-initramfs": "initramfs-tools",
              "usr/sbin/grub-install": "grub2-common"}
    if platform:
        needed["usr/lib/grub/" + platform] = "GRUB files for " + platform
    return needed


def missing_from_image(image, efi, arch):
    needed = image_requirements(efi, arch)
    try:
        listing = subprocess.run(["unsquashfs", "-l", "-d", "", image] + list(needed),
                                 stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                 text=True, timeout=120).stdout
    except (OSError, subprocess.TimeoutExpired) as exc:
        return ["Could not read the live system image: " + str(exc)]
    found = [line.strip().lstrip("/") for line in listing.splitlines()]
    errors = []
    for pattern, description in needed.items():
        prefix = pattern.rstrip("*")
        if not any(path.startswith(prefix) for path in found):
            errors.append("The live system image has no {} ({}).".format(description, pattern))
    return errors


def check(config, efi=None, arch=None):
    # Desktop sessions may omit sbin from the unprivileged user's PATH.
    search_path = os.environ.get("PATH", os.defpath) + os.pathsep + "/usr/sbin:/sbin"
    errors = ["Missing dependency: " + name for name in REQUIRED if not shutil.which(name, path=search_path)]
    if efi is None:
        efi = pathlib.Path("/sys/firmware/efi").is_dir()
    try:
        settings = yaml.safe_load((config / "settings.conf").read_text())
        if settings.get("branding") != "corry":
            errors.append("The active installer profile is not Corry.")
        data = yaml.safe_load((config / "modules/unpackfs.conf").read_text())
        for image in data["unpack"]:
            if not pathlib.Path(image["source"]).is_file():
                errors.append("Live system image not found: " + image["source"])
            elif not errors:
                if arch is None:
                    arch = subprocess.run(["dpkg", "--print-architecture"], stdout=subprocess.PIPE,
                                          text=True).stdout.strip()
                errors.extend(missing_from_image(image["source"], efi, arch))
    except (OSError, ValueError, KeyError, TypeError, yaml.YAMLError) as exc:
        errors.append("Invalid Corry profile: " + str(exc))
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=pathlib.Path, default=pathlib.Path("/etc/calamares"))
    args = parser.parse_args()
    errors = check(args.config)
    if errors:
        print("Corry cannot start:\n" + "\n".join(errors), file=sys.stderr)
        return 1
    print("Corry preflight passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
