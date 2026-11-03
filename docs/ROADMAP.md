<!-- SPDX-License-Identifier: CC0-1.0 -->
# Corry roadmap

Corry is the installer of **Edukasaun OS** (Debian stable) and **DebION GNU/Linux**
(Debian testing). Each release below has a clear goal and a checklist that must be
complete before it is tagged.

| Version | Theme | Status |
| --- | --- | --- |
| 0.1 | Redesign, offline/online, Debian packages | Done |
| 0.2 | One package per distribution, desktop shortcut, first field fixes | Done |
| 0.3 | New look; choice of init system and boot loader; Dili time zone | Done |
| **1.0** | **Stable: a theme per distribution, separate system pages, safer jobs, logs in /tmp/Corry, end-to-end tests** | **This release** |
| 1.1 | Proven on real hardware; ISO-level CI | Next |
| 1.2 | Languages and accessibility | Planned |
| 1.3 | Safer disks: snapshots and automatic encryption | Planned |
| 1.4 | Mass deployment: OEM mode, unattended installs, APT repository | Planned |
| 2.0 | Based on the next Calamares release; Debian 14 as stable | Later |

## 0.1 — Redesign (done)

- New Corry look; separate system check with internet.
- Offline installs from the media; online repair and updates (`corryupdate`).
- GParted, EFI 300 MiB with boot/ESP flags, same or separate administrator password.
- Slideshow with music, easy branding with `distro.yaml`, self-removal.
- Debian packages that replace Debian's Calamares.

## 0.2 — One package per distribution (done)

- `corry-edukasaun` built on Debian stable, `corry-debion` built on Debian testing.
- "Install …" shortcut on every user's desktop as soon as the package is installed.
- Secure Boot packages (`shim-signed`, `grub-efi-amd64-signed`) on UEFI, best effort.

## 0.3 — New look, init system and boot loader (done)

- Soft, light design; the System components page; `corryinit` and
  `corrybootloader`; the real init switch in CI; Asia/Dili.

## 1.0 — Stable (this release)

- [x] A theme per distribution: soft-blue (DebION), warm-pastel with a side menu
      (Edukasaun OS). Images only.
- [x] Init system and Boot loader on separate pages, offering only what the base's
      archive has; checked against the planned partitions and again before the jobs
      download anything.
- [x] The jobs use Calamares' API correctly, download before installing, leave
      reused EFI partitions alone, keep the system's tools after cleanup, and never
      stop the installation for anything that can be avoided.
- [x] Encrypted root, EFI directory, Secure Boot fallback, 32-bit UEFI, SVG plugin,
      LVM/LUKS partitioning, GParted rescans fixed.
- [x] The installation log in `/tmp/Corry`, owned by the user, with *Open log*.
- [x] CI: every offered package exists; the init switch for SysVinit, OpenRC and
      runit on both bases; end-to-end installs booted in QEMU (UEFI/BIOS,
      Btrfs/ext4, systemd/SysVinit, GRUB/systemd-boot); release only when versions
      agree.

## 1.1 — Proven on real hardware

- [ ] Field tests on at least five school and office computers per distribution
      (old BIOS, modern UEFI, NVMe, eMMC laptops, dual boot with Windows).
- [ ] Secure Boot on real firmware with GRUB; systemd-boot through Debian's signed
      `systemd-boot-efi` and shim, then offered with Secure Boot on.
- [ ] ISO-level CI: live-build ISOs for both distributions, booted in QEMU, the pages
      driven unattended, then the installed system booted.
- [ ] More `e2e` scenarios: XFS, OpenRC, runit, rEFInd, EXTLINUX, offline installs.
- [ ] Copy the installation log to a USB stick from the Finished page.

## 1.2 — Languages and accessibility

- [ ] Corry's own texts translated: Tetum, Bahasa Indonesia, Portuguese.
- [ ] Language packs installed for the chosen language when online.
- [ ] A high-contrast theme, keyboard-only navigation, Orca in the live session.
- [ ] 1366×768, 1024×768 and HiDPI layouts checked on every page for both themes.

## 1.3 — Safer disks

- [ ] Btrfs snapshots before and after updates (Snapper or Timeshift + `grub-btrfs`).
- [ ] Automatic full-disk encryption (LUKS2 + `cryptsetup-initramfs`) in Erase disk.
- [ ] zram swap for computers with little memory.
- [ ] Keep `/home` while reinstalling, tested.

## 1.4 — Mass deployment

- [ ] OEM mode: install now, create the user on first boot.
- [ ] Unattended installs from a settings file on a USB stick.
- [ ] Signed APT repository for the Corry packages (Edukasaun OS and DebION keys).
- [ ] Driver assistant (NVIDIA, Broadcom, firmware) when online.

## 2.0 — Next base

- [ ] Rebase on the next Calamares release, keeping Corry's pages, themes and jobs.
- [ ] Debian 14 as the stable base for Edukasaun OS; the next testing for DebION.
