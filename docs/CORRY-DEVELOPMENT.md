<!-- SPDX-License-Identifier: CC0-1.0 -->
# Corry 1.0 — integrating with Edukasaun OS and DebION GNU/Linux

Corry is a fork of Calamares 3.3.15: the installation engine is Calamares, the
Debian configuration is adapted from Catalyst, and the guided flow and slideshow
take inspiration from the Linux Mint Live Installer. The Catalyst configuration
snapshot and its ISC license are kept in `config/upstream/catalyst`. No logos or
images from the reference projects are copied.

The engine and the pages are C++ with Qt (Qt 6 in the Debian packages, Qt 5 for
local development builds); the header, side menu, slideshow and welcome card are
QML; the installation jobs Corry adds are Python 3 (the same job API as
Calamares' own Python modules); the launcher and packaging helpers are POSIX
shell. These are the languages Calamares itself uses, so every upstream module,
test tool and fix keeps working.

## Supported bases

| Base | Detected from `/etc/debian_version` | Qt | Distribution |
| --- | --- | --- | --- |
| Debian stable (13 "trixie") | `13`, `13.x` | 6 | Edukasaun OS (`corry-edukasaun`) |
| Debian testing | `14`, `14.x`, `forky/sid`, `…/sid` | 6 | DebION GNU/Linux (`corry-debion`) |

Any other base is refused. A derivative that rewrites `/etc/debian_version` sets
`CORRY_DEBIAN_BASE=stable` or `CORRY_DEBIAN_BASE=testing` when running
`install-dependencies.sh` and `build-corry.sh`. The profile's own base
(`debian:` in `distro.yaml`) decides which init systems and boot loaders are
offered.

## Install into an ISO root

Recommended: the Debian packages (see the README).

```bash
sudo sh install-corry-debs.sh edukasaun     # corry-edukasaun_1.0_amd64.deb, Debian stable chroot
sudo sh install-corry-debs.sh debion        # corry-debion_1.0_amd64.deb, Debian testing chroot
```

Each package ships the whole installer: `/usr/bin/calamares` (Corry engine),
private `libcalamares*`, modules, QML, `/usr/bin/corry-installer`,
`/usr/lib/corry/{preflight.py,remove-calamares,corry-desktop-icon,corry-session}`,
the polkit policy for `corry-session`, the APT hook, the autostart helper, and its
distribution's themed `/etc/calamares`, menu entry, icon and
`/usr/bin/install-debian` link. The two packages conflict with each other, with
Corry 0.1's `corry` and profile packages, and with Debian's `calamares` and
`calamares-settings-debian`, and replace all of them. When apt removes Calamares:

1. `postinst` runs `remove-calamares --leftovers` (deletes files Calamares left
   behind) and `corry-desktop-icon --all-users` (puts the shortcut on every user's
   desktop, executable and trusted, written by that user, and marks it done).
2. The APT hook runs `remove-calamares --purge-rc` after each later dpkg run and
   purges the removed packages' records.
3. Users created later get the shortcut once at their first login (XDG autostart).
4. `prerm` removes the shortcuts when the package is removed.

Script install for development:

```bash
sudo bash tools/install-dependencies.sh build
bash tools/build-corry.sh
sudo bash tools/install-corry.sh build-corry
sudo bash tools/install-profile.sh --distro edukasaun      # or debion, or --distro-dir PATH
```

These scripts purge Debian's Calamares first and record every installed file in
`/usr/lib/corry/manifest`. Branding and themes are described in
[BRANDING.md](BRANDING.md).

The ISO integrator still provides `/etc/os-release`, the kernel, firmware, desktop,
login manager, initramfs-tools, GRUB (`grub2-common`, `grub-pc-bin`,
`grub-efi-amd64-bin`) and the distribution's repositories and keyrings. Put
`grub-pc` and `grub-efi-amd64` (and `shim-signed`, `grub-efi-amd64-signed`) in the
ISO's package pool (`pool/`, `dists/`) so offline installs get the full boot loader
packages. The alternative init systems and boot loaders are always downloaded from
the repositories.

## Default installer

The packages provide an "Install <product>" menu entry, the `install-debian`
command, and a desktop icon that `corry-desktop-icon` copies to the live user's
desktop. Script installs instead hide leftover generic entries through
`/usr/local`; `install-profile.sh --autostart` also opens Corry at login.

The launcher starts in US English (`CORRY_LANG` overrides it), runs the preflight
check, then starts `corry-session` as root, which runs the engine **without** `-c`.
It prefers passwordless `sudo`, keeping the display and PulseAudio/PipeWire
environment so the background music plays and GParted can open; otherwise it uses
`pkexec` (with Corry's own polkit policy, which allows the graphical session).

### Exit codes and error messages

| Code | From | Meaning |
| --- | --- | --- |
| 0 | `corry-installer` | Installation finished or failed and the user closed Corry, or the user closed it earlier. |
| 1 | engine | The engine stopped with an error. |
| 2 | `corry-installer` | The preflight check failed: a missing dependency, live image, kernel, initramfs-tools or GRUB source, or a profile that is not Corry's. The reasons are printed, shown in a dialog and saved to `/tmp/Corry/preflight-error.log`. |
| 4 | `corry-installer` | `/usr/bin/calamares` is not installed. |
| 126, 127 | `pkexec` | Administrator rights were refused or could not be obtained (only when passwordless `sudo` is unavailable). |
| other | engine | The engine stopped unexpectedly (for example 139, a crash); its log is saved to `/tmp/Corry/crash-<date>.log`. |

### Logs

| File | Written | Contents |
| --- | --- | --- |
| `/tmp/Corry/install.log` | When the installation jobs end, failed or finished | A short report (Corry and Calamares versions, product, date, result, init system and boot loader with their messages, the error and its details) and the whole session log |
| `/tmp/Corry/install-<date>-<result>.log` | Same time | A dated copy, so a second attempt does not overwrite the first |
| `/tmp/Corry/crash-<date>.log` | The engine stopped unexpectedly | The session log up to that moment |
| `/tmp/Corry/preflight-error.log` | The preflight check failed | Why Corry could not start |
| `/root/.cache/calamares/session.log` | Always, live | The engine's own log; *Show details* on the install page shows it |

The files in `/tmp/Corry` belong to the user who started Corry (mode 0600, folder
0700), so they open in any text editor; the error dialog's **Open log** button and
the Finished page's **Open the installation log** button do that as that user. The
logs are written to a temporary file and renamed into place, so a planted link is
never followed. `/tmp` is in memory on a live system: copy the log before
restarting. Look for lines with `ERROR` or `WARNING`, and attach the file when
asking for help.

Job errors that stop an installation carry a title and a cause, for example
*Invalid target* (a job ran without a mounted target), *Boot loader files are
missing* (`corrygrub`: no GRUB in the image, pool or online, and the computer
cannot boot without it), *Bootloader installation error* (`grub-install` failed
even without an NVRAM entry). Everything else Corry adds is a **warning**, never an
error: updates, cleanup, the alternative init systems and boot loaders. The
installation continues with what works (systemd, GRUB, the packages from the
media) and the warning says why (`Corry: <name> was not installed: …`).

## Pages

| Step | Module | Notes |
| --- | --- | --- |
| Welcome | `welcome` (`corryPage: greeting`) | Greeting, language, the welcome image (`welcome-media.qml`); never blocks |
| System check | `welcome@check` (`welcomecheck.conf`) | Storage 20 GiB, RAM 1 GiB, root required; power, screen, internet shown; *Check again* |
| Location, Keyboard | `locale`, `keyboard` | Asia/Dili and English (US) preselected |
| Partitions | `partition` | Erase (Btrfs), manual with role buttons, *Open GParted*; EFI 300 MiB; LVM, LUKS and Windows data partitions allowed in manual mode |
| Users | `users` | Same or different administrator password; one-character minimum |
| Init system | `corrysystem@init` (`corrysystem-init.conf`) | systemd (default), SysVinit, OpenRC, runit |
| Boot loader | `corrysystem@bootloader` (`corrysystem-bootloader.conf`) | GRUB 2 (default), systemd-boot, rEFInd (stable only), Syslinux/EXTLINUX |
| Summary | `summary` | Final confirmation dialog before any disk change |
| Install | exec jobs | Slideshow, music, mute button, *Show details* |
| Finish | `finished` | Restart now (unchecked); *Open the installation log* |

Every page sits in a card (`Calamares::CorryCard`, drawn in
`ViewManager::corryPage`, colored by the theme); the heading of each page is
defined there as well. With the `left` layout the steps are a side menu
(`sidebar-left.qml`), with `top` a header with a timeline (`sidebar-top.qml`).

### Init system and Boot loader pages

Both pages are instances of the `corrysystem` module; `section:` says which one a
configuration is for, `base:` (written by `tools/corry-branding.py` from
`distro.yaml`) is the Debian base. The option marked `default: true` is what the
live image already has. Each alternative has `packages` and `availableOn` (the
bases whose archive has every package; CI checks this list with
`tools/ci/check-availability.py`), and a boot loader may be limited by `firmware`,
`filesystems` (of `/boot`), `secureBoot` and `needsSystemd`.

On every visit (and on *Check again*) a page re-reads the environment: internet,
firmware (also 32-bit UEFI), architecture, Secure Boot, GDM/GNOME Shell in the
image, os-prober's findings, the init choice of the previous page, and the planned
`/` and `/boot` (filesystem, encryption) that the Partitions page publishes as
`corryPlannedPartitions` when it is left. An option that cannot be used shows the
reason and cannot be chosen; a choice that becomes impossible falls back to the
default. Each page writes its section of
`corrySystem: {init: {id, name, packages, default}, bootloader: {…, filesystems}, online, base}`
in global storage; the Summary page shows both.

## Installation jobs

1. `partition`, `mount`, `unpackfs` (copies the live image), `machineid`, `fstab`
   (crypttab without a key script: the initramfs asks for the passphrase),
   `locale`, `keyboard`, `localecfg`, `users`, `displaymanager`, `networkcfg`, `hwclock`.
2. `corrycleanup`: marks the system's own tools (cryptsetup, lvm2, GRUB, sudo, …)
   as manually installed, purges `live-boot`/`live-config`, Corry and
   `calamares`/`calamares-settings-debian` with dpkg (one by one if dpkg refuses
   the set; no autoremove), deletes every path in the manifest and all launchers,
   removes the live account but never its home directory. Problems are warnings.
3. `corryupdate`: `dpkg --configure -a` always. When `internet-check-url` answers:
   `apt-get update`, `--fix-broken install`, then `upgrade --with-new-pkgs`
   (configurable: `safe`, `full`, `none`), downloaded first (`downloadTimeout`,
   default 2 h) and installed without a time limit. Offline:
   `--fix-broken install --no-download`. Uses a temporary `policy-rc.d` and DNS;
   never fails the installation.
4. `corryinit` (only for an alternative init system): refuses if GDM/GNOME is
   installed; `apt-get update`; simulates `apt-get install <packages>
   systemd-sysv- libpam-systemd- systemd- libnss-systemd-` (`--allow-remove-essential
   --no-install-recommends`) and refuses if anything outside systemd's own packages
   would be removed (`allowedRemovals` lists the exceptions); downloads, then
   installs; verifies that `/usr/sbin/init` is shipped by the new init package
   (`sysvinit-core`, also for OpenRC, or `runit-init`); purges systemd's packages
   when that removes nothing else. Any problem: a warning, systemd stays.
5. `corrygrub`: installs `grub-pc` (BIOS), `grub-efi-amd64` (UEFI) or
   `grub-efi-ia32` (32-bit UEFI) from the boot medium's pool, else online; with
   64-bit UEFI also `shim-signed` and `grub-efi-amd64-signed`. It always runs, so
   GRUB is available as the fallback.
6. `initramfs`.
7. `corrybootloader` (only for an alternative boot loader): checks firmware,
   32-bit UEFI, the ESP, the layout (filesystem and encryption of `/boot`;
   EXTLINUX also: compressed Btrfs, os-prober's systems, a logical partition,
   another active partition) and internet, all before downloading; downloads and
   installs the packages; installs the loader (systemd-boot: `bootctl` and
   `kernel-install`, or Corry's own entries and kernel hooks; rEFInd: copied to
   `EFI/refind` and `EFI/BOOT` with drivers, icons, `refind.conf` and
   `/boot/refind_linux.conf`; EXTLINUX: `extlinux.conf`, `extlinux --install`,
   MBR/GPT boot code, boot flag, kernel hooks); verifies; then purges GRUB's
   packages and removes `/boot/grub`, `/etc/default/grub` and `/etc/grub.d`. On
   an EFI partition formatted by this installation it also removes GRUB's EFI
   directory and this partition's GRUB entry; a reused EFI partition is left
   alone. On any failure the alternative is purged again (with the firmware
   entries it created) and the choice falls back to GRUB.
8. `grubcfg` (os-prober enabled) and `bootloader` (GRUB; EFI directory from
   `bootloader-name`, e.g. `EFI/debion`; the removable-media path gets the shim
   chain when Secure Boot packages are installed; retried with `--no-nvram` if
   the firmware refuses a boot entry) — skipped when an alternative loader is in
   place.
9. `umount`.

## Partitions and accounts

| Filesystem | Use |
| --- | --- |
| Btrfs | Default `/`; subvolumes `@`, `@home`, `@cache`, `@log`; zstd:1 compression |
| ext4 / XFS | Automatic and manual partitioning |
| FAT32 | EFI `/boot/efi`, 300 MiB recommended, 100 MiB minimum, boot/ESP flags |
| Swap | Virtual memory; no mount point |
| LVM PV, LUKS | Manual partitioning (volume groups, encrypted `/` and `/home`) |
| NTFS, exFAT | Existing Windows data partitions; mounted `nofail`, owned by the new user |

BIOS installs on an erased disk use MBR; UEFI installs use GPT. On a manual GPT
layout under BIOS, add a 1 MiB `bios_grub` partition (Calamares warns about it).
Editing an existing partition never turns on Format automatically. EXTLINUX needs an
ext4 or XFS `/boot` (it cannot read compressed Btrfs); rEFInd reads ext2/3/4 and
Btrfs; neither reads an encrypted `/boot`; systemd-boot keeps the kernels on the
EFI partition (about 100 MB each).

## Verification

`tools/test-profile.py` (57 tests) covers the Debian packaging, the workflows,
the `remove-calamares` and desktop-shortcut helpers, the logs in `/tmp/Corry`,
media size advice, themes (tokens, contrast) and derived accent shades, the module
schemas and job order, profile choices (EFI 300 MiB, root password, welcome pages,
os-prober, Asia/Dili, the Init system and Boot loader options per base), both
distribution profiles and the default-installer files, branding validation, the
new-distro tool, Debian base detection, live cleanup and complete self-removal,
GRUB package selection (pool, online, fallback, 32-bit UEFI), offline/online
package repair, the init switch (refusals, download first, switch, purge,
failures), every boot loader path (install, GRUB removal, reused ESP, unsuitable
layouts, fallback, unexpected errors, helpers) and the preflight image check
against a real squashfs. ctest: `corrysystemtest` (the pages' rules and the
planned layout) and `corrylogtest` (the saved log, link safety).

CI (`.github/workflows/corry.yml`):

| Job | What it proves |
| --- | --- |
| `package` (stable/Edukasaun, testing/DebION) | The packages build with all tests; installed over Debian's real Calamares, nothing of Calamares is left; the shortcut is there for the desktop user; the SVG plugin is installed; the installed Corry starts on Xvfb with every module and QML file loading; it purges completely; a failed `dpkg -i` is repaired |
| `init-switch` (both bases × SysVinit, OpenRC, runit) | Every offered package exists in the archive; with GDM the switch is refused; without it the real `corryinit` switches, `/usr/sbin/init` is the new init's, systemd is purged and the Xfce desktop stays complete |
| `e2e` (five scenarios) | `tools/ci/e2e-install.sh`: a small Debian live image is installed with the **packaged** job modules, in installer order (Calamares' `loadmodule`, global storage carried from job to job), into a disk image that is then **booted in QEMU** and must report its init and root filesystem: UEFI and BIOS, Btrfs and ext4, systemd and SysVinit, GRUB and systemd-boot |
| `release` | Only after all of the above, and only when the tag, `VERSION`, `debian/changelog` and `CHANGELOG-CORRY.md` agree |

The `Debian package probe` workflow (manual) prints the package relations the
design relies on.

`tools/screenshots/capture.sh BUILD DISTRO OUT` runs the real build on Xvfb and
saves every page. It uses a screenshot-only sequence without the partition step and
a demo job instead of the installation jobs, so nothing touches a disk. The
partition pages come from `tools/preview.py`.

## Before deploying on real hardware

The CI matrix covers the job chain and the boot of the installed disk in virtual
machines. On real computers, check at least once per distribution:

| Scenario | What must be shown |
| --- | --- |
| UEFI with Secure Boot on | Shim and signed GRUB start; the alternatives are refused on the page |
| Dual boot with Windows | os-prober entry in the GRUB menu; Windows still starts |
| Manual, GParted, existing `/home` | Data kept; EFI and boot loader on the right disk |
| Encrypted `/` | The passphrase prompt at boot; the system starts |
| OpenRC / runit installed | Desktop, network and sound work after the switch |
| rEFInd / EXTLINUX installed | The chosen menu appears; a kernel update keeps booting |
| Slow or no internet | Offline install completes; a slow online install is not interrupted |
| 1366×768 and HiDPI screens | Header or side menu, pages and dialogs usable |

See [RECOMMENDATIONS.md](RECOMMENDATIONS.md) for what is checked and what to add next.
