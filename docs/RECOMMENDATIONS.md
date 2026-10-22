<!-- SPDX-License-Identifier: CC0-1.0 -->
# Calamares review and recommendations (Corry 0.1)

Corry is a fork of Calamares 3.3.15. This page lists the Calamares behaviors
that were checked because they can break an installation, what Corry 0.1 does
about each, and what should be added next.

## Checked and handled in 0.1

| # | Risk in Calamares / Debian live installs | What Corry does |
| --- | --- | --- |
| 1 | The welcome step passed the raw "requirements satisfied" result as its Next state, so a failing check could also lock an unrelated page. | Found by running the real build: the step now reports its own verdict. The greeting never blocks; the System check page does. |
| 2 | QML files imported `QtQuick 2.3` but used newer properties; on Qt 5 the slideshow then failed to load. | Found by running the real build. All Corry QML imports `QtQuick 2.15`, valid on Qt 5.15 and Qt 6. |
| 3 | Calamares runs as root through `pkexec`, which drops the display and sound environment (no music, problems on Wayland, GParted). | The launcher prefers passwordless `sudo` (standard for Debian live users) and keeps `DISPLAY`, `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR` and the PulseAudio/PipeWire socket. `pkexec` remains the fallback. |
| 4 | `live-boot` left in the target breaks the first boot (it diverts `update-initramfs`). | `corrycleanup` purges the live packages before `initramfs` runs. |
| 5 | Live images ship only `grub-*-bin`; without `grub-pc`/`grub-efi-amd64`, kernel and GRUB updates stop updating the boot loader. | `corrygrub` installs the right package from the boot medium's pool, or online; if neither works but the GRUB files exist, it continues with a warning. |
| 6 | A broken image (no kernel, no way to get GRUB) is only discovered after the disk has been formatted. | `preflight.py` lists the squashfs before Calamares starts. A kernel and initramfs-tools must be in the image; GRUB may come from the image, the ISO's package pool or the internet (Debian's live images keep GRUB out of the image). |
| 7 | Debian 12+ disables os-prober, so other systems disappear from the boot menu. | `grubcfg` writes `GRUB_DISABLE_OS_PROBER=false`. |
| 8 | Half-configured or broken packages in the image make the first boot or first update fail. | `corryupdate` always runs `dpkg --configure -a`; online it also runs `apt-get --fix-broken install` and updates. |
| 9 | `apt` inside the target can start services and has no DNS. | `corryupdate` adds a temporary `policy-rc.d` and the live session's `resolv.conf`, and always restores both. |
| 10 | `full-upgrade` on Debian testing can remove packages during a transition. | The default is `upgrade --with-new-pkgs`, which never removes packages. Network failures are warnings, never errors. |
| 11 | BIOS + GPT without a `bios_grub` partition fails at `grub-install`, after formatting. | Erase-disk uses MBR on BIOS and GPT+ESP on UEFI. For manual GPT layouts on BIOS, Calamares' warning is kept. |
| 12 | The installed system still contains the installer (menu entries, desktop icons, `/etc/calamares`, the `calamares` package). | `corrycleanup` purges `calamares`/`calamares-settings-debian`, deletes every file in `/usr/lib/corry/manifest` and all launchers. Calamares 3.3 does not copy its log into the target, so no log is left either. |
| 13 | GParted changes disks behind Calamares' back. | The partition page re-reads all disks when GParted closes and discards the old plan. |
| 14 | An EFI partition without the ESP flag is not bootable. | The EFI role sets the boot/ESP flag automatically (KPMcore's Boot flag is the ESP flag on GPT); 300 MiB is proposed and can be changed. |
| 15 | The launcher started the engine with `-c /etc/calamares`, a testing option that makes it look for QML only in `/etc/calamares/qml`; installed systems would refuse to start. | Found by running the installed package: the launcher no longer passes `-c`; CI starts the installed package to catch this. |
| 16 | Debian's `calamares-settings-debian` would stay next to Corry (competing `/etc/calamares`, its own desktop icon at login). | The `corry` package conflicts with and replaces it; leftovers are deleted and its record purged. |
| 17 | Automated full-disk encryption is not tested with Debian's initramfs/GRUB integration. | Not offered in automatic mode yet. |

## Recommended next steps

In order of benefit for a smooth installation:

1. **VM test matrix in CI.** Boot a real Edukasaun OS and DebION ISO in QEMU with
   SeaBIOS and OVMF, install unattended and reboot. This is the only way to prove
   the whole chain works, and it should gate releases.
2. **Secure Boot on real firmware.** Since 0.2 `shim-signed` and
   `grub-efi-amd64-signed` are installed on UEFI; prove it on real computers and
   make shim the removable-media fallback. See [ROADMAP.md](ROADMAP.md).
3. **An APT repository** for the `corry` packages (signed with the distribution's
   key), so live images and updates get Corry like any other package. *(The packages
   themselves exist since 0.1.)*
4. **Btrfs snapshots** (Snapper or Timeshift with `grub-btrfs`) so a broken update can
   be rolled back from the boot menu.
5. **Hardware support:** detect NVIDIA/Broadcom hardware and offer the drivers when
   online; include `firmware-linux` and `firmware-misc-nonfree` in the image.
6. **zram swap** for low-memory classroom computers, instead of or next to a swap partition.
7. **Translations** of Corry's own texts: Tetum, Bahasa Indonesia and Portuguese.
8. **Accessibility:** high-contrast theme and screen reader (Orca) on the live session.
9. **Tested full-disk encryption** (LUKS2 with `cryptsetup-initramfs`) before it is offered.
10. **An optional "save installation log" button** on the Finish page, written to a USB
    stick rather than the installed system, for support without leaving traces.
11. **OEM mode** for schools that prepare many computers: install now, create the user
    on first boot.
