#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Install the Corry profile for one distribution and make Corry the live
# session's default installer. Run inside the ISO build chroot, or set DESTDIR.
# Every file written here is recorded in /usr/lib/corry/manifest so that the
# installed system can be cleaned of Corry completely.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
destination=${DESTDIR:-}
image=/run/live/medium/live/filesystem.squashfs
distro=debion
folder=
autostart=no
usage='Usage: install-profile.sh [--distro ID | --distro-dir PATH] [--image /absolute/image.squashfs] [--autostart]'
while [[ $# -gt 0 ]]; do
 case "$1" in
  --image) [[ $# -ge 2 && $2 == /* ]] || { echo '--image requires an absolute path' >&2; exit 2; }; image=$2; shift 2;;
  --distro) [[ $# -ge 2 ]] || { echo "$usage" >&2; exit 2; }; distro=$2; shift 2;;
  --distro-dir) [[ $# -ge 2 ]] || { echo "$usage" >&2; exit 2; }; folder=$(cd -- "$2" && pwd); shift 2;;
  --autostart) autostart=yes; shift;;
  *) echo "$usage" >&2; exit 2;;
 esac
done
if [[ -z $folder ]]; then
 [[ $distro =~ ^[a-z0-9][a-z0-9-]*$ ]] || { echo "Invalid distribution id '$distro'." >&2; exit 2; }
 folder="$repo/config/distros/$distro"
fi
[[ -f $folder/distro.yaml ]] || {
 echo "No distro.yaml in $folder. Available: $(cd "$repo/config/distros" && ls -d */ | tr -d / | tr '\n' ' ')" >&2; exit 2; }
[[ -n $destination || $EUID == 0 ]] || { echo 'Run as root or set DESTDIR for staging.' >&2; exit 1; }
config="$destination/etc/calamares"
if [[ -f $config/settings.conf ]]; then
 backup="$config/backup-corry-$(date +%Y%m%d-%H%M%S)-$$"
 mkdir -p "$backup"
 cp -a "$config/settings.conf" "$backup/"
 for item in modules branding; do
  [[ ! -e $config/$item ]] || cp -a "$config/$item" "$backup/"
 done
fi
# Older Corry revisions generated these for the removed software page.
rm -f -- "$config/corry-software.yaml" "$config/modules/packagechooser.conf" \
 "$config/modules/corryprepare.conf" "$config/modules/corrypackages.conf"
install -d "$config/modules" "$config/branding/corry" "$destination/usr/bin" "$destination/usr/lib/corry" \
 "$destination/usr/share/applications" "$destination/usr/local/bin" "$destination/usr/local/share/applications" \
 "$destination/etc/skel/Desktop" "$destination/etc/xdg/autostart"
install -m644 "$repo/config/corry/settings.conf" "$config/settings.conf"
install -m644 "$repo/config/corry/modules/"*.conf "$config/modules/"
# Replace product assets together so switching an ISO profile cannot mix images.
rm -rf -- "$config/branding/corry"
install -d "$config/branding/corry"
cp -r "$repo/src/branding/corry/". "$config/branding/corry/"
rm -rf -- "$config/branding/corry/slides"
for part in slides media; do
 [[ ! -d $folder/$part ]] || cp -r "$folder/$part" "$config/branding/corry/"
done
product=$(python3 "$repo/tools/corry-branding.py" "$folder" "$config" "$image" "$(cat "$repo/VERSION")")
install -m755 "$repo/tools/preflight.py" "$destination/usr/lib/corry/"
install -m755 "$repo/tools/corry-installer" "$destination/usr/bin/corry-installer"
launcher="$destination/usr/share/applications/corry-installer.desktop"
sed "s|^Name=.*|Name=Install $product|" "$repo/config/corry/corry-installer.desktop" > "$launcher"
chmod 644 "$launcher"
# Default installer: the live user gets a desktop icon, and the generic Debian
# launchers (calamares, install-debian) are hidden or redirected to Corry.
# /usr/local takes precedence over /usr in XDG_DATA_DIRS and PATH; nothing
# owned by a Debian package is overwritten.
install -m755 "$launcher" "$destination/etc/skel/Desktop/corry-installer.desktop"
for hidden in calamares install-debian; do
 printf '[Desktop Entry]\nType=Application\nName=Install\nExec=corry-installer\nHidden=true\nNoDisplay=true\n' \
  > "$destination/usr/local/share/applications/$hidden.desktop"
done
printf '#!/bin/sh\nexec /usr/bin/corry-installer "$@"\n' > "$destination/usr/local/bin/install-debian"
chmod 755 "$destination/usr/local/bin/install-debian"
if [[ $autostart == yes ]]; then
 { cat "$launcher"; printf 'X-GNOME-Autostart-enabled=true\n'; } > "$destination/etc/xdg/autostart/corry-installer.desktop"
else
 rm -f -- "$destination/etc/xdg/autostart/corry-installer.desktop"
fi
# Record what this profile installed; corrycleanup removes it from the target.
manifest="$destination/usr/lib/corry/manifest"
{
 [[ ! -f $manifest ]] || cat "$manifest"
 printf '%s\n' /etc/calamares /usr/lib/corry /usr/bin/corry-installer /usr/share/applications/corry-installer.desktop \
  /etc/skel/Desktop/corry-installer.desktop /etc/xdg/autostart/corry-installer.desktop \
  /usr/local/share/applications/calamares.desktop /usr/local/share/applications/install-debian.desktop \
  /usr/local/bin/install-debian
} | sort -u > "$manifest.new"
mv "$manifest.new" "$manifest"
echo "Corry $(cat "$repo/VERSION") profile installed for $product and set as the default installer. Run corry-installer from the live session."
