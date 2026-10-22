#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Install the Corry package that sits next to this script:
#
#   sudo sh install-corry-debs.sh               (the only corry-*.deb here)
#   sudo sh install-corry-debs.sh edukasaun     (or: debion, if both are here)
#
# corry-edukasaun is built for Debian stable (Edukasaun OS), corry-debion for
# Debian testing (DebION GNU/Linux). Uses apt, which downloads the dependencies
# and replaces Debian's Calamares. Also repairs an earlier failed "dpkg -i".
set -e
[ "$(id -u)" = 0 ] || { echo "Run with sudo: sudo sh $0 $*" >&2; exit 1; }
dir=$(cd "$(dirname "$0")" && pwd)
case "${1:-}" in
 edukasaun|debion) package=$(ls "$dir"/corry-"$1"_*.deb 2>/dev/null | head -n 1);;
 '') set -- "$dir"/corry-edukasaun_*.deb "$dir"/corry-debion_*.deb
     package=
     for candidate; do
      [ -f "$candidate" ] || continue
      [ -z "$package" ] || { echo "Both packages are here; choose: sudo sh $0 edukasaun|debion" >&2; exit 2; }
      package=$candidate
     done;;
 *) echo "Usage: sudo sh $0 [edukasaun|debion]" >&2; exit 2;;
esac
[ -n "$package" ] || { echo "No corry-edukasaun_*.deb or corry-debion_*.deb in $dir" >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get update
# Finish or undo whatever an earlier "dpkg -i" left half-installed.
apt-get install -y --fix-broken || true
apt-get install -y "$package"
# Corry's APT hook purges what is left of Calamares after this second run.
apt-get install -y --reinstall "$package" >/dev/null
# Packages of Corry 0.1 that this one replaces, if any are left.
for old in corry-dbgsym; do
 if dpkg-query -W "$old" >/dev/null 2>&1; then apt-get purge -y "$old"; fi
done
echo "Corry is installed and is the default installer."
echo "Start it from the desktop shortcut or the menu, or run: corry-installer"
