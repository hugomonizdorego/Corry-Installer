<!-- SPDX-License-Identifier: CC0-1.0 -->
# Corry — integrating with Edukasaun OS and DebION GNU/Linux

Corry is in development. It is an early fork of Calamares 3.3.15: the
installation engine is Calamares, the Debian configuration is adapted from
Catalyst, and the guided flow and slideshow take inspiration from the Linux Mint
Live Installer. The Catalyst configuration snapshot and its ISC license are kept
in `config/upstream/catalyst`. No logos or images from the reference projects are
copied.

## Supported bases

| Base | Detected from `/etc/debian_version` | Qt |
| --- | --- | --- |
| Debian stable (13 "trixie") | `13`, `13.x` | 6 |
| Debian testing | `14`, `14.x`, `forky/sid`, `…/sid` | 6 |

Any other base is refused. A derivative that rewrites `/etc/debian_version`
sets `CORRY_DEBIAN_BASE=stable` or `CORRY_DEBIAN_BASE=testing` when running
`install-dependencies.sh` and `build-corry.sh`. Debian 12 and Qt 5 are no
longer supported.

## Two distributions, one engine

Build and install the Corry backend, then install exactly one profile into each
ISO root:

```bash
sudo bash tools/install-profile.sh --distro edukasaun
sudo bash tools/install-profile.sh --distro debion --image /run/live/medium/live/custom.squashfs
# Open the installer automatically when the live session starts:
sudo bash tools/install-profile.sh --distro edukasaun --autostart
# Stage without changing the host:
DESTDIR=/tmp/edukasaun-root bash tools/install-profile.sh --distro edukasaun
```

Names, logos and slides are not compiled into the engine.
`config/distros/<id>/branding.desc` holds the product names; `profile.yaml` the
colors; `slides/slides.json` the slide order, titles, descriptions and local image
files. The profile script validates the images, generates `Slides.js`, and
applies the accent and tint colors to the stylesheet, header, slideshow and logo.
The shared QML and stylesheet live in `src/branding/corry`.

The profile does not build an ISO and does not turn the host into Edukasaun OS
or DebION. The ISO integrator still provides `/etc/os-release`, the kernel,
firmware, desktop, login manager, and the distribution's repositories and
keyrings in the image.

## Default installer

`install-profile.sh` installs the `corry-installer` launcher, an
"Install <product>" menu entry and a desktop icon for the live user
(`/etc/skel/Desktop`). It hides Debian's generic `calamares` and
`install-debian` menu entries through `/usr/local/share/applications` and
redirects the `install-debian` command through `/usr/local/bin`, so every
"Install" entry point in the live session opens Corry. Packages are never
modified. `--autostart` adds an XDG autostart entry as well.

The launcher sets `LANG=en_US.UTF-8` so the installer starts in US English. Set
`CORRY_LANG` to start in another language, or choose one on the welcome page.

The installed system is unpacked from the same image. `corrycleanup` therefore
removes the launcher files, the desktop icon copied into the new user's home,
the autostart entry and the redirects from the target. Extra live-only files can
be listed in `corrycleanup.conf` as `removeFiles`.

## Installation flow

1. The launcher runs `preflight.py`: filesystem tools, GRUB, initramfs-tools and
   the live image must exist. It then lists the image with `unsquashfs` and
   checks for a kernel (`boot/vmlinuz-*`), `update-initramfs`, `grub-install` and
   the GRUB platform files for this computer (`x86_64-efi` on UEFI, `i386-pc` on
   BIOS). Problems are shown in a dialog and no disk is touched.
2. Welcome (requirements: 20 GiB storage, 1 GiB RAM, root), location, keyboard,
   partitions, users and summary. Disk changes start only after the final
   confirmation.
3. Partition → mount → unpack the image → machine ID → fstab → locale and keyboard
   → users → display manager → network → hardware clock.
4. `corrycleanup` purges `live-boot`/`live-config` packages (without autoremove),
   removes the installer launchers and the live account (never its home directory).
5. `initramfs` regenerates the initramfs without live-boot.
6. `corrygrub` installs `grub-pc` (BIOS) or `grub-efi-amd64` (UEFI) inside the
   target from the boot medium's package pool (`/run/live/medium/pool`,
   `/run/live/medium/dists`), using a temporary, read-only bind mount and a
   private APT state directory. The network is never used. If the pool lacks the
   package but the image has the GRUB platform files, the installation continues
   with a warning; the system boots, but GRUB updates must then be configured
   manually.
7. `grubcfg` writes `/etc/default/grub` (os-prober enabled), `bootloader` runs
   `grub-install` (EFI directory `debian`, with the removable-media fallback), and
   `umount` releases the target. The slideshow runs throughout.

There is no software selection page and no package download. Ship the software
each distribution needs in its live image.

## Partitions and accounts

| Filesystem | Use |
| --- | --- |
| Btrfs | Default `/`; subvolumes `@`, `@home`, `@cache`, `@log`; zstd:1 compression |
| ext4 / XFS | Automatic and manual partitioning |
| FAT32 / VFAT | EFI `/boot/efi`, 512 MiB recommended, 100 MiB minimum |
| Swap | Virtual memory; no mount point |
| ext2 / ext3 | Manual, when the tools are available |
| JFS / ReiserFS | Manual, only when KPMcore and the kernel support them |

The Root, Home, EFI, Boot, Swap, Var and Tmp buttons change the partition plan.
A new Root starts at 20 GiB, EFI at 512 MiB, Boot at 1 GiB and Swap at 4 GiB,
limited by the free space. Size and filesystem stay editable. Editing an existing
partition never turns on Format automatically; for an existing `/home`, check
that Format is off and keep a backup. Automatic Btrfs snapshots and automatic
full-disk encryption are not offered yet.

Passwords need at least one character and must match. There is no separate root
password; the account is in the `sudo` group. Automatic login is off by default.

Set `liveUser` in `corrycleanup.conf` to the live account name (Debian live-build
uses `user`).

## Verification and release limits

`tools/test-profile.py` checks the module schemas, the job order, that the
software page is gone, both distribution profiles and the default-installer
files, base detection, live cleanup and launcher removal, GRUB package selection
and the package pool, and the preflight image check against a real squashfs.

CI builds the complete backend on `debian:stable` and `debian:testing`, runs the
native password and partition tests, installs the build and both profiles into
staging directories, and uploads development archives with SHA256 checksums
(kept for 14 days). These are for testing in ISO roots, not signed Debian packages
or release ISOs.

The screenshots come from `tools/preview.py`: production header and slideshow QML,
stylesheet and artwork, with storyboard page bodies and sample data. They are not
evidence of a successful ISO installation or reboot.

Before a release, complete this virtual-machine matrix **for each distribution and
each base**:

| Scenario | What must be shown |
| --- | --- |
| UEFI + GPT / BIOS + MBR and GPT | Correct partitions, initramfs, GRUB, reboot and login |
| Btrfs / ext4 / XFS | fstab correct and boot succeeds |
| Manual with existing `/home` / multiple disks | Data kept; EFI and boot loader on the right disk |
| Pool with and without `grub-pc`/`grub-efi-amd64` | Package installed, or warning and successful boot |
| Dual boot with another OS | os-prober entry in the GRUB menu |
| One-character password | Login and sudo after reboot |
| Installed system | No installer icon, menu entry or autostart |
| 1024×768 / HiDPI | Header, pages and dialogs are usable |
| Power, media or package failures | Logs are readable and mounts are released |

Secure Boot and full-disk encryption are not validated yet. Corry makes no claim
of guaranteed success until the ISO and boot tests above pass.
