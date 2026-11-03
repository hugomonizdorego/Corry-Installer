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
# The newest corry-DISTRO_*.deb here (several versions may sit side by side).
newest() { ls "$dir"/corry-"$1"_*.deb 2>/dev/null | sort -V | tail -n 1; }
case "${1:-}" in
 edukasaun|debion) package=$(newest "$1");;
 '') edukasaun=$(newest edukasaun); debion=$(newest debion)
     if [ -n "$edukasaun" ] && [ -n "$debion" ]; then
      echo "Packages for both distributions are here; choose: sudo sh $0 edukasaun|debion" >&2; exit 2
     fi
     package=$edukasaun$debion;;
 *) echo "Usage: sudo sh $0 [edukasaun|debion]" >&2; exit 2;;
esac
[ -n "$package" ] || { echo "No corry-edukasaun_*.deb or corry-debion_*.deb in $dir" >&2; exit 1; }
export DEBIAN_FRONTEND=noninteractive
# The installer's own configuration always comes from the new package: no
# conffile question can stop the script.
confnew="-o Dpkg::Options::=--force-confdef -o Dpkg::Options::=--force-confnew"
apt-get update
# Finish or undo whatever an earlier "dpkg -i" left half-installed.
apt-get install -y --fix-broken || true
# shellcheck disable=SC2086
apt-get install -y $confnew "$package"
# Corry's APT hook purges what is left of Calamares after this second run.
# shellcheck disable=SC2086
apt-get install -y $confnew --reinstall "$package" >/dev/null
# Packages of Corry 0.1 that this one replaces, if any are left.
for old in corry-dbgsym; do
 if dpkg-query -W "$old" >/dev/null 2>&1; then apt-get purge -y "$old"; fi
done
echo "Corry is installed and is the default installer."
echo "Start it from the desktop shortcut or the menu, or run: corry-installer"
