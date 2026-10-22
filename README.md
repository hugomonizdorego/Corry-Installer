<!-- SPDX-License-Identifier: CC0-1.0 -->
# Corry Installer 0.1

> **Status: in development (0.1).** Corry has not yet been validated by full ISO
> installations on real hardware. Do not use it on a computer with data you
> cannot afford to lose.

Corry is the default system installer for **Edukasaun OS** and
**DebION GNU/Linux**. It is a fork of **Calamares 3.3.15** with one shared
installation engine and an easily edited profile per distribution. Both
distributions are built on **Debian stable (13 "trixie")** and **Debian testing**;
Corry supports exactly those two bases.

## Screenshots, start to finish

Captured from the **real Corry 0.1 build** running on a virtual display
(`tools/screenshots/capture.sh`), except the two partition pages marked
*preview*: a container has no disks to list, so those come from the design
preview (`tools/preview.py`). The real capture run skips the partition step, so
the header counts 8 steps there instead of 9.

| | |
| --- | --- |
| ![1 Welcome](docs/screenshots/edukasaun-01-welcome.png) **1 · Welcome** with the product video | ![2 System check](docs/screenshots/edukasaun-02-system-check.png) **2 · System check** and internet recommendation |
| ![3 Location](docs/screenshots/edukasaun-03-location.png) **3 · Location** | ![4 Keyboard](docs/screenshots/edukasaun-04-keyboard.png) **4 · Keyboard** |
| ![5 Partitions](docs/screenshots/edukasaun-05-partitions-preview.png) **5 · Partitions** with *Open GParted* (preview) | ![6 Partition role](docs/screenshots/edukasaun-06-partition-role-preview.png) **EFI role: 300 MiB, boot/ESP flags set automatically** (preview) |
| ![7 Users](docs/screenshots/edukasaun-07-users.png) **5 · Users**: same password for the administrator | ![8 Admin password](docs/screenshots/edukasaun-08-users-admin-password.png) **…or a different administrator password** |
| ![9 Summary](docs/screenshots/edukasaun-09-summary.png) **6 · Summary** | ![10 Confirm](docs/screenshots/edukasaun-10-confirm.png) **Final confirmation** |
| ![11 Install](docs/screenshots/edukasaun-11-install.png) **7 · Install**: slideshow with music | ![12 Slides](docs/screenshots/edukasaun-12-install-slides.png) **7 slides with recommendations** |
| ![13 Finish](docs/screenshots/edukasaun-13-finish.png) **8 · Finish** | ![DebION](docs/screenshots/debion-12-install-slides.png) **DebION GNU/Linux** (same engine, own profile) |

All DebION GNU/Linux screenshots are in [`docs/screenshots`](docs/screenshots).

## What Corry does

- **Welcome** greets the user with a short, muted, looping product video (or an image)
  and offers the language. **System check** follows on its own page: disk space,
  memory, power, administrator rights, screen and **internet**, with a *Check again* button.
- **Works with and without internet.** Without it, everything comes from the
  installation media. With it — which Corry recommends — Corry also repairs broken
  packages and installs updates during installation, and can download the GRUB
  package if the media lacks it. Network problems never fail the installation.
- **Partitions:** erase disk (Btrfs by default, ext4 and XFS available), manual
  partitioning with Root/Home/EFI/Boot/Swap/Var/Tmp role buttons, or **Open GParted**;
  disks are re-read when GParted closes. Choosing **EFI** proposes **300 MiB** FAT32
  and sets the **boot/ESP flags automatically**; the size stays adjustable.
- **Users:** one checkbox decides whether the administrator (root) account uses
  **the same password** as the user or **a different one**.
- **Legacy BIOS and UEFI:** BIOS installs use an MBR disk and `grub-pc`; UEFI installs
  use GPT, a 300 MiB EFI partition and `grub-efi-amd64`. os-prober is enabled for dual boot.
- **Installation:** a slideshow of at least five images (seven by default) with tips,
  and calm background music that can be muted.
- **Leaves no trace.** After installation the new system contains no Corry or
  Calamares files, packages, launchers, menu entries or configuration.
- **Replaces Calamares.** The `corry` package removes Debian's `calamares` and
  `calamares-settings-debian` completely and becomes the default installer.
- **Its own look.** Page headings, summary cards, a borderless installation page with
  *Show details*, a finish page and a confirmation dialog designed for Corry.
- **Easy branding:** one `distro.yaml` per distribution holds names, colors, links,
  video, music and slides. `tools/new-distro.py` creates a new profile in one command.
- US English (`en_US.UTF-8`) by default; other languages can be chosen on the welcome page.

## Install the Debian packages

Corry is packaged as three `.deb` files (built by CI for Debian stable and
testing, see *Actions → Artifacts*, or locally with `dpkg-buildpackage -us -uc -b`):

| Package | Contents |
| --- | --- |
| `corry_0.1_<arch>.deb` | The installer engine, launcher, preflight check and Calamares clean-up |
| `corry-edukasaun_0.1_all.deb` | Edukasaun OS profile: branding, settings, menu entry |
| `corry-debion_0.1_all.deb` | DebION GNU/Linux profile (installing one profile removes the other) |

In the live system or the ISO build chroot, with internet (for the dependencies),
from the folder with the downloaded files:

```bash
sudo sh install-corry-debs.sh edukasaun      # or: debion
# the same by hand:
sudo apt install ./corry_0.1_amd64.deb ./corry-edukasaun_0.1_all.deb
```

**Do not use `dpkg -i`**: it does not download the dependencies (for example
`qml6-module-qtqml-workerscript`) and leaves the packages unconfigured. If that
already happened, `install-corry-debs.sh` (or `sudo apt --fix-broken install`)
repairs it. `corry-dbgsym` holds debug symbols only and is not needed.

apt resolves the dependencies and **removes Debian's
`calamares` and `calamares-settings-debian`** (Corry conflicts with and replaces
them). Corry's `postinst` then deletes every file they left behind (such as their
desktop autostart entry), and an APT hook purges their package records after the
next dpkg run, so nothing of Calamares remains to conflict. Corry then is the
default installer: the "Install Edukasaun OS" menu entry, a desktop icon in the live
session, and Debian's `install-debian` command all open Corry.

`sudo apt purge corry corry-edukasaun` removes Corry completely. On the installed
system, Corry's `corrycleanup` job purges these packages automatically.

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

- [Integration and testing guide](docs/CORRY-DEVELOPMENT.md)
- [Branding guide: edit or add a distribution, media sizes](docs/BRANDING.md)
- [Calamares review and recommendations](docs/RECOMMENDATIONS.md)
- [Changelog](CHANGELOG-CORRY.md)

CI builds the packages on `debian:stable` and `debian:testing`, installs Debian's
real `calamares` + `calamares-settings-debian`, installs Corry over them, checks that
nothing of Calamares is left, starts the installed Corry on a virtual display,
switches profile, purges Corry, and uploads the `.deb` files.

## Licensing

Upstream per-file licenses and notices are retained; see `LICENSES/`. New Corry code
uses GPL-3.0-or-later unless marked otherwise. The slide artwork, welcome video and
background music are original, generated by `tools/generate-default-media.py`, and
CC0-1.0. The configuration is derived from
[CatalystDevOrg/calamares-settings-debian](https://github.com/CatalystDevOrg/calamares-settings-debian),
kept in `config/upstream/catalyst` with its ISC notice
([source provenance](config/upstream/catalyst/UPSTREAM.md)). Calamares upstream:
https://codeberg.org/Calamares/calamares
