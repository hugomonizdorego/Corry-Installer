#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
mode=${1:-runtime}
case "$mode" in runtime|build) ;; *) echo 'Usage: install-dependencies.sh [runtime|build]' >&2; exit 2;; esac
[[ $EUID == 0 ]] || { echo 'Run with sudo, or as root inside the ISO build chroot.' >&2; exit 1; }
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
. "$repo/tools/debian-base.sh"
corry_detect_base
echo "Installing Corry dependencies for Debian $corry_base."
apt-get -o APT::Update::Error-Mode=any update
runtime=(calamares zenity btrfs-progs xfsprogs e2fsprogs dosfstools jfsutils util-linux kmod parted
  cryptsetup lvm2 squashfs-tools rsync locales tzdata keyboard-configuration
  initramfs-tools sudo os-prober efibootmgr grub2-common python3 python3-yaml
  polkitd pkexec fonts-noto-core gparted
  qml6-module-qtmultimedia libqt6multimedia6
  qml6-module-qtquick qml6-module-qtquick-layouts qml6-module-qtquick-controls
  qml6-module-qtquick-templates qml6-module-qtquick-window qml6-module-qtqml-workerscript)
# Binary support for the target architecture; no grub-pc/grub-efi metapackage conflict.
case $(dpkg --print-architecture) in
 amd64) runtime+=(grub-pc-bin grub-efi-amd64-bin) ;;
 arm64) runtime+=(grub-efi-arm64-bin) ;;
 i386) runtime+=(grub-pc-bin grub-efi-ia32-bin) ;;
 *) echo 'Configure bootloader packages for this architecture first.' >&2; exit 1;;
esac
apt-get install -y --no-install-recommends "${runtime[@]}"
if [[ $mode == build ]]; then
 common=(build-essential cmake ninja-build extra-cmake-modules pkg-config
   gettext libyaml-cpp-dev libicu-dev libpwquality-dev libkpmcore-dev libparted-dev
   python3-dev python3-jsonschema)
 qt=(qt6-base-dev qt6-declarative-dev qt6-tools-dev qt6-tools-dev-tools
   qt6-l10n-tools qt6-svg-dev libpolkit-qt6-1-dev libkf6coreaddons-dev
   libkf6config-dev libkf6i18n-dev libkf6service-dev libkf6package-dev libkf6widgetsaddons-dev
   qml6-module-qtquick qml6-module-qtquick-layouts qml6-module-qtquick-controls
   qml6-module-qtquick-templates qml6-module-qtquick-window qml6-module-qtqml-workerscript)
 apt-get install -y --no-install-recommends "${common[@]}" "${qt[@]}"
fi
# ReiserFS is deliberately optional. No unsupported kernel driver is installed.
echo 'Corry dependencies installed. Include these packages in the live image before packing its squashfs.'
