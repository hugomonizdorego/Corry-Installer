# SPDX-License-Identifier: GPL-3.0-or-later
"""Install the boot loader chosen on Corry's System page instead of GRUB.

GRUB is the default and is installed by the usual bootloader module. When the
user chose systemd-boot, rEFInd, EXTLINUX or U-Boot's menu, this job runs
before grubcfg/bootloader: it downloads the packages into the target, installs
and checks the loader, and then purges GRUB and its files so that only one
boot loader remains. Should any step fail, the choice falls back to GRUB (the
bootloader module then installs it) with a warning that says why. The
installed system always has a boot loader.
"""
from pathlib import Path
import os
import re
import shutil
import subprocess
import urllib.request
import libcalamares

APT = ["env", "DEBIAN_FRONTEND=noninteractive", "apt-get", "-y",
       "-o", "Dpkg::Options::=--force-confdef", "-o", "Dpkg::Options::=--force-confold"]
POLICY = "#!/bin/sh\n# Temporary, written by Corry during installation.\nexit 101\n"
DEFAULT_GRUB_PACKAGES = ["grub-pc", "grub-pc-bin", "grub-efi-amd64", "grub-efi-amd64-bin", "grub-efi-amd64-signed",
                         "grub-efi-ia32-bin", "grub-efi-arm64", "grub-efi-arm64-bin", "grub2-common", "grub-common",
                         "shim-signed", "shim-signed-common", "shim-helpers-amd64-signed"]
# EFI binary names per Debian architecture: (loader suffix, removable-media name).
EFI_NAMES = {"amd64": ("x64", "BOOTX64.EFI"), "arm64": ("aa64", "BOOTAA64.EFI"), "i386": ("ia32", "BOOTIA32.EFI")}
HOOK_HEADER = "#!/bin/sh\n# Written by Corry Installer: keeps the boot loader's kernel list current.\nset -e\n"
# Set only by test harnesses that run the job against a container's own root.
ALLOW_LIVE_ROOT = False


def pretty_name():
    return "Install the chosen boot loader"


# --- small helpers ---------------------------------------------------------

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
        self.in_place = None
        if self.path.exists() or self.path.is_symlink():
            try:
                self.path.rename(self.backup)
            except OSError:
                # A bind-mounted file (containers) cannot be renamed: keep its
                # content and overwrite it in place instead.
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


def call(args, timeout=1800):
    return libcalamares.utils.target_env_call(list(args), "", timeout)


def output(args, timeout=600):
    try:
        return libcalamares.utils.target_env_process_output(list(args), None, "", timeout)
    except subprocess.CalledProcessError as exc:
        libcalamares.utils.debug("Corry: {} failed: {}".format(" ".join(args), exc.output))
        return None


