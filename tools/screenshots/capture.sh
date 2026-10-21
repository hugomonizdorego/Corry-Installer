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
settings['sequence'] = [{'show': ['welcome', 'welcome@check', 'locale', 'keyboard', 'users', 'summary']},
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
# The 1120x780 window is centered on the 1280x860 screen.
shot() { xdotool mousemove 1270 850; sleep 0.5; import -window root -crop 1120x780+80+40 +repage "$out/$distro-$1.png"; }
click() { xdotool mousemove "$1" "$2" click 1; sleep "${3:-1.5}"; }
next() { click 980 799 2; }
shot 01-welcome; next
sleep 2; shot 02-system-check; next
shot 03-location; next
shot 04-keyboard; next
# Field positions below Corry's page heading.
click 237 313; xdotool type --delay 20 'Hugo Moniz'
click 237 529; xdotool type a; click 480 529; xdotool type a
shot 07-users
click 125 603; shot 08-users-admin-password; click 125 603
next; shot 09-summary
next; shot 10-confirm
# "Install now" is the default button of the confirmation dialog.
xdotool key Return; sleep 6; shot 11-install
sleep 10; shot 12-install-slides
sleep 20; shot 13-finish
echo "Screenshots written to $out"
