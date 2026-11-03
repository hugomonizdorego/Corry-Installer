<!-- SPDX-License-Identifier: CC0-1.0 -->
# Corry Installer 1.0

> **Stable release 1.0.** Every release is installed and booted in virtual
> machines by CI (UEFI and BIOS, Btrfs and ext4, systemd and SysVinit, GRUB and
> systemd-boot). Try it once on your own hardware before installing on many
> computers, and keep a backup of data you cannot afford to lose.

Corry is the default system installer for **Edukasaun OS** and
**DebION GNU/Linux**. It is a fork of **Calamares 3.3.15** with one shared
installation engine and an easily edited profile per distribution:

| Distribution | Debian base | Look |
| --- | --- | --- |
| **Edukasaun OS** | Debian stable (13 "trixie") | *warm-pastel*: cream page, rounded mint side menu, salmon welcome card, coral buttons, pastel cards |
| **DebION GNU/Linux** | Debian testing | *soft-blue*: neumorphic light-blue cards, timeline header, blue gradient buttons |

## Screenshots, start to finish

Captured from the **real Corry 1.0 build** running on a virtual display
(`tools/screenshots/capture.sh`), except the two partition pages marked
*preview*: a container has no disks to list, so those come from the design
preview (`tools/preview.py`). The real capture run skips the partition step, so
the menu counts 10 steps there instead of 11.

**Edukasaun OS** (Debian stable, warm-pastel)

| | |
| --- | --- |
| ![Welcome](docs/screenshots/edukasaun-01-welcome.png) **Welcome** and language | ![System check](docs/screenshots/edukasaun-02-system-check.png) **System check** and internet recommendation |
| ![Location](docs/screenshots/edukasaun-03-location.png) **Location** (Asia/Dili preselected) | ![Keyboard](docs/screenshots/edukasaun-04-keyboard.png) **Keyboard** |
| ![Partitions](docs/screenshots/edukasaun-05-partitions-preview.png) **Partitions** with *Open GParted* (preview) | ![Partition role](docs/screenshots/edukasaun-06-partition-role-preview.png) **EFI role: 300 MiB, flags set automatically** (preview) |
| ![Users](docs/screenshots/edukasaun-07-users.png) **Users**: same password for the administrator | ![Admin password](docs/screenshots/edukasaun-08-users-admin-password.png) **…or a different one** |
| ![Init system](docs/screenshots/edukasaun-09-system-init.png) **Init system** | ![Boot loader](docs/screenshots/edukasaun-10-system-boot-loader.png) **Boot loader** (offline here: only the defaults) |
| ![Summary](docs/screenshots/edukasaun-11-summary.png) **Summary** | ![Confirm](docs/screenshots/edukasaun-12-confirm.png) **Final confirmation** |
| ![Install](docs/screenshots/edukasaun-13-install.png) **Install**: slideshow with music | ![Slides](docs/screenshots/edukasaun-14-install-slides.png) **7 slides** |
| ![Finish](docs/screenshots/edukasaun-15-finish.png) **Finish** with *Open the installation log* | |

**DebION GNU/Linux** (Debian testing, soft-blue)

| | |
| --- | --- |
| ![Welcome](docs/screenshots/debion-01-welcome.png) **Welcome** | ![Partitions](docs/screenshots/debion-05-partitions-preview.png) **Partitions** (preview) |
| ![Users](docs/screenshots/debion-07-users.png) **Users** | ![Init system](docs/screenshots/debion-09-system-init.png) **Init system** |
| ![Boot loader](docs/screenshots/debion-10-system-boot-loader.png) **Boot loader** (testing: no rEFInd) | ![Slides](docs/screenshots/debion-14-install-slides.png) **Install** |

All screenshots are in [`docs/screenshots`](docs/screenshots).

## What Corry does

- **A theme per distribution.** Colors, fonts, corner radius and layout (header on
  top or a side menu of steps) come from `config/themes`; each distribution picks
  one in its `distro.yaml`. Pages are soft cards with pill buttons and one gradient
  main action.
- **Welcome** greets the user with an image and offers the language. **System
  check** follows on its own page: disk space, memory, power, administrator rights,
  screen and **internet**, with a *Check again* button.