def host(args, timeout=120):
    """Run a command in the live system (for efibootmgr and parted on real devices)."""
    try:
        return subprocess.run(list(args), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                              timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        libcalamares.utils.debug("Corry: {} failed: {}".format(" ".join(args), exc))
        return None


def installed(package):
    text = output(["dpkg-query", "-W", "-f=${db:Status-Abbrev}", package], 60)
    return bool(text) and text.startswith("ii")


def architecture():
    text = output(["dpkg", "--print-architecture"], 60)
    return (text or "amd64").strip()


# --- what to boot ----------------------------------------------------------

def partitions():
    return libcalamares.globalstorage.value("partitions") or []

def partition_at(mount_point):
    for partition in partitions():
        if partition.get("mountPoint") == mount_point:
            return partition
    return None


def kernel_params(configuration):
    """Kernel command line for the new system, as the bootloader module builds it."""
    params = list(configuration.get("kernelParams", ["quiet"]))
    root = partition_at("/")
    if root is None:
        return None
    if "luksMapperName" in root:
        params.append("root=/dev/mapper/" + root["luksMapperName"])
    else:
        params.append("root=UUID=" + root["uuid"])
    if root.get("fs") == "btrfs":
        subvolume = libcalamares.globalstorage.value("btrfsRootSubvolume")
        if subvolume:
            params.append("rootflags=subvol=" + subvolume)
    for partition in partitions():
        if partition.get("fs") == "linuxswap" and partition.get("claimed", True) and "luksMapperName" not in partition:
            params.append("resume=UUID=" + partition["uuid"])
            break
    params.append("rw")
    return " ".join(params)


def kernels(root):
    """Installed kernels, newest first: (version, vmlinuz, initrd) paths relative to the target."""
    found = []
    for vmlinuz in Path(root, "boot").glob("vmlinuz-*"):
        version = vmlinuz.name[len("vmlinuz-"):]
        initrd = vmlinuz.with_name("initrd.img-" + version)
        found.append((version, "/boot/" + vmlinuz.name, "/boot/" + initrd.name if initrd.exists() else ""))
    return sorted(found, key=lambda k: version_key(k[0]), reverse=True)


def version_key(version):
    return [int(part) if part.isdigit() else part for part in re.split(r"[.\-+~]", version)]


def disk_of(device):
    """(disk, partition number) for /dev/sda3, /dev/nvme0n1p2, /dev/mmcblk0p1."""
    match = re.match(r"^(.*?)(p?)(\d+)$", device)
    if not match:
        return None, None
    base, p, number = match.groups()
    if p and not re.search(r"\d$", base):
        base += p
    return base, int(number)


def partition_table(disk):
    result = host(["blkid", "-p", "-s", "PTTYPE", "-o", "value", disk])
    return (result.stdout.strip() if result and result.returncode == 0 else "") or "unknown"


def esp_path():
    return libcalamares.globalstorage.value("efiSystemPartition") or "/boot/efi"


def free_megabytes(path):
    try:
        usage = shutil.disk_usage(path)
        return usage.free // (1024 * 1024)
    except OSError:
        return 0


def write(path, content, mode=0o644):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)
    path.chmod(mode)


def boot_menu_entries(product, cmdline, kernel_list, prefix):
    """EXTLINUX / U-Boot style menu: one LABEL per kernel, newest first."""
    lines = ["# Written by Corry Installer; regenerated by /etc/kernel/postinst.d/zz-corry-extlinux.",
             "DEFAULT linux-0", "TIMEOUT {}".format(int(TIMEOUT) * 10), "PROMPT 0", ""]
    for index, (version, vmlinuz, initrd) in enumerate(kernel_list):
        lines += ["LABEL linux-{}".format(index), "  MENU LABEL {} ({})".format(product, version),
                  "  LINUX {}{}".format(prefix, vmlinuz[len("/boot"):])]
        if initrd:
            lines.append("  INITRD {}{}".format(prefix, initrd[len("/boot"):]))
        lines += ["  APPEND {}".format(cmdline), ""]
    return "\n".join(lines)


TIMEOUT = 5


# --- the loaders -------------------------------------------------------------

def efi_variables_entry(label, disk, number, loader_path):
    """Best effort NVRAM entry; the removable-media copy covers firmware that ignores it."""
    if not disk or not number:
        return
    host(["efibootmgr", "-c", "-w", "-d", disk, "-p", str(number), "-L", label, "-l", loader_path])


def remove_efi_entries(matching):
    """Delete NVRAM entries whose loader path or label contains @p matching (case-insensitive)."""
    listing = host(["efibootmgr", "-v"])
    if not listing:
        return
    for line in listing.stdout.splitlines():
        match = re.match(r"^Boot([0-9A-Fa-f]{4})\*?\s+(.*)$", line)
        if match and matching.lower() in match.group(2).lower():
            host(["efibootmgr", "-b", match.group(1), "-B"])


