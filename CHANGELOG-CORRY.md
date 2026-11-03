<!-- SPDX-License-Identifier: CC0-1.0 -->
# Corry changelog

## 1.0 — stable

The first stable release, for Edukasaun OS (Debian stable) and DebION GNU/Linux
(Debian testing).

### Look

- **A theme per distribution** (`config/themes`, chosen with `theme:` in
  `distro.yaml`): **soft-blue** for DebION — neumorphic light-blue cards with a
  soft highlight, a timeline header on top — and **warm-pastel** for Edukasaun
  OS — cream page, a rounded mint side menu of numbered steps, a salmon welcome
  card, coral pill buttons and mint/salmon/yellow/blue cards. Every color,
  the fonts and the corner radius come from the theme; `colors:` in
  `distro.yaml` overrides single colors. Branding sources use `@token@`
  placeholders, checked by `tools/corry-branding.py` (unknown tokens are errors).
- **Images only**: the welcome video, its player and its generator are gone; an
  old `welcome.video` line is ignored with a note. Default slides take the
  theme's tile colors.
- Combo boxes have a themed chevron, checked boxes a tick, radios stay round,
  the welcome title wraps, the side-menu layout gets a 1240px window and
  pages scroll instead of being cut on small screens.

### Init system and boot loader

- **Two pages** instead of one: *Init system* and *Boot loader*
  (`corrysystem@init`, `corrysystem@bootloader`). Each lists only options whose
  packages exist on the distribution's Debian base (`availableOn`, written per
  distribution as `base:`): SysVinit, OpenRC and runit on both bases;
  systemd-boot and Syslinux/EXTLINUX on both; rEFInd on stable only. U-Boot is
  no longer offered (Corry's packages are amd64). CI checks every offered
  package against the real archives and switches to SysVinit, OpenRC and runit
  for real on both bases.
- The boot loader page sees the **planned partitions** (published by the
  partition page) and refuses rEFInd/EXTLINUX for an encrypted `/boot`,
  EXTLINUX for compressed Btrfs or next to another operating system, and every
  alternative on 32-bit UEFI. `corrybootloader` checks again with the real
  partition list, and also refuses EXTLINUX on a logical partition or next to
  another active partition, before anything is downloaded.

### Installation safety

- `corryinit` and `corrybootloader` read command output with
  `check_target_env_output`; `target_env_process_output` returns only the exit
  code in Calamares 3.3, which made every alternative init choice fail. The test
  fakes now follow the real API.
- Packages are **downloaded first** (safe to interrupt on a slow line) and then
  installed without a time limit, so dpkg is never killed half-way.
- A **reused EFI partition** keeps other systems' `EFI/…` directories and boot
  entries; only an EFI partition formatted by this installation is cleaned.
- **BIOS installations get GRUB again.** Since the upstream hybrid-GRUB change,
  the bootloader job skipped `grub-install` on BIOS whenever an EFI directory was
  known, and the partition module always sets one: BIOS computers were left
  without a boot loader. Found by the new end-to-end test.
- An unexpected error in `corryinit`, `corrybootloader`, `corryupdate` or
  `corrycleanup` becomes a warning; the system keeps systemd or GRUB.
- `corrycleanup` marks the system's own tools (cryptsetup, lvm2, GRUB, sudo…)
  as manually installed before Corry is purged, so `apt autoremove` cannot break
  the boot, and a refused purge no longer stops the installation.
- **Encrypted root**: crypttab without `keyscript=/bin/cat` (nothing created the
  key file, so the root could not be unlocked).
- GRUB's EFI directory follows `GRUB_DISTRIBUTOR` (`debion`, `edukasaun`), as
  Debian's grub-efi upgrades expect; boot menu names no longer repeat
  "GNU/Linux". With Secure Boot the removable-media path gets the shim chain;
  `grub-install` is retried without an NVRAM entry when the firmware refuses
  one. 32-bit UEFI gets GRUB for `i386-efi`.
- Manual partitioning allows LVM physical volumes, LUKS and Windows data
  partitions (writable by the new user, never blocking the boot); GParted
  rescans the disks in place; *Check again* no longer starts parallel checks.
- The packages depend on Qt's **SVG image plugin** (it was missing, so SVG
  logos, slides and icons could not be drawn) and on `fdisk`; they recommend the
  theme fonts, `ntfs-3g` and `exfatprogs`.

