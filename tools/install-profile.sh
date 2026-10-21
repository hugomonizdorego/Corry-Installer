#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
destination=${DESTDIR:-}
image=/run/live/medium/live/filesystem.squashfs
if [[ $# -gt 0 ]]; then
 [[ $# == 2 && $1 == --image && $2 == /* ]] || { echo 'Usage: install-profile.sh [--image /absolute/live/image.squashfs]' >&2; exit 2; }
 image=$2
fi
[[ -n $destination || $EUID == 0 ]] || { echo 'Run as root or set DESTDIR for staging.' >&2; exit 1; }
config="$destination/etc/calamares"
if [[ -f $config/settings.conf ]]; then
 backup="$config/backup-corry-$(date +%Y%m%d-%H%M%S)-$$"
 mkdir -p "$backup"
 cp -a "$config/settings.conf" "$backup/"
 [[ ! -d $config/modules ]] || cp -a "$config/modules" "$backup/"
fi
install -d "$config/modules" "$config/branding/corry" "$destination/usr/bin" "$destination/usr/lib/corry" "$destination/usr/share/applications"
install -m644 "$repo/config/corry/settings.conf" "$config/settings.conf"
install -m644 "$repo/config/corry/modules/"*.conf "$config/modules/"
install -m644 "$repo/src/branding/corry/"* "$config/branding/corry/"
# JSON strings are valid YAML scalars, including spaces and quotes in image paths.
python3 - "$config/modules/unpackfs.conf" "$image" <<'INNER'
import json, pathlib, sys
pathlib.Path(sys.argv[1]).write_text('unpack:\n  - source: ' + json.dumps(sys.argv[2]) + '\n    sourcefs: squashfs\n    destination: ""\n')
INNER
install -m755 "$repo/tools/preflight.py" "$destination/usr/lib/corry/preflight.py"
install -m755 "$repo/tools/corry-installer" "$destination/usr/bin/corry-installer"
install -m644 "$repo/config/corry/corry-installer.desktop" "$destination/usr/share/applications/corry-installer.desktop"
echo 'Corry profile installed. Run corry-installer from the live session.'