def install_systemd_boot(root, configuration, cmdline, product, arch, problems):
    esp = esp_path()
    esp_dir = Path(root + esp)
    if free_megabytes(esp_dir) < 120:
        problems.append("the EFI partition has less than 120 MB free; systemd-boot keeps the kernels there")
        return False
    write(Path(root, "etc/kernel/cmdline"), cmdline + "\n")
    if call(["bootctl", "--esp-path=" + esp, "--graceful", "install"], 300):
        if call(["bootctl", "--esp-path=" + esp, "--no-variables", "install"], 300):
            problems.append("bootctl could not install systemd-boot")
            return False
        esp_partition = partition_at(esp) or {}
        disk, number = disk_of(esp_partition.get("device", ""))
        suffix = EFI_NAMES.get(arch, EFI_NAMES["amd64"])[0]
        efi_variables_entry("Linux Boot Manager", disk, number, "\\EFI\\systemd\\systemd-boot{}.efi".format(suffix))
    write(esp_dir / "loader/loader.conf", "timeout {}\nconsole-mode keep\neditor no\n".format(TIMEOUT))
    (esp_dir / "loader/entries").mkdir(parents=True, exist_ok=True)
    machine_id = Path(root, "etc/machine-id").read_text().strip() if Path(root, "etc/machine-id").exists() else "corry"
    kernel_list = kernels(root)
    if not kernel_list:
        problems.append("no kernel found in /boot")
        return False
    have_kernel_install = call(["sh", "-c", "command -v kernel-install >/dev/null"], 30) == 0
    if have_kernel_install:
        for version, vmlinuz, initrd in kernel_list:
            if call(["kernel-install", "add", version, vmlinuz] + ([initrd] if initrd else []), 600):
                have_kernel_install = False
                break
    if not have_kernel_install:
        # Without systemd's kernel-install (another init system was chosen):
        # copy kernels ourselves and keep doing so from a kernel hook.
        for version, vmlinuz, initrd in kernel_list:
            target_dir = esp_dir / machine_id / version
            target_dir.mkdir(parents=True, exist_ok=True)
            shutil.copy2(Path(root + vmlinuz), target_dir / "linux")
            if initrd:
                shutil.copy2(Path(root + initrd), target_dir / "initrd")
            entry = ["title {}".format(product), "version {}".format(version), "machine-id {}".format(machine_id),
                     "linux /{}/{}/linux".format(machine_id, version)]
            if initrd:
                entry.append("initrd /{}/{}/initrd".format(machine_id, version))
            entry.append("options {}".format(cmdline))
            write(esp_dir / "loader/entries/{}-{}.conf".format(machine_id, version), "\n".join(entry) + "\n")
        hook = HOOK_HEADER + """version="$1"
esp={esp}
id={machine_id}
[ -n "$version" ] || exit 0
mkdir -p "$esp/$id/$version"
cp -f "/boot/vmlinuz-$version" "$esp/$id/$version/linux"
[ ! -f "/boot/initrd.img-$version" ] || cp -f "/boot/initrd.img-$version" "$esp/$id/$version/initrd"
cat > "$esp/loader/entries/$id-$version.conf" <<EOF
title {product}
version $version
machine-id $id
linux /$id/$version/linux
initrd /$id/$version/initrd
options $(cat /etc/kernel/cmdline)
EOF
""".format(esp=esp, machine_id=machine_id, product=product)
        write(Path(root, "etc/kernel/postinst.d/zz-corry-systemd-boot"), hook, 0o755)
        write(Path(root, "etc/initramfs/post-update.d/zz-corry-systemd-boot"), hook, 0o755)
        write(Path(root, "etc/kernel/postrm.d/zz-corry-systemd-boot"), HOOK_HEADER
              + 'rm -rf "{esp}/{id}/$1" "{esp}/loader/entries/{id}-$1.conf"\n'.format(esp=esp, id=machine_id), 0o755)
    suffix = EFI_NAMES.get(arch, EFI_NAMES["amd64"])[0]
    loader = esp_dir / "EFI/systemd/systemd-boot{}.efi".format(suffix)
    if not loader.exists() or not any((esp_dir / "loader/entries").glob("*.conf")):
        problems.append("systemd-boot's files are missing on the EFI partition after installation")
        return False
    return True


