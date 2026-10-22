<!-- SPDX-License-Identifier: CC0-1.0 -->
# Corry changelog

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