- **Works with and without internet.** Without it, everything comes from the
  installation media. With it — which Corry recommends — Corry also repairs broken
  packages and installs updates (downloaded first, so a slow line never breaks the
  system), can download the GRUB package if the media lacks it, and offers the
  alternative init systems and boot loaders.
- **Partitions:** erase disk (Btrfs by default, ext4 and XFS available), manual
  partitioning with Root/Home/EFI/Boot/Swap/Var/Tmp role buttons (also LVM, LUKS
  and kept Windows data partitions), or **Open GParted**; disks are re-read when
  GParted closes. Choosing **EFI** proposes **300 MiB** FAT32 and sets the
  **boot/ESP flags automatically**.
- **Users:** one checkbox decides whether the administrator (root) account uses
  **the same password** as the user or **a different one**.
- **Init system** page: systemd (Debian's default) or SysVinit, OpenRC, runit.
  **Boot loader** page: GRUB 2 (the default for BIOS and UEFI) or systemd-boot,
  rEFInd (Debian stable only) and Syslinux/EXTLINUX. Each page offers only what the
  distribution's Debian base really has (checked against the archives in CI). The
  defaults work offline; an alternative needs internet and is offered only when it
  fits this computer and the planned partitions: BIOS or UEFI, 32-bit UEFI, the
  filesystem and encryption of `/boot`, other operating systems, Secure Boot
  (Debian signs GRUB), a GNOME desktop (needs systemd) and the init choice. Once
  the alternative is installed and checked, **the replaced default is removed from
  the new system** so that only one init system and one boot loader remain. If
  anything goes wrong, the default stays and the log says why.
- **Legacy BIOS and UEFI:** BIOS installs use an MBR disk and `grub-pc`; UEFI
  installs use GPT, a 300 MiB EFI partition, `grub-efi-amd64` with shim for Secure
  Boot (also on the removable-media path), and `grub-efi-ia32` on 32-bit UEFI.
  os-prober is enabled for dual boot.
- **Installation:** a slideshow of at least five images (seven by default) with
  tips, and calm background music that can be muted.
- **The log is kept for you.** If the installation fails, the whole log is saved to
  **`/tmp/Corry/install.log`**, owned by you; the error dialog has **Open log** and
  Corry stays on the Finished page. Crashes and preflight problems are logged there
  too.
- **Leaves no trace.** After installation the new system contains no Corry or
  Calamares files, packages, launchers, menu entries or configuration; the tools the
  system needs (cryptsetup, lvm2, GRUB, sudo…) stay installed for good.
- **Replaces Calamares.** The packages remove Debian's `calamares` and
  `calamares-settings-debian` completely and become the default installer, with an
  "Install …" shortcut on every desktop.
- **Easy branding:** one `distro.yaml` per distribution holds names, Debian base,
  theme, color overrides, links, music and slides. `tools/new-distro.py` creates a
  new profile in one command.
- US English (`en_US.UTF-8`) by default; other languages can be chosen on the welcome
  page. Time zone Asia/Dili (Timor-Leste) preselected.

## Install the Debian packages

There is one complete package per distribution:

| Package | For | Built on |
| --- | --- | --- |
| `corry-edukasaun_1.0_amd64.deb` | Edukasaun OS | Debian stable |
| `corry-debion_1.0_amd64.deb` | DebION GNU/Linux | Debian testing |

Download it from the GitHub release (or a CI run's *Artifacts*), then, in the live
system or the ISO build chroot, with internet for the dependencies:

```bash
sudo sh install-corry-debs.sh                    # installs the corry-*.deb next to it
# the same by hand:
sudo apt install ./corry-edukasaun_1.0_amd64.deb
```

**Do not use `dpkg -i`**: it does not download the dependencies and leaves the
package unconfigured. If that already happened, `install-corry-debs.sh` (or
`sudo apt --fix-broken install`) repairs it. Install the package that matches the
base: the testing build needs Debian testing's libraries.

After installation every user has an **"Install Edukasaun OS"** (or "Install DebION
GNU/Linux") shortcut on the desktop; double-click it to start Corry.

apt resolves the dependencies and **removes Debian's
`calamares` and `calamares-settings-debian`** (Corry conflicts with and replaces
them). Corry's `postinst` then deletes every file they left behind (such as their
desktop autostart entry), and an APT hook purges their package records after the
next dpkg run, so nothing of Calamares remains to conflict. Corry then is the
default installer: the "Install Edukasaun OS" menu entry, a desktop icon in the live
session, and Debian's `install-debian` command all open Corry.

`sudo apt purge corry-edukasaun` removes Corry completely, desktop shortcuts included. On the installed
system, Corry's `corrycleanup` job purges these packages automatically.

### If something goes wrong

| Where | What to do |
| --- | --- |
| Corry does not start | `corry-installer` exits with **2** and says what is missing (a tool, the live image, a kernel, GRUB, the profile); the reasons are also in **`/tmp/Corry/preflight-error.log`**. **4**: the engine is not installed; **126/127**: administrator rights were refused |
| The installation stops | The error dialog says which step failed and why. Press **Open log**, or open **`/tmp/Corry/install.log`** in any text editor: look for lines with `ERROR` or `WARNING`, and attach the file when you ask for help. `/tmp` is emptied at restart, so copy it first |
| Corry closes unexpectedly | Its log is in **`/tmp/Corry/crash-<date>.log`** |

Details in [docs/CORRY-DEVELOPMENT.md](docs/CORRY-DEVELOPMENT.md#exit-codes-and-error-messages).

## Build from source

Run inside a disposable Debian stable or testing machine:

```bash
sudo apt install dpkg-dev debhelper && sudo apt build-dep ./
dpkg-buildpackage -us -uc -b            # builds and tests; packages land in ../
```

Without packages (development only): `tools/install-dependencies.sh build`,
`tools/build-corry.sh`, `sudo tools/install-corry.sh build-corry`,
`sudo tools/install-profile.sh --distro edukasaun`. These scripts also purge
Debian's Calamares first and record every file in `/usr/lib/corry/manifest` for
self-removal. The base is detected from `/etc/debian_version` (`13.x` stable,
`forky/sid` or `14.x` testing); override with `CORRY_DEBIAN_BASE`.

The live image must contain what the installed system needs: a Debian kernel,
firmware, desktop, login manager, initramfs-tools, `grub2-common`, `grub-pc-bin` and
`grub-efi-amd64-bin` (ideally `grub-pc`/`grub-efi-amd64` in the ISO's package pool).

- [Integration and testing guide, exit codes](docs/CORRY-DEVELOPMENT.md)
- [Branding guide: edit or add a distribution, themes, media sizes](docs/BRANDING.md)
- [Calamares and Debian review, recommended features](docs/RECOMMENDATIONS.md)
- [Roadmap](docs/ROADMAP.md)
- [Changelog](CHANGELOG-CORRY.md)

CI builds the packages on `debian:stable` and `debian:testing`, installs Debian's
real `calamares` + `calamares-settings-debian`, installs Corry over them, checks that
nothing of Calamares is left, starts the installed Corry on a virtual display,
purges Corry, checks every package the Init system and Boot loader pages offer
against the real archives, switches to SysVinit, OpenRC and runit for real, and
installs a small Debian system with the packaged job modules into a disk image that
is then booted in QEMU. A release is published only when all of this passes.

## Languages Corry is written in

The engine and its pages are **C++ with Qt 6** (Qt 5 for local development), the
header, side menu, slideshow and welcome card are **QML**, the installation jobs
Corry adds are **Python 3**, and the launcher and packaging helpers are **POSIX
shell**. These are the languages of Calamares itself: every upstream module, test
tool and fix keeps working, the Python jobs run inside the engine with Calamares'
job API, and Debian ships all of it.

## Licensing

Upstream per-file licenses and notices are retained; see `LICENSES/`. New Corry code
uses GPL-3.0-or-later unless marked otherwise. The slide artwork and background music
are original, generated by `tools/generate-default-media.py`, and CC0-1.0. The configuration is derived from
[CatalystDevOrg/calamares-settings-debian](https://github.com/CatalystDevOrg/calamares-settings-debian),
kept in `config/upstream/catalyst` with its ISC notice
([source provenance](config/upstream/catalyst/UPSTREAM.md)). Calamares upstream:
https://codeberg.org/Calamares/calamares