def install_refind(root, configuration, cmdline, product, arch, problems):
    """Copy rEFInd to EFI/refind and to the removable-media path; write its configuration."""
    esp = esp_path()
    esp_dir = Path(root + esp)
    suffix, removable = EFI_NAMES.get(arch, EFI_NAMES["amd64"])
    share = Path(root, "usr/share/refind/refind")
    binary = share / "refind_{}.efi".format(suffix)
    if not binary.exists():
        problems.append("the refind package has no {}".format(binary.name))
        return False
    boot_fs = (partition_at("/boot") or partition_at("/") or {}).get("fs", "")
    drivers = [d for d in ("ext4", "ext2", "btrfs") if d == boot_fs or (boot_fs == "ext3" and d == "ext4")]
    conf = "\n".join(["# Written by Corry Installer.", "timeout {}".format(TIMEOUT), "use_graphics_for linux",
                      "scanfor internal,external,optical,manual", "fold_linux_kernels true",
                      "extra_kernel_version_strings linux", 'default_selection "vmlinuz"', ""])
    for destination, name in ((esp_dir / "EFI/refind", "refind_{}.efi".format(suffix)), (esp_dir / "EFI/BOOT", removable)):
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copy2(binary, destination / name)
        for driver in drivers:
            source = share / "drivers_{}".format(suffix) / "{}_{}.efi".format(driver, suffix)
            if source.exists():
                (destination / "drivers_{}".format(suffix)).mkdir(exist_ok=True)
                shutil.copy2(source, destination / "drivers_{}".format(suffix) / source.name)
        if (share / "icons").is_dir():
            shutil.copytree(share / "icons", destination / "icons", dirs_exist_ok=True)
        write(destination / "refind.conf", conf)
    write(Path(root, "boot/refind_linux.conf"),
          '"Boot with standard options"  "{0}"\n"Boot to single-user mode"    "{0} single"\n'
          '"Boot with minimal options"   "ro root={1}"\n'.format(cmdline, cmdline.split("root=", 1)[1].split()[0]))
    esp_partition = partition_at(esp) or {}
    disk, number = disk_of(esp_partition.get("device", ""))
    remove_efi_entries("refind")
    efi_variables_entry("rEFInd Boot Manager", disk, number, "\\EFI\\refind\\refind_{}.efi".format(suffix))
    if not kernels(root):
        problems.append("no kernel found in /boot")
        return False
    return True


def install_extlinux(root, configuration, cmdline, product, arch, problems):
    boot = partition_at("/boot")
    prefix = "" if boot else "/boot"
    target = boot or partition_at("/")
    if not target:
        problems.append("no root partition is known")
        return False
    disk, number = disk_of(target.get("device", ""))
    if not disk:
        problems.append("cannot tell which disk holds {}".format(target.get("device", "/boot")))
        return False
    kernel_list = kernels(root)
    if not kernel_list:
        problems.append("no kernel found in /boot")
        return False
    directory = Path(root, "boot/extlinux")
    directory.mkdir(parents=True, exist_ok=True)
    write(directory / "extlinux.conf", boot_menu_entries(product, cmdline, kernel_list, prefix))
    hook = HOOK_HEADER + """# Rewrite /boot/extlinux/extlinux.conf from the kernels in /boot.
conf=/boot/extlinux/extlinux.conf
prefix={prefix}
cmdline='{cmdline}'
{{
  echo '# Written by Corry Installer; regenerated by /etc/kernel/postinst.d/zz-corry-extlinux.'
  echo 'DEFAULT linux-0'; echo 'TIMEOUT {timeout}'; echo 'PROMPT 0'; echo
  i=0
  for k in $(ls -1 /boot/vmlinuz-* 2>/dev/null | sed 's|/boot/vmlinuz-||' | sort -V -r); do
    echo "LABEL linux-$i"; echo "  MENU LABEL {product} ($k)"; echo "  LINUX $prefix/vmlinuz-$k"
    [ ! -f "/boot/initrd.img-$k" ] || echo "  INITRD $prefix/initrd.img-$k"
    echo "  APPEND $cmdline"; echo
    i=$((i + 1))
  done
}} > "$conf.new" && mv "$conf.new" "$conf"
""".format(prefix=prefix, cmdline=cmdline.replace("'", "'\\''"), timeout=int(TIMEOUT) * 10, product=product)
    for path in ("etc/kernel/postinst.d/zz-corry-extlinux", "etc/kernel/postrm.d/zz-corry-extlinux",
                 "etc/initramfs/post-update.d/zz-corry-extlinux"):
        write(Path(root, path), hook, 0o755)
    if call(["extlinux", "--install", "/boot/extlinux"], 120):
        problems.append("extlinux --install failed (is /boot on ext4 or XFS?)")
        return False
    table = partition_table(disk)
    mbr_name = "gptmbr.bin" if table == "gpt" else "mbr.bin"
    mbr = next((p for p in (Path(root, "usr/lib/EXTLINUX", mbr_name), Path(root, "usr/lib/syslinux/mbr", mbr_name))
                if p.exists()), None)
    if mbr is None:
        problems.append("the extlinux package has no " + mbr_name)
        return False
    result = host(["dd", "if=" + str(mbr), "of=" + disk, "bs=440", "count=1", "conv=notrunc"])
    if result is None or result.returncode:
        problems.append("could not write the master boot record of " + disk)
        return False
    flag = "legacy_boot" if table == "gpt" else "boot"
    result = host(["parted", "-s", disk, "set", str(number), flag, "on"])
    if result is None or result.returncode:
        problems.append("could not set the {} flag on partition {} of {}".format(flag, number, disk))
        return False
    if not (directory / "ldlinux.sys").exists():
        problems.append("ldlinux.sys is missing after extlinux --install")
        return False
    return True


