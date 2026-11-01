# SPDX-License-Identifier: GPL-3.0-or-later
"""Install the init system chosen on Corry's System page and retire systemd.

The live image starts with systemd, Debian's default. When another init system
was chosen, its packages are downloaded into the target. First apt's simulation
of the change is read: if anything but systemd's own packages would be removed
(for example GDM, which needs systemd), nothing is changed. Only then is the
switch made, /sbin/init is verified, and systemd is purged as far as the
dependencies allow, so that no second init system is left behind. Every problem
keeps systemd and becomes a warning: the installation always continues with a
system that boots.
"""
from pathlib import Path
import re
import shutil
import subprocess
import urllib.request
import libcalamares

# Debian testing marks systemd-sysv Essential: removing it needs the extra flag.
# Recommends are not installed; the option's package list names what is needed.
APT = ["env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "-y", "--allow-remove-essential",
       "--no-install-recommends", "-o", "Dpkg::Options::=--force-confdef", "-o", "Dpkg::Options::=--force-confold"]
POLICY = "#!/bin/sh\n# Temporary, written by Corry during installation.\nexit 101\n"
# Desktops that only work with systemd as PID 1; the System page hides the
# alternatives when they are present, and the job checks again.
NEEDS_SYSTEMD = ("gdm3", "gnome-shell", "gnome-session")
# systemd's own packages: the switch may remove these and nothing else. Debian's
# elogind conflicts with the systemd package itself, so the whole family goes.
SYSTEMD_FAMILY = ("systemd", "libsystemd", "libpam-systemd", "libnss-systemd")
DEFAULT_ALLOWED = ["dbus-user-session", "sysv-rc", "libpam-elogind-compat"]
# Asked to be removed explicitly: apt refuses to drop manually installed packages
# on its own, and the live image marks every package as manual.
DEFAULT_REMOVE = ["systemd-sysv", "libpam-systemd", "systemd", "libnss-systemd"]
DEFAULT_PURGE = ["systemd-sysv", "libpam-systemd", "systemd", "libnss-systemd", "systemd-timesyncd",
                 "systemd-resolved"]
# Set only by test harnesses that run the job against a container's own root.
ALLOW_LIVE_ROOT = False


def allowed_removal(package, allowed):
    return package in allowed or any(package == p or package.startswith(p + "-") for p in SYSTEMD_FAMILY) \
        or package.startswith("libsystemd")


def pretty_name():
    return "Install the chosen init system"


def online(url, timeout=10):
    try:
        with urllib.request.urlopen(url, timeout=timeout):
            return True
    except (OSError, ValueError):
        return False


class TemporaryFile:
    """Replace a target file for the duration of the job, then restore it."""

    def __init__(self, path, content=None, source=None):
        self.path, self.content, self.source = Path(path), content, source
        self.backup = self.path.with_name(self.path.name + ".corry-backup")

    def __enter__(self):
        if self.path.exists() or self.path.is_symlink():
            self.path.rename(self.backup)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.source:
            shutil.copyfile(self.source, self.path)
        else:
            self.path.write_text(self.content)
            self.path.chmod(0o755)
        return self

    def __exit__(self, *exc):
        if self.path.exists() or self.path.is_symlink():
            self.path.unlink()
        if self.backup.exists() or self.backup.is_symlink():
            self.backup.rename(self.path)
        return False


def call(args, timeout=1800):
    return libcalamares.utils.target_env_call(list(args), "", timeout)


def output(args, timeout=600):
    """stdout of a target command, or None when it fails."""
    try:
        return libcalamares.utils.target_env_process_output(list(args), None, "", timeout)
    except subprocess.CalledProcessError as exc:
        libcalamares.utils.debug("Corry: {} failed: {}".format(" ".join(args), exc.output))
        return None


LAST_APT_OUTPUT = ""


def plan(action, packages):
    """What apt would install and remove, as (installed, removed) sets; None if apt refuses."""
    global LAST_APT_OUTPUT
    try:
        text = libcalamares.utils.target_env_process_output(APT + ["-s", action] + list(packages), None, "", 600)
    except subprocess.CalledProcessError as exc:
        LAST_APT_OUTPUT = str(exc.output or "")
        libcalamares.utils.debug("Corry: apt-get -s {} refused: {}".format(action, LAST_APT_OUTPUT))
        return None
    LAST_APT_OUTPUT = text or ""
    installed = set(re.findall(r"^Inst (\S+)", text, re.M))
    removed = set(re.findall(r"^Remv (\S+)", text, re.M))
    return installed, removed


def apt_explanation():
    """The lines of apt's last refusal that name packages, for the warning."""
    lines = [l.strip() for l in LAST_APT_OUTPUT.splitlines() if l.strip().startswith(("E:", "1.", "2.", "3."))
             or "is selected" in l or "Depends:" in l or "Conflicts:" in l]
    return " ".join(lines[-4:])[:300]


def removal_markers(configuration, packages):
    """apt arguments asking for the removal of the packages the new init replaces."""
    markers = [p + "-" for p in configuration.get("remove", DEFAULT_REMOVE) if installed(p)]
    if "openrc" in packages and installed("sysv-rc"):
        markers.append("sysv-rc-")
    return markers


def installed(package):
    text = output(["dpkg-query", "-W", "-f=${db:Status-Abbrev}", package], 60)
    return bool(text) and text.startswith("ii")


