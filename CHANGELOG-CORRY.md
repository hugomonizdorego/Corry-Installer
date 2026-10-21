<!-- SPDX-License-Identifier: CC0-1.0 -->
# Corry changelog

## 0.1 — in development

### Packages and design (latest)

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