### Logs

- A failed installation saves the whole log, with a short report on top, to
  **`/tmp/Corry/install.log`** (and a dated copy), owned by the desktop user. The
  error dialog names the file and has **Open log**; Corry then stays on the
  Finished page, which explains where the log is and opens it in a text editor.
  A successful installation keeps its log there too.
- If the engine stops unexpectedly, `corry-session` saves its log as
  `/tmp/Corry/crash-<date>.log`; a failed preflight check is saved to
  `/tmp/Corry/preflight-error.log`.

### Tests and tools

- **End-to-end test** (`tools/ci/e2e-install.sh`, CI job `e2e`): a small Debian
  live image is installed with the packaged job modules into a disk image, which
  is booted in QEMU and must report its init system and root filesystem — UEFI
  and BIOS, Btrfs and ext4, systemd and SysVinit, GRUB and systemd-boot.
  Calamares' `loadmodule` can save global storage (`-G`) and fails with exit 1.
- Release checks that the tag, `VERSION`, `debian/changelog` and this changelog
  agree; the smoke test fails when a module or QML file does not load.
- `corry-desktop-icon` writes every file in a home as its owner.
- `install-corry-debs.sh` takes the newest package and never stops at a conffile
  question; `remove-calamares --purge` reports a failed purge.

## 0.3 — pre-release

- **New look.** A light blue page with soft white cards (painted by the new
  `CorryCard` widget, no images needed), pill buttons, a gradient main action,
  a timeline header, and a redesigned slideshow, welcome media and summary. The
  light and dark accent shades used by gradients and hover states are derived
  from each distribution's `colors.accent` (or set with `accent-light` and
  `accent-dark` in `distro.yaml`).
- **System components page.** After *Users*, Corry asks for the **init system**
  (systemd, the default; SysVinit, OpenRC, runit) and the **boot loader** (GRUB 2,
  the default; systemd-boot, rEFInd, Syslinux/EXTLINUX, U-Boot menu). The defaults
  work offline; the alternatives are downloaded from the distribution's
  repositories and need internet. Every option is checked against this computer:
  firmware (BIOS/UEFI), architecture, the filesystem of `/boot`, Secure Boot, a
  GNOME desktop (needs systemd) and the init choice (Debian's systemd-boot needs
  systemd). Unavailable options say why; *Check again* re-tests the connection.
- **`corryinit`.** Installs the chosen init system with `elogind`, after reading
  apt's simulation: if anything but systemd's own packages would be removed, the
  switch is refused and systemd stays. systemd's packages are asked to be removed
  explicitly (the live image marks everything as manually installed, and
  `systemd-sysv` is Essential), `/sbin/init` is verified, and systemd is purged as
  far as the dependencies allow. Problems become warnings; the system always boots.
- **`corrybootloader`.** Installs systemd-boot (`bootctl` + `kernel-install`, or
  its own entries and kernel hooks when `kernel-install` is missing), rEFInd
  (copied to `EFI/refind` and the removable-media path, with the matching
  filesystem drivers), EXTLINUX (`extlinux --install`, MBR/GPT boot code, boot
  flag, kernel hooks) or `u-boot-menu`; then purges GRUB's packages, files, EFI
  directory and NVRAM entries. Any failure falls back to GRUB with a warning;
  `grubcfg` and `bootloader` step aside only when the alternative is in place.
- CI: an `init-switch` job runs `corryinit` for real on Debian stable and testing
  (`tools/ci/run-job.py`); a manual Debian probe workflow documents the packages.
