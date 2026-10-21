#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# Install a Corry build and record every installed file, so the corrycleanup
# job can remove Corry completely from the installed system.
set -euo pipefail
build=${1:?Usage: install-corry.sh BUILD_DIRECTORY}
destination=${DESTDIR:-}
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
if [[ -z $destination ]] && command -v dpkg-query >/dev/null; then
 # Corry replaces Calamares' files; Debian's packages must go first.
 sh "$repo/tools/remove-calamares" --purge
fi
cmake --install "$build"
install -d "$destination/usr/lib/corry"
# install_manifest.txt holds absolute paths, prefixed with DESTDIR when staging.
sed "s|^$destination||" "$build/install_manifest.txt" >> "$destination/usr/lib/corry/manifest"
sort -u -o "$destination/usr/lib/corry/manifest" "$destination/usr/lib/corry/manifest"
echo "Corry installed; $(wc -l < "$destination/usr/lib/corry/manifest") files recorded for removal after installation."
