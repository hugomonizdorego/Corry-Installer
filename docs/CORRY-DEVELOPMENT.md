<!-- SPDX-License-Identifier: CC0-1.0 -->
# Corry 0.3 — integrating with Edukasaun OS and DebION GNU/Linux

Corry is in development. It is a fork of Calamares 3.3.15: the installation
engine is Calamares, the Debian configuration is adapted from Catalyst, and the
guided flow and slideshow take inspiration from the Linux Mint Live Installer.
The Catalyst configuration snapshot and its ISC license are kept in
`config/upstream/catalyst`. No logos or images from the reference projects are copied.

## Supported bases

| Base | Detected from `/etc/debian_version` | Qt |
| --- | --- | --- |
| Debian stable (13 "trixie") | `13`, `13.x` | 6 |
| Debian testing | `14`, `14.x`, `forky/sid`, `…/sid` | 6 |

Any other base is refused. A derivative that rewrites `/etc/debian_version` sets
`CORRY_DEBIAN_BASE=stable` or `CORRY_DEBIAN_BASE=testing` when running
`install-dependencies.sh` and `build-corry.sh`.

## Install into an ISO root

Recommended: the Debian packages (see the README).

```bash
sudo apt install ./corry-edukasaun_0.3_amd64.deb      # Edukasaun OS, Debian stable chroot
sudo apt install ./corry-debion_0.3_amd64.deb         # DebION GNU/Linux, Debian testing chroot
```

Each package ships the whole installer: `/usr/bin/calamares` (Corry engine),
private `libcalamares*`, modules, QML, `/usr/bin/corry-installer`,
`/usr/lib/corry/{preflight.py,remove-calamares,corry-desktop-icon}`, the APT hook,
the autostart helper, and its distribution's `/etc/calamares`, menu entry, icon and
`/usr/bin/install-debian` link. The two packages conflict with each other, with
Corry 0.1's `corry` and profile packages, and with Debian's `calamares` and
`calamares-settings-debian`, and replace all of them. When apt removes Calamares:

1. `postinst` runs `remove-calamares --leftovers` (deletes files Calamares left
   behind) and `corry-desktop-icon --all-users` (puts the shortcut on every user's
   desktop, executable and trusted, and marks it done for that user).
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
`/usr/lib/corry/manifest`. Branding is described in [BRANDING.md](BRANDING.md).

The ISO integrator still provides `/etc/os-release`, the kernel, firmware, desktop,
login manager, initramfs-tools, GRUB (`grub2-common`, `grub-pc-bin`,
`grub-efi-amd64-bin`) and the distribution's repositories and keyrings. Put
`grub-pc` and `grub-efi-amd64` in the ISO's package pool (`pool/`, `dists/`) so
offline installs get the full boot loader packages. The alternative init systems
and boot loaders are always downloaded from the repositories.

## Default installer

The packages provide an "Install <product>" menu entry, the `install-debian`
command, and a desktop icon that `corry-desktop-icon` copies to the live user's
desktop at login. Script installs instead hide leftover generic entries through
`/usr/local`; `install-profile.sh --autostart` also opens Corry at login.

The launcher starts in US English (`CORRY_LANG` overrides it), runs the preflight
check, then starts the engine as root **without** `-c`. It prefers passwordless
`sudo`, keeping the display and PulseAudio/PipeWire environment so the background
music plays and GParted can open; otherwise it uses `pkexec`.

### Exit codes and error messages

| Code | From | Meaning |
| --- | --- | --- |
| 0 | `corry-installer` | Installation finished, or the user closed Corry. |
| 1 | engine | The engine stopped with an error (the dialog and the log say which job). |
| 2 | `corry-installer` | The preflight check failed: a missing dependency, live image, kernel, initramfs-tools or GRUB source, or a profile that is not Corry's. The reasons are printed and shown in a dialog. |
| 4 | `corry-installer` | `/usr/bin/calamares` is not installed. |
| 126, 127 | `pkexec` | Administrator rights were refused or could not be obtained (only when passwordless `sudo` is unavailable). |

