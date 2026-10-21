#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
build=${1:-"$repo/build-corry"}
. /etc/os-release
qt6=OFF
[[ ${VERSION_ID:-} != 13 ]] || qt6=ON
# Keep only the modules used by the Debian profile. Extra views remain available
# in the source and can be enabled deliberately in later iterations.
keep=' welcome locale keyboard partition users summary finished mount unpackfs machineid fstab localecfg displaymanager networkcfg hwclock corrycleanup initramfs grubcfg bootloader umount '
skip=()
for path in "$repo"/src/modules/*/; do
 name=$(basename "$path")
 [[ $keep == *" $name "* ]] || skip+=("$name")
done
cmake -S "$repo" -B "$build" -G Ninja -DCMAKE_BUILD_TYPE="${CORRY_BUILD_TYPE:-RelWithDebInfo}"  -DCMAKE_INSTALL_PREFIX=/usr -DWITH_QT6="$qt6" -DWITH_QML=ON -DWITH_PYTHON=ON  -DINSTALL_CONFIG=OFF -DBUILD_TESTING=ON -DBUILD_CRASH_REPORTING=OFF  -DSKIP_MODULES="${skip[*]}"
cmake --build "$build" --parallel "${CORRY_BUILD_JOBS:-2}"
# A successful generic configure may skip a module whose dependencies are missing.
# Require the native pages explicitly rather than shipping a partial installer.
cmake --build "$build" --target calamares_viewmodule_partition calamares_viewmodule_users