def init_owner():
    """The package owning the init binary in the target."""
    path = (output(["readlink", "-f", "/sbin/init"], 60) or "/sbin/init").strip() or "/sbin/init"
    text = output(["dpkg-query", "-S", path], 60)
    if not text:
        return ""
    return text.split(":", 1)[0].strip()


def record(system, init, result, message):
    init = dict(init or {})
    init["installed"] = result
    init["message"] = message
    system = dict(system or {})
    system["init"] = init
    libcalamares.globalstorage.insert("corrySystem", system)


def switch(root, configuration, packages, warn):
    """Install the new init system; True when /sbin/init belongs to it."""
    allowed = set(configuration.get("allowedRemovals", DEFAULT_ALLOWED)) | set(packages)
    present = [p for p in configuration.get("needsSystemd", NEEDS_SYSTEMD) if installed(p)]
    if present:
        warn("{} need systemd".format(", ".join(present)))
        return False
    if call(["apt-get", "update"], 900):
        warn("the package lists could not be refreshed")
        return False
    libcalamares.job.setprogress(0.2)
    request = list(packages) + removal_markers(configuration, packages)
    simulated = plan("install", request)
    if simulated is None:
        warn("apt cannot install {}: {}".format(", ".join(packages), apt_explanation() or "unresolved dependencies"))
        return False
    blockers = sorted(p for p in simulated[1] if not allowed_removal(p, allowed))
    if blockers:
        libcalamares.utils.debug("Corry: apt would remove {}".format(sorted(simulated[1])))
        warn("it would remove {} (they need systemd)".format(", ".join(blockers)))
        return False
    libcalamares.utils.debug("Corry: switching init; apt will remove {}".format(sorted(simulated[1]) or "nothing"))
    if call(APT + ["install"] + request, 3600):
        warn("apt-get could not complete the installation")
        # Make sure the target still has a working init before continuing.
        call(APT + ["--fix-broken", "install"], 1800)
        if init_owner() != packages[0] and not installed("systemd-sysv"):
            call(APT + ["install", "systemd-sysv"], 1800)
        return False
    libcalamares.job.setprogress(0.6)
    owner = init_owner()
    if owner != packages[0]:
        warn("/sbin/init still belongs to {} after installing {}".format(owner or "an unknown package", packages[0]))
        return False
    return True


def retire_systemd(configuration, packages, warn):
    """Purge systemd's packages when that removes nothing else."""
    allowed = set(configuration.get("allowedRemovals", DEFAULT_ALLOWED)) | set(packages)
    candidates = [p for p in configuration.get("purge", DEFAULT_PURGE) if installed(p)]
    attempts = [candidates, [p for p in candidates if p != "systemd"], [p for p in candidates if p in ("systemd-sysv", "libpam-systemd")]]
    for attempt in attempts:
        if not attempt:
            continue
        simulated = plan("purge", attempt)
        if simulated is None or any(not allowed_removal(p, allowed) for p in simulated[1]):
            continue
        if call(APT + ["purge"] + attempt, 1800) == 0:
            kept = [p for p in candidates if p not in attempt]
            if kept:
                warn("{} stay installed (inactive) because other packages need them".format(", ".join(kept)))
            return attempt
    warn("systemd's packages stay installed (inactive) because other packages need them")
    return []


def run():
    root = libcalamares.globalstorage.value("rootMountPoint")
    if not root or (root == "/" and not ALLOW_LIVE_ROOT):
        return ("Invalid target", "The init system can only be changed in a mounted target system.")
    system = libcalamares.globalstorage.value("corrySystem") or {}
    init = system.get("init") or {}
    wanted = init.get("id", "systemd")
    packages = [str(p) for p in (init.get("packages") or [])]
    if init.get("default", wanted == "systemd") or not packages:
        libcalamares.utils.debug("Corry: keeping the image's init system (systemd).")
        return None
    name = init.get("name", wanted)
    configuration = libcalamares.job.configuration
    problems = []
    warn = problems.append
    url = configuration.get("checkUrl", "http://deb.debian.org/debian/")
    if not online(url):
        warn("the computer is offline and the packages cannot be downloaded")
    else:
        with TemporaryFile(Path(root) / "usr/sbin/policy-rc.d", POLICY):
            resolv = Path("/etc/resolv.conf")
            if resolv.exists():
                with TemporaryFile(Path(root) / "etc/resolv.conf", source=resolv):
                    done = switch(root, configuration, packages, warn)
                    if done:
                        purged = retire_systemd(configuration, packages, warn)
            else:
                done = switch(root, configuration, packages, warn)
                if done:
                    purged = retire_systemd(configuration, packages, warn)
            call(["apt-get", "clean"], 300)
        if done:
            message = "{} is the init system; removed: {}.".format(name, ", ".join(purged) if purged else "nothing")
            libcalamares.utils.debug("Corry: " + message)
            for problem in problems:
                libcalamares.utils.warning("Corry: {}: {}.".format(name, problem))
            record(system, init, wanted, message)
            libcalamares.job.setprogress(1.0)
            return None
    reason = "; ".join(problems) or "unknown problem"
    libcalamares.utils.warning("Corry: {} was not installed: {}. The system keeps systemd.".format(name, reason))
    record(system, init, "systemd", "{} not installed: {}".format(name, reason))
    libcalamares.job.setprogress(1.0)
    return None
