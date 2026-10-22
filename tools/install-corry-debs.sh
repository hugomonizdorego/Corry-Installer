#!/bin/sh
# SPDX-License-Identifier: GPL-3.0-or-later
# Install the Corry .deb packages that sit next to this script.
#
#   sudo sh install-corry-debs.sh edukasaun     (or: debion)
#
# Uses apt, which downloads the dependencies and replaces Debian's Calamares.
# Also repairs a system where the packages were tried with "dpkg -i" before.
set -e
profile=${1:-edukasaun}
case "$profile" in
 edukasaun|debion) ;;
 *) echo "Usage: sudo sh $0 edukasaun|debion" >&2; exit 2;;
esac
[ "$(id -u)" = 0 ] || { echo "Run with sudo: sudo sh $0 $profile" >&2; exit 1; }
dir=$(cd "$(dirname "$0")" && pwd)
# corry_*.deb does not match the debug-symbol package corry-dbgsym_*.deb.
engine=$(ls "$dir"/corry_*.deb 2>/dev/null | head -n 1)
profile_deb=$(ls "$dir"/corry-"$profile"_*.deb 2>/dev/null | head -n 1)
[ -n "$engine" ] && [ -n "$profile_deb" ] || {
 echo "corry_*.deb and corry-${profile}_*.deb must be in $dir" >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
apt-get update
# Finish or undo whatever an earlier "dpkg -i" left half-installed.
apt-get install -y --fix-broken || true
apt-get install -y "$engine" "$profile_deb"
# Corry's APT hook purges what is left of Calamares after this second run.
apt-get install -y --reinstall "$profile_deb" >/dev/null
# Debug symbols are not needed to install systems.
if dpkg-query -W corry-dbgsym >/dev/null 2>&1; then apt-get purge -y corry-dbgsym; fi
echo "Corry is installed and is the default installer. Start it with: corry-installer"
