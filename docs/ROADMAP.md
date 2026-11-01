<!-- SPDX-License-Identifier: CC0-1.0 -->
# Corry roadmap to 1.0

Corry is the installer of **Edukasaun OS** (Debian stable) and **DebION GNU/Linux**
(Debian testing). Each release below has a clear goal and a checklist that must be
complete before it is tagged. Versions before 1.0 are pre-releases: they are for
testing, not for computers with data that matters.

| Version | Theme | Status |
| --- | --- | --- |
| 0.1 | Redesign, offline/online, Debian packages | Done |
| 0.2 | One package per distribution, desktop shortcut, first field fixes | Done |
| **0.3** | **New look; choice of init system and boot loader; Dili time zone** | **This release** |
| 0.4 | Proven installs in virtual machines | Next |
| 0.5 | Real hardware and Secure Boot | Planned |
| 0.6 | Languages and accessibility | Planned |
| 0.7 | Safer disks: encryption and snapshots | Planned |
| 0.8 | Distribution integration: APT repository, ISO builds, OEM mode | Planned |
| 0.9 | Feature freeze, beta and release candidate | Planned |
| **1.0** | **Final** | Planned |

## 0.1 — Redesign (done)

- New Corry look; welcome page with video; separate system check with internet.
- Offline installs from the media; online repair and updates (`corryupdate`).
- GParted, EFI 300 MiB with boot/ESP flags, same or separate administrator password.
- Slideshow with music, easy branding with `distro.yaml`, self-removal.
- Debian packages that replace Debian's Calamares.

## 0.2 — One package per distribution (done)

- `corry-edukasaun` built on Debian stable, `corry-debion` built on Debian testing.
- "Install …" shortcut on every user's desktop as soon as the package is installed.
- Fixes from the first field test: GRUB outside the live image, failed `dpkg -i`,
  debug-symbol package, start-up with `-c`.
- Secure Boot packages (`shim-signed`, `grub-efi-amd64-signed`) on UEFI, best effort.
- GitHub release with both packages.

## 0.3 — New look, init system and boot loader (this release)

- [x] Soft, light design: page cards with shadows, pill buttons, gradient main action,
      timeline header, redesigned slideshow, welcome media and summary.
- [x] **System components** page: init system (systemd default; SysVinit, OpenRC,
      runit) and boot loader (GRUB default; systemd-boot, rEFInd, Syslinux/EXTLINUX,
      U-Boot menu). Alternatives need internet; each option is checked against the
      firmware, architecture, `/boot` filesystem, Secure Boot, GNOME and the init choice.
- [x] `corryinit`: apt simulation as a guard, explicit removal of systemd's packages,
      `/sbin/init` verified, systemd purged; any problem keeps systemd with a warning.
- [x] `corrybootloader`: installs the chosen loader, removes GRUB from the new system,
      falls back to GRUB on any problem; `grubcfg`/`bootloader` step aside.
- [x] CI runs the real init switch on Debian stable and testing (`tools/ci/run-job.py`).
- [x] Time zone preselected: Asia/Dili. Exit codes of the launcher documented.

## 0.4 — Proven installs in virtual machines

Goal: every release is installed and booted automatically before it is published.

- [ ] CI builds a small Edukasaun OS and DebION live ISO with live-build and the
      matching Corry package.
- [ ] Unattended installs in QEMU: BIOS + MBR, UEFI + GPT, Btrfs, ext4, XFS; offline
      and online; with systemd/GRUB and with each alternative init system and loader.
- [ ] Each test boots the installed system and checks login, `sudo`, the boot menu,
      fstab, the init system in use and that no Corry or Calamares file is left.
- [ ] Installation log saved as a CI artifact when a test fails.
- [ ] Fix whatever these tests find.

## 0.5 — Real hardware and Secure Boot

- [ ] Field tests on at least five school and office computers per distribution
      (old BIOS, modern UEFI, NVMe, eMMC laptops, dual boot with Windows).
- [ ] Secure Boot proven on real firmware with GRUB; shim as the removable-media fallback.
- [ ] systemd-boot with Secure Boot through Debian 13's signed `systemd-boot-efi` and
      shim; rEFInd with a MOK. Offer them only once proven.
- [ ] Hardware detection: offer non-free firmware, NVIDIA and Broadcom drivers when online.
- [ ] zram swap option for computers with little memory.
- [ ] "Save installation log" button on the finish page (to a USB stick, not the new system).

## 0.6 — Languages and accessibility

- [ ] Corry's own texts translated: Tetum, Bahasa Indonesia, Portuguese.
- [ ] Language packs installed for the chosen language when online.
- [ ] High-contrast theme, keyboard-only navigation, Orca screen reader in the live session.
- [ ] 1024×768 and HiDPI layouts checked on every page.

## 0.7 — Safer disks

- [ ] Full-disk encryption (LUKS2 + `cryptsetup-initramfs`) tested and offered in
      "Erase disk".
- [ ] Btrfs snapshots before and after updates (Snapper or Timeshift + `grub-btrfs`).
- [ ] Clear warnings and a final disk preview before any partition is changed.
- [ ] Keep `/home` while reinstalling, tested.

## 0.8 — Distribution integration

- [ ] Signed APT repository for the Corry packages (Edukasaun OS and DebION keys).
- [ ] Live-build configuration for both ISOs in the distributions' build repositories.
- [ ] OEM mode: install now, create the user on first boot (for schools that prepare
      many computers).
- [ ] Upgrade path from 0.x packages verified.

## 0.9 — Beta and release candidate

- [ ] Feature freeze: no new features, only fixes.
- [ ] Public beta ISOs; issue template and feedback channel.
- [ ] Documentation for users (how to install) and for integrators (how to brand).
- [ ] Release candidate: no known critical or major bugs; the full VM matrix passes for
      both distributions and both Debian bases; translations complete; screenshots and
      documentation final.

## 1.0 — Final

Release criteria:

- [ ] Installs complete and boot on BIOS and UEFI (Secure Boot on and off), offline
      and online, for Edukasaun OS (Debian stable) and DebION GNU/Linux (Debian testing).
- [ ] Every 0.4–0.9 checklist is complete.
- [ ] No open critical or major issues for two weeks of beta/RC testing.
- [ ] Signed packages in the distributions' APT repositories; release ISOs built with Corry.
