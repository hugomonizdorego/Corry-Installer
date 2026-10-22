<!-- SPDX-License-Identifier: CC0-1.0 -->
# Corry 0.2 — integrating with Edukasaun OS and DebION GNU/Linux

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
sudo apt install ./corry-edukasaun_0.2_amd64.deb      # Edukasaun OS, Debian stable chroot
sudo apt install ./corry-debion_0.2_amd64.deb         # DebION GNU/Linux, Debian testing chroot
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
offline installs get the full boot loader packages.

## Default installer

The packages provide an "Install <product>" menu entry, the `install-debian`
command, and a desktop icon that `corry-desktop-icon` copies to the live user's
desktop at login (only in a live session; Debian policy forbids packages in
`/etc/skel`). Script installs instead hide leftover generic entries through
`/usr/local`; `install-profile.sh --autostart` also opens Corry at login.

The launcher starts in US English (`CORRY_LANG` overrides it), runs the preflight
check, then starts the engine as root **without** `-c` (that option is for testing:
it makes the engine look for its QML files under `/etc/calamares` and fail to start). It prefers passwordless `sudo`, keeping the
display and PulseAudio/PipeWire environment so the background music plays and
GParted can open; otherwise it uses `pkexec`.

## Pages

| Step | Module | Notes |
| --- | --- | --- |
| Welcome | `welcome` (`corryPage: greeting`) | Greeting, language, video (`welcome-media.qml`); never blocks |
| System check | `welcome@check` (`welcomecheck.conf`) | Storage 20 GiB, RAM 1 GiB, root required; power, screen, internet shown; *Check again* |
| Location, Keyboard | `locale`, `keyboard` | Asia/Dili and English (US) preselected |
| Partitions | `partition` | Erase (Btrfs), manual with role buttons, *Open GParted*; EFI 300 MiB |
| Users | `users` | Same or different administrator password; one-character minimum |
| Summary | `summary` | Final confirmation dialog before any disk change |
| Install | exec jobs | Slideshow, music, mute button |
| Finish | `finished` | Restart now (unchecked) |

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
4. `corrygrub`: installs `grub-pc` (BIOS) or `grub-efi-amd64` (UEFI) from the boot
   medium's pool, else online; else continues with a warning if the GRUB files exist.
5. `initramfs`, `grubcfg` (os-prober enabled), `bootloader` (EFI directory `debian`
   plus the removable-media fallback), `umount`.

## Partitions and accounts

| Filesystem | Use |
| --- | --- |
| Btrfs | Default `/`; subvolumes `@`, `@home`, `@cache`, `@log`; zstd:1 compression |
| ext4 / XFS | Automatic and manual partitioning |
| FAT32 | EFI `/boot/efi`, 300 MiB recommended, 100 MiB minimum, boot/ESP flags |
| Swap | Virtual memory; no mount point |

BIOS installs on an erased disk use MBR; UEFI installs use GPT. On a manual GPT
layout under BIOS, add a 1 MiB `bios_grub` partition (Calamares warns about it).
Editing an existing partition never turns on Format automatically.

## Verification

`tools/test-profile.py` (20 tests) covers the Debian packaging, the
`remove-calamares` helper, media size advice, the module schemas and job order, profile
choices (EFI 300 MiB, root password, welcome pages, os-prober), both distribution
profiles and the default-installer files, branding validation, the new-distro tool,
Debian base detection, live cleanup and complete self-removal, GRUB package
selection (pool, online, fallback), offline/online package repair, and the
preflight image check against a real squashfs.

CI builds the packages on `debian:stable` and `debian:testing` (running all tests),
installs Debian's real Calamares packages, installs Corry over them, verifies that
nothing of Calamares is left, starts the installed Corry on Xvfb and checks it loads
`/etc/calamares`, `/usr/share/calamares/qml` and the Corry branding, switches the
profile, purges Corry and uploads the `.deb` files.

`tools/screenshots/capture.sh BUILD DISTRO OUT` runs the real build on Xvfb and
saves every page. It uses a screenshot-only sequence without the partition step and
a demo job instead of the installation jobs, so nothing touches a disk. The
partition pages come from `tools/preview.py`.

## Before a release

Complete this virtual-machine matrix for each distribution and each base:

| Scenario | What must be shown |
| --- | --- |
| UEFI + GPT / BIOS + MBR | Correct partitions, initramfs, GRUB, reboot and login |
| Offline / online | Offline install completes; online install also updates |
| Btrfs / ext4 / XFS | fstab correct and boot succeeds |
| Manual, GParted, existing `/home` | Data kept; EFI and boot loader on the right disk |
| Dual boot | os-prober entry in the GRUB menu |
| Same / different administrator password | `sudo` and `su` work as chosen after reboot |
| Installed system | No Corry/Calamares file, package, menu entry, icon or autostart |
| Music and video | Played in the live session; muted button works |
| 1024×768 / HiDPI | Header, pages and dialogs usable |

Secure Boot and full-disk encryption are not validated yet. See
[RECOMMENDATIONS.md](RECOMMENDATIONS.md) for what to add next.