- Time zone preselected: Asia/Dili (Timor-Leste). Launcher exit codes documented.
- Screenshots of the 0.3 build from start to finish; roadmap updated.

## 0.2 — pre-release

- **One package per distribution.** `corry-edukasaun` is built on Debian stable
  (Edukasaun OS) and `corry-debion` on Debian testing (DebION GNU/Linux). Each
  contains the whole installer and replaces the 0.1 `corry` and profile packages
  as well as Debian's `calamares` and `calamares-settings-debian`.
- **Desktop shortcut.** Installing the package puts an "Install Edukasaun OS" /
  "Install DebION GNU/Linux" shortcut, executable and trusted, on every user's
  desktop right away (and once for users who log in later). Removing the package
  removes the shortcuts. The shortcut uses the product logo as its icon.
- **Secure Boot.** On 64-bit UEFI, `shim-signed` and `grub-efi-amd64-signed` are
  installed from the media pool or online (best effort; a warning if not possible).
- No `-dbgsym` or `dwz` debug files; `install-corry-debs.sh` finds the package next
  to it and installs it with apt.
- Release workflow: pushing a `v*` tag publishes both packages as a GitHub release.
- Roadmap to 1.0 in `docs/ROADMAP.md`.

## 0.1

### Fixes from the first test on Debian testing

- Corry refused to start on Debian live images because GRUB is not inside their
  `filesystem.squashfs`. GRUB may now come from the image, the ISO's package pool
  or the internet; Corry installs it during installation (`corrygrub`).
- `install-corry-debs.sh` installs the packages with apt and repairs a failed
  `dpkg -i`; CI artifacts no longer include the `corry-dbgsym` debug package.

### Packages and design

- Debian packages: `corry`, `corry-edukasaun`, `corry-debion`. Installing them with
  apt removes Debian's `calamares` and `calamares-settings-debian`; leftovers are
  deleted and their records purged. Corry becomes the default installer.
- Fixed a start-up failure on installed systems (launcher used the testing option `-c`).
- Corry headings on Location, Keyboard, Partitions, Users and Summary; summary cards;
  borderless installation page with *Show details*; new finish page; confirmation
  dialog without the question-mark icon; text-only welcome buttons.
- Fixed media sizes: welcome video 560×315 (16:9), slides in a 16:9 card;
  `corry-branding.py` warns about sizes, ratios and file sizes. Default welcome
  videos are now 1280×720.
- Desktop icon for the live user via an autostart helper (no `/etc/skel` files).

### First 0.1 changes

First numbered Corry release, based on Calamares 3.3.15, for Edukasaun OS and
DebION GNU/Linux on Debian stable (13) and Debian testing.

- Welcome split into a greeting page (with a muted, looping product video) and a
  separate System check page (requirements and internet, with *Check again*).
- Works with and without internet: offline from the installation media; online,
  packages are repaired and updated during installation (`corryupdate`).
- *Open GParted* on the partition page; disks are re-read when it closes.
- EFI role proposes 300 MiB and sets the boot/ESP flags automatically; adjustable.
- Users choose the same or a different administrator (root) password.
- Legacy BIOS (MBR, `grub-pc`) and UEFI (GPT, `grub-efi-amd64`); os-prober enabled.
- Installation slideshow with at least five slides (seven by default) and
  background music with a mute button.
- Corry removes itself completely from the installed system (manifest, packages,
  launchers, configuration).
- One `distro.yaml` per distribution; `tools/new-distro.py` and
  `tools/corry-branding.py --check`.
- Fixed: the greeting page could be locked by a failing system check; the
  slideshow failed to load on Qt 5 because of an old QtQuick import.
- Launcher keeps the display and sound environment when it can (passwordless sudo).
- Version shown in the header and the About dialog: "Corry 0.1 (based on Calamares 3.3.15)".
- Screenshots of the real build from start to finish; see the README.
