# SPDX-License-Identifier: GPL-3.0-or-later
"""Remove live-session packages and installer launchers from the target only."""
from pathlib import Path
import re
import libcalamares

LIVE_PACKAGES = (
    "live-boot", "live-boot-initramfs-tools", "live-config",
    "live-config-systemd", "live-config-sysvinit", "live-tools",
)
# The live image is unpacked as-is, so the installed system would otherwise keep
# showing "Install" launchers. The installer binaries themselves stay in place.
LAUNCHERS = (
    "usr/share/applications/corry-installer.desktop",
    "etc/skel/Desktop/corry-installer.desktop",
    "etc/xdg/autostart/corry-installer.desktop",
    "usr/local/share/applications/calamares.desktop",
    "usr/local/share/applications/install-debian.desktop",
    "usr/local/bin/install-debian",
)


def remove_launchers(root, username, extra=()):
    root = Path(root)
    paths = list(LAUNCHERS) + list(extra)
    if username:
        paths.append("home/{}/Desktop/corry-installer.desktop".format(username))
    for relative in paths:
        if relative.startswith("/") or ".." in Path(relative).parts:
            raise ValueError("Launcher paths must be relative to the target: " + relative)
        path = root / relative
        if path.is_file() or path.is_symlink():
            path.unlink()


def pretty_name():
    return "Prepare the installed system"


def run():
    # Never allow this module to run against the live root.
    root = libcalamares.globalstorage.value("rootMountPoint")
    if not root or root == "/":
        return ("Invalid target", "Corry cleanup requires a mounted target system.")
    installed = []
    for package in LIVE_PACKAGES:
        if libcalamares.utils.target_env_call(["dpkg-query", "--status", package]) == 0:
            installed.append(package)
    if installed:
        code = libcalamares.utils.target_env_call(["dpkg", "--purge"] + installed)
        if code:
            return ("Could not remove live-session packages", "Target dpkg returned error {}.".format(code))
    live_user = libcalamares.job.configuration.get("liveUser", "")
    new_user = libcalamares.globalstorage.value("username")
    try:
        remove_launchers(root, new_user, libcalamares.job.configuration.get("removeFiles", []))
    except (OSError, ValueError) as exc:
        return ("Could not remove installer launchers", str(exc))
    if live_user and live_user != new_user:
        if not re.fullmatch(r"[a-z_][a-z0-9_-]*", live_user) or live_user == "root":
            return ("Invalid live username", "Set corrycleanup.liveUser to the live image account.")
        if libcalamares.utils.target_env_call(["id", "-u", live_user]) == 0:
            # A preserved /home partition may contain a real user's directory
            # with the same name as the live account. Remove the account only.
            code = libcalamares.utils.target_env_call(["userdel", "--", live_user])
            if code:
                return ("Could not remove the live account", "Target userdel returned error {}.".format(code))
    return None