def install_uboot(root, configuration, cmdline, product, arch, problems):
    cmdline_without_root = " ".join(p for p in cmdline.split() if not p.startswith("root="))
    root_param = next((p for p in cmdline.split() if p.startswith("root=")), "")
    write(Path(root, "etc/default/u-boot"),
          '# Written by Corry Installer; read by u-boot-update.\nU_BOOT_MENU_LABEL="{}"\n'
          'U_BOOT_PARAMETERS="{}"\nU_BOOT_ROOT="{}"\nU_BOOT_TIMEOUT="{}"\n'.format(product, cmdline_without_root, root_param,
                                                                                int(TIMEOUT) * 10))
    if call(["u-boot-update"], 300):
        problems.append("u-boot-update failed")
        return False
    if not Path(root, "boot/extlinux/extlinux.conf").exists():
        problems.append("u-boot-update wrote no /boot/extlinux/extlinux.conf")
        return False
    return True


INSTALLERS = {"systemd-boot": install_systemd_boot, "refind": install_refind, "extlinux": install_extlinux,
              "uboot": install_uboot}


# --- GRUB removal ------------------------------------------------------------

def is_grub_binary(path):
    try:
        data = Path(path).read_bytes()
    except OSError:
        return False
    return b"GRUB" in data or b"grub" in data[:4096] or b"shim" in data[:65536]


def remove_grub(root, configuration, firmware, problems):
    """Purge GRUB's packages and delete what they leave in /boot and on the EFI partition."""
    packages = [p for p in configuration.get("grubPackages", DEFAULT_GRUB_PACKAGES) if installed(p)]
    if packages and call(APT + ["purge"] + packages, 1800):
        problems.append("GRUB's packages could not be purged: " + ", ".join(packages))
    for relative in ("boot/grub", "etc/default/grub", "etc/default/grub.d", "etc/grub.d"):
        path = Path(root, relative)
        if path.is_dir() and not path.is_symlink():
            shutil.rmtree(path, ignore_errors=True)
        elif path.exists():
            path.unlink()
    if firmware == "efi":
        esp_dir = Path(root + esp_path())
        label = configuration.get("grubEfiDirectory", "debian")
        for candidate in esp_dir.glob("EFI/*"):
            if candidate.name.lower() == label.lower() and candidate.is_dir():
                shutil.rmtree(candidate, ignore_errors=True)
        for candidate in esp_dir.glob("EFI/[Bb][Oo][Oo][Tt]/*.[Ee][Ff][Ii]"):
            if is_grub_binary(candidate) and b"systemd" not in candidate.read_bytes()[:200000] \
                    and b"rEFInd" not in candidate.read_bytes()[:200000]:
                candidate.unlink()
        for candidate in esp_dir.glob("EFI/[Bb][Oo][Oo][Tt]/fbx64.efi"):
            candidate.unlink()
        remove_efi_entries("\\EFI\\{}\\".format(label))
    return packages


def record(system, loader, result, message):
    loader = dict(loader or {})
    loader["id"] = result
    loader["message"] = message
    system = dict(system or {})
    system["bootloader"] = loader
    libcalamares.globalstorage.insert("corrySystem", system)


# --- the job -----------------------------------------------------------------

