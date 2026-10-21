# SPDX-License-Identifier: GPL-3.0-or-later
# Sourced by the Corry scripts. Sets corry_base to "stable" or "testing".
# Edukasaun OS and DebION keep Debian's /etc/debian_version, which names the base
# even when /etc/os-release carries the product's own name and version.
corry_detect_base() {
 local version
 version=$(cat /etc/debian_version 2>/dev/null || true)
 case ${CORRY_DEBIAN_BASE:-} in
  stable|testing) corry_base=$CORRY_DEBIAN_BASE; return 0;;
  '') ;;
  *) echo 'CORRY_DEBIAN_BASE must be stable or testing.' >&2; return 1;;
 esac
 case $version in
  13|13.*) corry_base=stable;;
  14|14.*|forky*|*/sid) corry_base=testing;;
  *) echo "Unsupported Debian base '${version:-unknown}'. Corry supports Debian 13 (stable) and Debian testing; set CORRY_DEBIAN_BASE=stable or testing for a derivative." >&2
     return 1;;
 esac
}
