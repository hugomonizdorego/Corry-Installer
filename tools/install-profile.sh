#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
destination=${DESTDIR:-}
image=/run/live/medium/live/filesystem.squashfs
distro=debion
brand_source=
while [[ $# -gt 0 ]]; do
 case "$1" in
  --image) [[ $# -ge 2 && $2 == /* ]] || { echo '--image requires an absolute path' >&2; exit 2; }; image=$2; shift 2;;
  --distro) [[ $# -ge 2 && $2 =~ ^[a-z0-9][a-z0-9-]*$ ]] || exit 2; distro=$2; shift 2;;
  --branding) [[ $# -ge 2 && $2 == /* ]] || { echo '--branding requires an absolute folder' >&2; exit 2; };brand_source=$2;shift 2;;
  *) echo 'Usage: install-profile.sh [--distro debion|edukasaun|custom] [--branding /folder] [--image /absolute/image.squashfs]' >&2; exit 2;;
 esac
done
brand_source=${brand_source:-"$repo/config/distros/$distro"}
[[ -n $destination || $EUID == 0 ]] || { echo 'Run as root or set DESTDIR for staging.' >&2; exit 1; }
work=$(mktemp -d -t corry-profile-XXXXXXXX)
trap 'rm -rf -- "$work"' EXIT
# Compile and validate all branding, paths, codecs and software before touching the active profile.
python3 "$repo/tools/configure-profile.py" --source "$brand_source" --output "$work" --image "$image" --distro "$distro"
config="$destination/etc/calamares"
if [[ -f $config/settings.conf ]]; then
 backup="$config/backup-corry-$(date +%Y%m%d-%H%M%S)-$$"
 mkdir -p "$backup"
 for item in settings.conf modules branding corry-software.yaml corry-distro; do
  [[ ! -e $config/$item ]] || cp -a "$config/$item" "$backup/"
 done
fi
install -d "$config/modules" "$config/branding" "$destination/usr/bin" "$destination/usr/lib/corry" "$destination/usr/share/applications"
rm -rf -- "$config/branding/corry"
cp -r "$work/". "$config/"
install -m755 "$repo/tools/preflight.py" "$repo/tools/repository-check.py" "$destination/usr/lib/corry/"
install -m644 "$repo/tools/apt_support.py" "$destination/usr/lib/corry/apt_support.py"
install -m755 "$repo/tools/corry-installer" "$destination/usr/bin/corry-installer"
install -m644 "$repo/config/corry/corry-installer.desktop" "$destination/usr/share/applications/corry-installer.desktop"
echo "Corry profile installed for $distro. Run corry-installer from the live session."