def run():
    global TIMEOUT
    root = libcalamares.globalstorage.value("rootMountPoint")
    if not root or (root == "/" and not ALLOW_LIVE_ROOT):
        return ("Invalid target", "The boot loader can only be installed into a mounted target system.")
    system = libcalamares.globalstorage.value("corrySystem") or {}
    loader = system.get("bootloader") or {}
    wanted = loader.get("id", "grub")
    if wanted == "grub" or loader.get("default", False):
        libcalamares.utils.debug("Corry: GRUB stays the boot loader.")
        return None
    name = loader.get("name", wanted)
    configuration = libcalamares.job.configuration
    TIMEOUT = int(configuration.get("timeout", 5))
    firmware = libcalamares.globalstorage.value("firmwareType") or "bios"
    branding = libcalamares.globalstorage.value("branding") or {}
    product = branding.get("bootloaderEntryName") or branding.get("productName") or "Linux"
    problems = []
    installer = INSTALLERS.get(wanted)
    cmdline = kernel_params(configuration)
    packages = [str(p) for p in (loader.get("packages") or [])]
    done = False
    if installer is None:
        problems.append("Corry does not know how to install '{}'".format(wanted))
    elif cmdline is None:
        problems.append("no root partition is known")
    elif wanted in ("systemd-boot", "refind") and firmware != "efi":
        problems.append("{} needs UEFI; this computer started in BIOS mode".format(name))
    elif wanted == "extlinux" and firmware == "efi":
        problems.append("EXTLINUX is a BIOS boot loader; this computer started with UEFI")
    elif firmware == "efi" and not partition_at(esp_path()):
        problems.append("no EFI system partition is mounted on " + esp_path())
    elif not online(configuration.get("checkUrl", "http://deb.debian.org/debian/")):
        problems.append("the computer is offline and the packages cannot be downloaded")
    else:
        arch = architecture()
        with TemporaryFile(Path(root) / "usr/sbin/policy-rc.d", POLICY):
            resolv = Path("/etc/resolv.conf")
            keep_dns = TemporaryFile(Path(root) / "etc/resolv.conf", source=resolv) if resolv.exists() and root != "/" else None
            if keep_dns:
                keep_dns.__enter__()
            try:
                if wanted == "refind":
                    call(["sh", "-c", "echo 'refind refind/install_to_esp boolean false' | debconf-set-selections"], 60)
                if call(["apt-get", "update"], 900):
                    problems.append("the package lists could not be refreshed")
                elif packages and call(APT + ["--no-install-recommends", "install"] + packages, 1800):
                    problems.append("apt-get could not install " + ", ".join(packages))
                else:
                    libcalamares.job.setprogress(0.4)
                    try:
                        done = installer(root, configuration, cmdline, product, arch, problems)
                    except (OSError, ValueError, KeyError) as exc:
                        problems.append("{}: {}".format(type(exc).__name__, exc))
                        done = False
                    if done:
                        libcalamares.job.setprogress(0.7)
                        purged = remove_grub(root, configuration, firmware, problems)
                        if wanted == "systemd-boot":
                            # Debian's systemd-boot package adds signed shim + signed
                            # systemd-boot to the ESP once signed GRUB is gone (best effort).
                            call(["dpkg-reconfigure", "-fnoninteractive", "systemd-boot"], 300)
                    elif packages:
                        # Leave no half-installed alternative next to GRUB.
                        call(APT + ["purge"] + [p for p in packages if installed(p)], 1800)
                        remove_efi_entries(name)
                call(["apt-get", "clean"], 300)
            finally:
                if keep_dns:
                    keep_dns.__exit__(None, None, None)
    libcalamares.job.setprogress(1.0)
    if done:
        message = "{} installed; GRUB removed ({}).".format(name, ", ".join(purged) if purged else "no packages")
        libcalamares.utils.debug("Corry: " + message)
        for problem in problems:
            libcalamares.utils.warning("Corry: {}: {}.".format(name, problem))
        record(system, loader, wanted, message)
        return None
    reason = "; ".join(problems) or "unknown problem"
    libcalamares.utils.warning("Corry: {} was not installed: {}. GRUB is installed instead.".format(name, reason))
    record(system, loader, "grub", "{} not installed: {}".format(name, reason))
    return None
