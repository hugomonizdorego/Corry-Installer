#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Capture screenshots of the REAL Corry build, page by page, on a virtual display.
#   bash tools/screenshots/capture.sh BUILD_DIR DISTRO OUTPUT_DIR
# Needs: Xvfb, xdotool, ImageMagick, a Corry build (tools/build-corry.sh).
# Disks cannot be listed in a container, so this runs a screenshot-only sequence
# without the partition step and with a harmless demo job in place of the real
# installation jobs. Nothing is written to any disk.
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
build=$(cd -- "$1" && pwd); distro=$2; out=$(mkdir -p "$3" && cd "$3" && pwd)
stage=$(mktemp -d); trap 'pkill -x calamares || true; rm -rf "$stage"' EXIT
DESTDIR=$stage bash "$repo/tools/install-profile.sh" --distro "$distro" >/dev/null
config=$stage/etc/calamares
qt=qt6; grep -q 'WITH_QT6:BOOL=ON' "$build/CMakeCache.txt" || qt=qt5
mkdir -p "$config/qml/calamares" && cp -r "$repo/src/qml/calamares-$qt/slideshow" "$config/qml/calamares/"
python3 - "$config" "$repo/tools/screenshots" <<'PY'
import sys, yaml
from pathlib import Path
config, demo = Path(sys.argv[1]), sys.argv[2]
settings = yaml.safe_load((config / 'settings.conf').read_text())
settings['modules-search'] = ['local', demo]
settings['sequence'] = [{'show': ['welcome', 'welcome@check', 'locale', 'keyboard', 'users', 'corrysystem@init',
                                   'corrysystem@bootloader', 'summary']},
                        {'exec': ['corrydemo']}, {'show': ['finished']}]
(config / 'settings.conf').write_text(yaml.safe_dump(settings, sort_keys=False))
check = yaml.safe_load((config / 'modules/welcomecheck.conf').read_text())
# A container has no disks; the storage result would only show that.
check['requirements']['check'].remove('storage')
check['requirements']['required'] = ['ram', 'root']
(config / 'modules/welcomecheck.conf').write_text(yaml.safe_dump(check, sort_keys=False))
PY
export DISPLAY=${DISPLAY:-:99}
xdpyinfo >/dev/null 2>&1 || { Xvfb "$DISPLAY" -screen 0 1280x860x24 >/dev/null 2>&1 & sleep 1; }
(cd "$build" && LANG=en_US.UTF-8 ./calamares -d -c "$config" > "$stage/calamares.log" 2>&1 &)
sleep 18
# The window (windowSize in branding.desc) is centered on the 1280x860 screen.
size=$(python3 -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))["windowSize"].replace("px", ""))' \
 "$config/branding/corry/branding.desc")
width=${size%,*}; height=${size#*,}; left=$(( (1280 - width) / 2 )); top=$(( (860 - height) / 2 ))
shot() { xdotool mousemove 1279 859; sleep 0.5; import -window root -crop "${width}x${height}+$left+$top" +repage "$out/$distro-$1.png"; }
click() { xdotool mousemove "$1" "$2" click 1; sleep "${3:-1.5}"; }
# The Next button is the gradient pill at the bottom right of the window.
next() { click "${CORRY_NEXT_X:-$(( left + width - 222 ))}" "${CORRY_NEXT_Y:-$(( top + height - 36 ))}" 2; }
# Field positions inside the page card (see docs/screenshots to re-check):
# name, password, repeated password, "same password for the administrator".
if grep -q 'sidebar: qml,left' "$config/branding/corry/branding.desc"; then
 fields=(456 214 456 436 706 436 350 520)   # side menu, 1240x780 window
else
 fields=(280 333 280 549 523 549 160 641)   # header on top, 1120x780 window
fi
shot 01-welcome; next
sleep 2; shot 02-system-check; next
shot 03-location; next
shot 04-keyboard; next
click "${fields[0]}" "${fields[1]}"; xdotool type --delay 20 'Hugo Moniz'
click "${fields[2]}" "${fields[3]}"; xdotool type a; click "${fields[4]}" "${fields[5]}"; xdotool type a
shot 07-users
click "${fields[6]}" "${fields[7]}"; shot 08-users-admin-password; click "${fields[6]}" "${fields[7]}"
next; shot 09-system-init
next; shot 10-system-boot-loader
next; shot 11-summary
next; shot 12-confirm
# "Install now" is the default button of the confirmation dialog.
xdotool key Return; sleep 6; shot 13-install
sleep 10; shot 14-install-slides
sleep 20; shot 15-finish
echo "Screenshots written to $out"