The log is `~/.cache/calamares/session.log` of the user who started Corry (or
`/root/.cache/calamares/` through `pkexec`); *Show details* on the install page shows
it live. Job errors that stop an installation carry a title and a cause, for
example *Invalid target* (a job ran without a mounted target), *Boot loader files
are missing* (`corrygrub`: no GRUB in the image, pool or online), *Could not remove
live-session packages* / *Could not remove the installer* (`corrycleanup`),
*Bootloader installation error* (`grub-install` failed). Everything about the
alternative init systems and boot loaders is a **warning**, never an error: the
installation continues with systemd and GRUB and the warning says why
(`Corry: <name> was not installed: …`).

## Pages

| Step | Module | Notes |
| --- | --- | --- |
| Welcome | `welcome` (`corryPage: greeting`) | Greeting, language, video (`welcome-media.qml`); never blocks |
| System check | `welcome@check` (`welcomecheck.conf`) | Storage 20 GiB, RAM 1 GiB, root required; power, screen, internet shown; *Check again* |
| Location, Keyboard | `locale`, `keyboard` | Asia/Dili and English (US) preselected |
| Partitions | `partition` | Erase (Btrfs), manual with role buttons, *Open GParted*; EFI 300 MiB |
| Users | `users` | Same or different administrator password; one-character minimum |
| System | `corrysystem` | Init system and boot loader; see below |
| Summary | `summary` | Final confirmation dialog before any disk change |
| Install | exec jobs | Slideshow, music, mute button, *Show details* |
| Finish | `finished` | Restart now (unchecked) |

Every page sits in a white card (`Calamares::CorryCard`, drawn in
`ViewManager::corryPage`); the heading of each page is defined there as well.

### System components page

`corrysystem.conf` lists the options; the first (or the one marked `default: true`)
is what the live image already has. Each alternative has `packages`, and may be
limited by `firmware`, `architectures`, `filesystems` (of `/boot`), `secureBoot`
and `needsSystemd`. On every visit (and on *Check again*) the page re-reads the
environment: internet, firmware, architecture, Secure Boot, GDM/GNOME Shell in the
image, and the planned partitions (from the Partitions page). An option that cannot
be used shows the reason and cannot be chosen; a choice that becomes impossible
falls back to the default. The selection is written to global storage as
`corrySystem: {init: {id, name, packages, default}, bootloader: {…}, online}` and
shown on the Summary page.

## Installation jobs

1. `partition`, `mount`, `unpackfs` (copies the live image), `machineid`, `fstab`,
   `locale`, `keyboard`, `localecfg`, `users`, `displaymanager`, `networkcfg`, `hwclock`.
2. `corrycleanup`: purges `live-boot`/`live-config` and `calamares`/`calamares-settings-debian`
   (no autoremove), deletes every path in the manifest and all launchers, removes the
   live account but never its home directory.
3. `corryupdate`: `dpkg --configure -a` always. When `internet-check-url` answers:
   `apt-get update`, `--fix-broken install`, `upgrade --with-new-pkgs` (configurable:
   `safe`, `full`, `none`). Offline: `--fix-broken install --no-download`. Uses a
   temporary `policy-rc.d` and DNS; never fails the installation.
4. `corryinit` (only for an alternative init system): refuses if GDM/GNOME is
   installed; `apt-get update`; simulates `apt-get install <packages>
   systemd-sysv- libpam-systemd- systemd- libnss-systemd-` (`--allow-remove-essential
   --no-install-recommends`) and refuses if anything outside systemd's own packages
   would be removed (`allowedRemovals` lists the exceptions); installs; verifies that
   `/sbin/init` belongs to the new package; purges systemd's packages when that
   removes nothing else. Any problem: a warning, systemd stays.
5. `corrygrub`: installs `grub-pc` (BIOS) or `grub-efi-amd64` (UEFI) from the boot
   medium's pool, else online; else continues with a warning if the GRUB files exist.
   It always runs, so GRUB is available as the fallback.
6. `initramfs`.
7. `corrybootloader` (only for an alternative boot loader): checks firmware, ESP,
   internet; installs the packages; installs the loader (systemd-boot: `bootctl` and
   `kernel-install`, or Corry's own entries and kernel hooks; rEFInd: copied to
   `EFI/refind` and `EFI/BOOT` with drivers, icons, `refind.conf` and
   `/boot/refind_linux.conf`; EXTLINUX: `extlinux.conf`, `extlinux --install`,
   MBR/GPT boot code, boot flag, kernel hooks; U-Boot: `/etc/default/u-boot` and
   `u-boot-update`); verifies; then purges GRUB's packages and removes `/boot/grub`,
   `/etc/default/grub`, `/etc/grub.d`, `EFI/debian` and GRUB's NVRAM entries. On any
   failure the alternative is purged again and the choice falls back to GRUB.
