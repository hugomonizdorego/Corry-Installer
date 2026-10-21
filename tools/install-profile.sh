#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Install the Corry profile for one distribution and make Corry the live
# session's default installer. Run inside the ISO build chroot, or set DESTDIR.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
destination=${DESTDIR:-}
image=/run/live/medium/live/filesystem.squashfs
distro=debion
autostart=no
usage='Usage: install-profile.sh [--distro edukasaun|debion] [--image /absolute/image.squashfs] [--autostart]'
while [[ $# -gt 0 ]]; do
 case "$1" in
  --image) [[ $# -ge 2 && $2 == /* ]] || { echo '--image requires an absolute path' >&2; exit 2; }; image=$2; shift 2;;
  --distro) [[ $# -ge 2 ]] || { echo "$usage" >&2; exit 2; }; distro=$2; shift 2;;
  --autostart) autostart=yes; shift;;
  *) echo "$usage" >&2; exit 2;;
 esac
done
case "$distro" in edukasaun|debion) ;; *) echo "Unknown distribution profile '$distro'. Use edukasaun or debion." >&2; exit 2;; esac
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
rm -rf -- "$config/branding/corry/slides"
cp -r "$repo/src/branding/corry/". "$config/branding/corry/"
cp -r "$repo/config/distros/$distro/slides" "$config/branding/corry/"
install -m644 "$repo/config/distros/$distro/branding.desc" "$config/branding/corry/branding.desc"
python3 - "$repo" "$config" "$image" "$distro" <<'INNER'
import json, pathlib, sys, yaml
repo, config = map(pathlib.Path, sys.argv[1:3]); image, distro = sys.argv[3:]
(config/'modules/unpackfs.conf').write_text(yaml.safe_dump({'unpack': [{'source': image, 'sourcefs': 'squashfs', 'destination': ''}]}, sort_keys=False))
# The boot medium is the directory that holds live/filesystem.squashfs.
medium = pathlib.PurePosixPath(image).parent.parent
(config/'modules/corrygrub.conf').write_text(yaml.safe_dump({'medium': str(medium)}))
profile = yaml.safe_load((repo/f'config/distros/{distro}/profile.yaml').read_text())
brand = config/'branding/corry'
for name in ['stylesheet.qss', 'corry-mark.svg', 'calamares-sidebar.qml', 'show.qml', 'SlideControl.qml']:
    path = brand/name
    path.write_text(path.read_text().replace('#6445a4', profile['accent']).replace('#f0ecf8', profile['tint']))
(config/'corry-distro').write_text(distro + '\n')
slides = brand/'slides'
entries = json.loads((slides/'slides.json').read_text())
if not entries:
    raise SystemExit('A distribution must provide at least one slideshow image')
for entry in entries:
    picture = pathlib.Path(entry['image'])
    if picture.is_absolute() or '..' in picture.parts or not (slides/picture).is_file():
        raise SystemExit('Invalid local slideshow image: ' + str(picture))
(slides/'Slides.js').write_text('// SPDX-License-Identifier: CC0-1.0\nvar slides = ' + json.dumps(entries, ensure_ascii=False) + ';\n')
INNER
install -m755 "$repo/tools/preflight.py" "$destination/usr/lib/corry/"
install -m755 "$repo/tools/corry-installer" "$destination/usr/bin/corry-installer"
product=$(python3 -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))["name"])' "$repo/config/distros/$distro/profile.yaml")
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
echo "Corry profile installed for $distro and set as the default installer. Run corry-installer from the live session."
