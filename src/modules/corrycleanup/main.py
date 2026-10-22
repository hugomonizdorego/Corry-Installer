# SPDX-License-Identifier: GPL-3.0-or-later
"""Remove the live session and Corry itself from the installed system.

The target is unpacked from the live image, so it starts with the live-boot
packages, the live account and the whole installer. After this job the new
system has no trace of Corry: no launcher, menu entry, configuration, program
file or package. Only the target is changed; the running installer is not.
"""
from pathlib import Path
import re
import shutil
import libcalamares

LIVE_PACKAGES = (
    "live-boot", "live-boot-initramfs-tools", "live-config",
    "live-config-systemd", "live-config-sysvinit", "live-tools",
)
# Debian packages that only exist for the installer: Corry's own packages and,
# for script installs, Debian's Calamares.
INSTALLER_PACKAGES = ("corry-edukasaun", "corry-debion", "corry", "calamares", "calamares-settings-debian")
# Files and directories that belong only to the installer.
INSTALLER_PATHS = (
    "usr/share/applications/corry-installer.desktop",
    "usr/share/applications/calamares.desktop",
    "etc/skel/Desktop/corry-installer.desktop",
    "etc/xdg/autostart/corry-installer.desktop",
    "etc/xdg/autostart/corry-desktop-icon.desktop",
    "etc/apt/apt.conf.d/80corry-remove-calamares",
    "usr/local/share/applications/calamares.desktop",
    "usr/local/share/applications/install-debian.desktop",
    "usr/local/bin/install-debian",
    "usr/bin/corry-installer",
    "usr/share/icons/hicolor/scalable/apps/corry-installer.svg",
    "usr/share/pixmaps/corry-installer.png",
    "usr/bin/calamares",
    "usr/share/polkit-1/actions/com.github.calamares.calamares.policy",
    "usr/share/metainfo/io.calamares.calamares.appdata.xml",
    "usr/share/man/man8/calamares.8.gz",
    "etc/calamares",
    "usr/share/calamares",
    "usr/lib/calamares",
    "usr/include/libcalamares",
    "usr/lib/cmake/Calamares",
)
# The manifest lists every file installed by tools/install-corry.sh and
# tools/install-profile.sh. It is removed last.
MANIFEST = "usr/lib/corry/manifest"
# Never removed, even if a manifest lists them.
PROTECTED = {"", "etc", "usr", "usr/bin", "usr/lib", "usr/share", "usr/local", "usr/local/bin",
             "usr/share/applications", "usr/local/share", "usr/local/share/applications",
             "etc/skel", "etc/xdg", "etc/xdg/autostart", "home", "boot", "var", "root"}


def relative_path(value):
    relative = value.strip().lstrip("/")
    parts = Path(relative).parts
    if not relative or ".." in parts:
        raise ValueError("Unsafe path for removal: " + value)
    return relative


def remove(root, relative):
    relative = relative_path(relative)
    if relative.rstrip("/") in PROTECTED:
        return
    path = Path(root) / relative
    if path.is_dir() and not path.is_symlink():
        shutil.rmtree(path)
    elif path.exists() or path.is_symlink():
        path.unlink()


def remove_empty_parents(root, relative):
    parent = Path(relative_path(relative)).parent
    while str(parent) not in PROTECTED and str(parent) != ".":
        try:
            (Path(root) / parent).rmdir()
        except OSError:
            return
        parent = parent.parent


def remove_installer(root, username, extra=()):
    """Delete every Corry file from the target and return the paths handled."""
    root = Path(root)
    paths = list(INSTALLER_PATHS) + list(extra)
    if username:
        paths.append("home/{}/Desktop/corry-installer.desktop".format(username))
    manifest = root / MANIFEST
    if manifest.is_file():
        paths += [line for line in manifest.read_text().splitlines() if line.strip()]
    paths.append("usr/lib/corry")
    for relative in paths:
        remove(root, relative)
    for relative in paths:
        remove_empty_parents(root, relative)
    return paths


def installed(packages):
    return [p for p in packages if libcalamares.utils.target_env_call(["dpkg-query", "--status", p]) == 0]


def pretty_name():
    return "Remove the live session and the installer"


def run():
    # Never allow this module to run against the live root.
    root = libcalamares.globalstorage.value("rootMountPoint")
    if not root or root == "/":
        return ("Invalid target", "Corry cleanup requires a mounted target system.")
    configuration = libcalamares.job.configuration
    packages = installed(LIVE_PACKAGES + INSTALLER_PACKAGES + tuple(configuration.get("purgePackages", [])))
    if packages:
        code = libcalamares.utils.target_env_call(["dpkg", "--purge"] + packages)
        if code:
            return ("Could not remove live-session packages", "Target dpkg returned error {}.".format(code))
    live_user = configuration.get("liveUser", "")
    new_user = libcalamares.globalstorage.value("username")
    try:
        remove_installer(root, new_user, configuration.get("removeFiles", []))
    except (OSError, ValueError) as exc:
        return ("Could not remove the installer", str(exc))
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
