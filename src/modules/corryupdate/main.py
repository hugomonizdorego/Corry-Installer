# SPDX-License-Identifier: GPL-3.0-or-later
"""Repair packages in the installed system and, when online, update them.

Works with and without internet. Offline, half-configured packages from the
image are finished. Online, the package lists are refreshed, broken
dependencies are fixed and updates are installed. This job never fails the
installation: every problem becomes a warning and the system keeps the
packages from the installation media.
"""
from pathlib import Path
import shutil
import urllib.request
import libcalamares

APT_OPTIONS = ["-y", "-o", "Dpkg::Options::=--force-confdef", "-o", "Dpkg::Options::=--force-confold"]
# Keeps package scripts from starting services inside the target.
POLICY = "#!/bin/sh\n# Temporary, written by Corry during installation.\nexit 101\n"


def pretty_name():
    return "Check and update packages"


def online(url, timeout=10):
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except Exception:  # OSError, ValueError, http.client.HTTPException (a non-HTTP answer)
        return False


def call(args, timeout):
    return libcalamares.utils.target_env_call(["env", "DEBIAN_FRONTEND=noninteractive"] + args, "", timeout)


class TemporaryFile:
    """Replace a target file for the duration of the job, then restore it."""

    def __init__(self, path, content=None, source=None):
        self.path, self.content, self.source = Path(path), content, source
        self.backup = self.path.with_name(self.path.name + ".corry-backup")

    def __enter__(self):
        self.in_place = None
        if self.path.exists() or self.path.is_symlink():
            try:
                self.path.rename(self.backup)
            except OSError:
                # A bind-mounted file cannot be renamed: overwrite it in place.
                self.in_place = self.path.read_bytes()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.source:
            shutil.copyfile(self.source, self.path)
        else:
            self.path.write_text(self.content)
            self.path.chmod(0o755)
        return self

    def __exit__(self, *exc):
        if self.in_place is not None:
            self.path.write_bytes(self.in_place)
            return False
        if self.path.exists() or self.path.is_symlink():
            self.path.unlink()
        if self.backup.exists() or self.backup.is_symlink():
            self.backup.rename(self.path)
        return False


def update(root, configuration, warn):
    if call(["apt-get", "update"], 900):
        warn("Could not refresh the package lists; keeping the packages from the installation media.")
        return
    libcalamares.job.setprogress(0.4)
    if call(["apt-get", "--fix-broken", "install"] + APT_OPTIONS, 0):
        warn("Could not repair package dependencies online.")
    libcalamares.job.setprogress(0.6)
    mode = configuration.get("upgrade", "safe")
    if mode in ("safe", "full"):
        command = "full-upgrade" if mode == "full" else "upgrade"
        extra = [] if mode == "full" else ["--with-new-pkgs"]
        # Download first: a slow line may be interrupted safely (the updates are
        # then skipped). Installing runs without a time limit, so dpkg is never
        # killed half-way.
        if call(["apt-get", "--download-only", command] + extra + APT_OPTIONS,
                int(configuration.get("downloadTimeout", 7200))):
            warn("Could not download all updates in time; the system keeps the packages from the installation "
                 "media. Run 'sudo apt upgrade' after installation.")
        elif call(["apt-get", "--no-download", command] + extra + APT_OPTIONS, 0):
            call(["dpkg", "--configure", "-a"], 0)
            warn("Could not install all updates; the system is complete but not fully up to date.")


def update_target():
    root = libcalamares.globalstorage.value("rootMountPoint")
    if not root or root == "/":
        return ("Invalid target", "Package checks require a mounted target system.")
    configuration = libcalamares.job.configuration
    warnings = []
    warn = warnings.append
    with TemporaryFile(Path(root) / "usr/sbin/policy-rc.d", POLICY):
        if call(["dpkg", "--configure", "-a"], 0):
            warn("Some packages could not be configured.")
        libcalamares.job.setprogress(0.2)
        url = configuration.get("checkUrl", "http://deb.debian.org/debian/")
        if configuration.get("useNetwork", True) and online(url):
            resolv = Path("/etc/resolv.conf")
            if resolv.exists():
                with TemporaryFile(Path(root) / "etc/resolv.conf", source=resolv):
                    update(root, configuration, warn)
            else:
                update(root, configuration, warn)
        else:
            libcalamares.utils.debug("Corry: offline, installing from the installation media only.")
            if call(["apt-get", "--fix-broken", "install", "--no-download"] + APT_OPTIONS, 0):
                warn("Broken packages could not be repaired offline; connect to the internet and run "
                     "'sudo apt --fix-broken install' after installation.")
        call(["apt-get", "clean"], 300)
    libcalamares.job.setprogress(1.0)
    for message in warnings:
        libcalamares.utils.warning("Corry: " + message)
    return None


def run():
    # Updates are optional: an unexpected error is reported, never fatal.
    try:
        return update_target()
    except Exception as exc:
        libcalamares.utils.warning("Corry: checking and updating packages stopped early ({}: {}); the system keeps "
                                   "the packages from the installation media.".format(type(exc).__name__, exc))
        return None
