# SPDX-License-Identifier: GPL-3.0-or-later
"""Remove live-session packages from the target only, before initramfs generation."""
import re
import libcalamares

LIVE_PACKAGES = (
    "live-boot", "live-boot-initramfs-tools", "live-config",
    "live-config-systemd", "live-config-sysvinit", "live-tools",
)


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
