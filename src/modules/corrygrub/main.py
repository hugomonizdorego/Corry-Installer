# SPDX-License-Identifier: GPL-3.0-or-later
"""Install the Debian GRUB package for the detected firmware into the target.

Live images usually ship only the grub-*-bin packages. The installed system also
needs grub-pc or grub-efi-<arch> so kernel and GRUB updates keep it bootable.
Packages come from the boot medium's package pool. When the pool lacks them
and the computer is online, the distribution's own repositories are used.
"""
from pathlib import Path
import shutil
import subprocess
import urllib.request
import libcalamares

EFI_PACKAGES = {"amd64": "grub-efi-amd64", "arm64": "grub-efi-arm64", "i386": "grub-efi-ia32"}
EFI_PLATFORMS = {"amd64": "x86_64-efi", "arm64": "arm64-efi", "i386": "i386-efi"}
MOUNT = "media/corry-medium"
APT_DIR = "var/lib/corry-apt"


def pretty_name():
    return "Install boot loader packages"


def wanted(firmware, arch):
    """Return the (package, GRUB platform directory) pair, or (None, None)."""
    if firmware == "efi":
        return EFI_PACKAGES.get(arch), EFI_PLATFORMS.get(arch)
    if arch in ("amd64", "i386"):
        return "grub-pc", "i386-pc"
    return None, None


def installed(root, package):
    try:
        status = (Path(root) / "var/lib/dpkg/status").read_text(errors="replace")
    except OSError:
        return False
    for entry in status.split("\n\n"):
        fields = dict(line.split(": ", 1) for line in entry.splitlines() if ": " in line and not line.startswith(" "))
        if fields.get("Package") == package and fields.get("Status") == "install ok installed":
            return True
    return False


def medium_sources(medium, package):
    """Return apt source lines for a Debian package pool on the boot medium."""
    medium = Path(medium)
    if not any((medium / "pool").glob("**/" + package + "_*.deb")):
        return []
    lines = []
    for suite in sorted((medium / "dists").iterdir()) if (medium / "dists").is_dir() else []:
        release = suite / "Release"
        if suite.is_symlink() or not release.is_file():
            continue
        components = ["main"]
        for line in release.read_text(errors="replace").splitlines():
            if line.startswith("Components:"):
                components = line.split(":", 1)[1].split() or components
        lines.append("deb [trusted=yes] file:/{} {} {}".format(MOUNT, suite.name, " ".join(components)))
    return lines


def apt(*args):
    options = ["-o", "Dir::Etc::SourceList=/{}/sources.list".format(APT_DIR),
               "-o", "Dir::Etc::SourceParts=/{}/parts".format(APT_DIR),
               "-o", "Dir::State::Lists=/{}/lists".format(APT_DIR),
               "-o", "APT::Get::List-Cleanup=0", "-o", "Acquire::Languages=none"]
    return libcalamares.utils.target_env_call(
        ["env", "DEBIAN_FRONTEND=noninteractive", "apt-get"] + options + list(args))


def install_from_medium(root, medium, sources, package):
    target = Path(root)
    mount_point = target / MOUNT
    state = target / APT_DIR
    mount_point.mkdir(parents=True, exist_ok=True)
    (state / "parts").mkdir(parents=True, exist_ok=True)
    (state / "lists/partial").mkdir(parents=True, exist_ok=True)
    (state / "sources.list").write_text("\n".join(sources) + "\n")
    if subprocess.run(["mount", "--bind", "-o", "ro", str(medium), str(mount_point)]).returncode:
        return "could not mount the boot medium"
    try:
        if apt("update"):
            return "the package index on the boot medium could not be read"
        if apt("-y", "--no-install-recommends", "install", package):
            return "apt-get could not install " + package
        return None
    finally:
        subprocess.run(["umount", "--lazy", str(mount_point)])
        shutil.rmtree(state, ignore_errors=True)
        try:
            mount_point.rmdir()
        except OSError:
            pass


def online(url):
    try:
        with urllib.request.urlopen(url, timeout=10):
            return True
    except (OSError, ValueError):
        return False


def install_from_network(root, package):
    """Use the target's own APT sources; DNS comes from the live session."""
    resolv = Path(root) / "etc/resolv.conf"
    backup = resolv.with_name("resolv.conf.corry-backup")
    if resolv.exists() or resolv.is_symlink():
        resolv.rename(backup)
    try:
        shutil.copyfile("/etc/resolv.conf", resolv)
        command = ["env", "DEBIAN_FRONTEND=noninteractive", "apt-get"]
        if libcalamares.utils.target_env_call(command + ["update"]):
            return "the package lists could not be refreshed"
        if libcalamares.utils.target_env_call(command + ["-y", "--no-install-recommends", "install", package]):
            return "apt-get could not download " + package
        return None
    except OSError as exc:
        return str(exc)
    finally:
        if resolv.exists() or resolv.is_symlink():
            resolv.unlink()
        if backup.exists() or backup.is_symlink():
            backup.rename(resolv)


def run():
    root = libcalamares.globalstorage.value("rootMountPoint")
    if not root or root == "/":
        return ("Invalid target", "The boot loader packages require a mounted target system.")
    firmware = libcalamares.globalstorage.value("firmwareType")
    arch = subprocess.run(["dpkg", "--print-architecture"], stdout=subprocess.PIPE,
                          text=True).stdout.strip()
    package, platform = wanted(firmware, arch)
    if not package:
        libcalamares.utils.warning("No GRUB package is known for {} on {}.".format(firmware, arch))
        return None
    if installed(root, package):
        return None
    medium = libcalamares.job.configuration.get("medium", "/run/live/medium")
    sources = medium_sources(medium, package)
    problem = install_from_medium(root, medium, sources, package) if sources else \
        "{} is not in the package pool of the boot medium".format(package)
    if problem is None:
        return None
    url = libcalamares.job.configuration.get("checkUrl", "http://deb.debian.org/debian/")
    if online(url):
        network_problem = install_from_network(root, package)
        if network_problem is None:
            return None
        problem += "; online: " + network_problem
    # grub-install only needs the platform files. Without the package the system
    # still boots, but GRUB is not updated automatically. Warn instead of failing.
    if (Path(root) / "usr/lib/grub" / platform).is_dir():
        libcalamares.utils.warning("Continuing without {}: {}.".format(package, problem))
        return None
    return ("Boot loader files are missing",
            "The installed system has no GRUB files for {} and {}. "
            "Add {} or its -bin package to the live image.".format(platform, problem, package))
