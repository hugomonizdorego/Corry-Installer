#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
mode=${1:-runtime}
case "$mode" in runtime|build) ;; *) echo 'Usage: install-dependencies.sh [runtime|build]' >&2; exit 2;; esac
[[ $EUID == 0 ]] || { echo 'Run with sudo, or as root inside the ISO build chroot.' >&2; exit 1; }
. /etc/os-release
[[ ${ID:-} == debian ]] || { echo 'This dependency profile supports Debian 12 and 13.' >&2; exit 1; }
case ${VERSION_ID:-} in 12|13) ;; *) echo 'Unsupported Debian release; validate package names first.' >&2; exit 1;; esac
apt-get update
runtime=(calamares zenity btrfs-progs xfsprogs e2fsprogs dosfstools jfsutils util-linux kmod parted
  cryptsetup lvm2 squashfs-tools rsync locales tzdata keyboard-configuration
  initramfs-tools sudo os-prober efibootmgr grub2-common python3 python3-yaml
  polkitd pkexec fonts-noto-core)
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
 if [[ $VERSION_ID == 13 ]]; then
   qt=(qt6-base-dev qt6-declarative-dev qt6-tools-dev qt6-tools-dev-tools
     qt6-l10n-tools qt6-svg-dev libpolkit-qt6-1-dev libkf6coreaddons-dev
     libkf6config-dev libkf6i18n-dev libkf6service-dev libkf6package-dev libkf6widgetsaddons-dev
     qml6-module-qtquick qml6-module-qtquick-layouts qml6-module-qtquick-controls
     qml6-module-qtquick-templates qml6-module-qtquick-window qml6-module-qtqml-workerscript)
 else
   qt=(qtbase5-dev qtdeclarative5-dev qttools5-dev qttools5-dev-tools
     libqt5svg5-dev libpolkit-qt5-1-dev libkf5coreaddons-dev libkf5config-dev
     libkf5i18n-dev libkf5service-dev libkf5package-dev libkf5widgetsaddons-dev qml-module-qtquick2
     qml-module-qtquick-layouts qml-module-qtquick-controls2)
 fi
 apt-get install -y --no-install-recommends "${common[@]}" "${qt[@]}"
fi
# ReiserFS is deliberately optional. No unsupported kernel driver is installed.
echo 'Corry dependencies installed. Include these packages in the live image before packing its squashfs.'