8. `grubcfg` (os-prober enabled) and `bootloader` (GRUB; EFI directory `debian` plus
   the removable-media fallback) — skipped when an alternative loader is in place.
9. `umount`.

## Partitions and accounts

| Filesystem | Use |
| --- | --- |
| Btrfs | Default `/`; subvolumes `@`, `@home`, `@cache`, `@log`; zstd:1 compression |
| ext4 / XFS | Automatic and manual partitioning |
| FAT32 | EFI `/boot/efi`, 300 MiB recommended, 100 MiB minimum, boot/ESP flags |
| Swap | Virtual memory; no mount point |

BIOS installs on an erased disk use MBR; UEFI installs use GPT. On a manual GPT
layout under BIOS, add a 1 MiB `bios_grub` partition (Calamares warns about it).
Editing an existing partition never turns on Format automatically. EXTLINUX needs an
ext4 or XFS `/boot` (it cannot read compressed Btrfs); rEFInd reads ext2/3/4 and
Btrfs; systemd-boot keeps the kernels on the EFI partition (about 100 MB each).

## Verification

`tools/test-profile.py` (45 tests) covers the Debian packaging, the
`remove-calamares` helper, media size advice, derived accent shades, the module
schemas and job order, profile choices (EFI 300 MiB, root password, welcome pages,
os-prober, Asia/Dili, the System page options), both distribution profiles and the
default-installer files, branding validation, the new-distro tool, Debian base
detection, live cleanup and complete self-removal, GRUB package selection (pool,
online, fallback), offline/online package repair, the init switch (refusals,
switch, purge, failures), every boot loader path (install, GRUB removal, fallback,
helpers) and the preflight image check against a real squashfs. `corrysystemtest`
(ctest) covers the compatibility rules of the System page.

CI builds the packages on `debian:stable` and `debian:testing` (running all tests),
installs Debian's real Calamares packages, installs Corry over them, verifies that
nothing of Calamares is left, starts the installed Corry on Xvfb, purges Corry and
uploads the `.deb` files. The `init-switch` job runs `corryinit` for real in both
containers through `tools/ci/run-job.py` (a stand-in for libcalamares): with GDM
installed the switch must be refused; without it `/sbin/init` must belong to
`sysvinit-core` and systemd must be gone. The `Debian package probe` workflow
(manual) prints the package relations the design relies on.

`tools/screenshots/capture.sh BUILD DISTRO OUT` runs the real build on Xvfb and
saves every page. It uses a screenshot-only sequence without the partition step and
a demo job instead of the installation jobs, so nothing touches a disk. The
partition pages come from `tools/preview.py`.

## Before a release

Complete this virtual-machine matrix for each distribution and each base:

| Scenario | What must be shown |
| --- | --- |
| UEFI + GPT / BIOS + MBR | Correct partitions, initramfs, boot loader, reboot and login |
| Offline / online | Offline install completes; online install also updates |
| Btrfs / ext4 / XFS | fstab correct and boot succeeds |
| Manual, GParted, existing `/home` | Data kept; EFI and boot loader on the right disk |
| Dual boot | os-prober entry in the GRUB menu |
| Same / different administrator password | `sudo` and `su` work as chosen after reboot |
| SysVinit / OpenRC / runit | `/sbin/init` is the chosen one, systemd purged, desktop and network work |
| systemd-boot / rEFInd / EXTLINUX | The chosen menu appears, GRUB is gone, a kernel update keeps booting |
| Installed system | No Corry/Calamares file, package, menu entry, icon or autostart |
| Music and video | Played in the live session; muted button works |
| 1024×768 / HiDPI | Header, pages and dialogs usable |

Secure Boot with the alternative loaders and full-disk encryption are not validated
yet. See [RECOMMENDATIONS.md](RECOMMENDATIONS.md) for what is checked and what to add next.
