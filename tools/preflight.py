#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Read-only checks. Never format, mount, or modify a disk."""
import argparse
import pathlib
import shutil
import sys
import yaml

REQUIRED = ("mkfs.btrfs", "mkfs.ext4", "mkfs.xfs", "mkfs.fat", "mkswap",
            "unsquashfs", "rsync", "parted", "grub-install", "grub-mkconfig",
            "update-initramfs", "calamares", "modprobe", "sudo")


def check(config):
    errors = ["Missing dependency: " + name for name in REQUIRED if not shutil.which(name)]
    try:
        settings = yaml.safe_load((config / "settings.conf").read_text())
        if settings.get("branding") != "corry":
            errors.append("The active installer profile is not Corry.")
        data = yaml.safe_load((config / "modules/unpackfs.conf").read_text())
        for image in data["unpack"]:
            if not pathlib.Path(image["source"]).is_file():
                errors.append("Live system image not found: " + image["source"])
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
