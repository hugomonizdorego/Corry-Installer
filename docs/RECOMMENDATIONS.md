<!-- SPDX-License-Identifier: CC0-1.0 -->
# Calamares and Debian review, recommendations (Corry 0.3)

Corry is a fork of Calamares 3.3.15. This page lists the Calamares and Debian
behaviors that were checked because they can break an installation, what Corry
does about each, and what should be added next.

## Checked and handled

| # | Risk in Calamares / Debian live installs | What Corry does |
| --- | --- | --- |
| 1 | The welcome step passed the raw "requirements satisfied" result as its Next state, so a failing check could also lock an unrelated page. | Found by running the real build: the step now reports its own verdict. The greeting never blocks; the System check page does. |
| 2 | QML files imported `QtQuick 2.3` but used newer properties; on Qt 5 the slideshow then failed to load. | Found by running the real build. All Corry QML imports `QtQuick 2.15`, valid on Qt 5.15 and Qt 6. |
| 3 | Calamares runs as root through `pkexec`, which drops the display and sound environment (no music, problems on Wayland, GParted). | The launcher prefers passwordless `sudo` (standard for Debian live users) and keeps `DISPLAY`, `WAYLAND_DISPLAY`, `XDG_RUNTIME_DIR` and the PulseAudio/PipeWire socket. `pkexec` remains the fallback. |
| 4 | `live-boot` left in the target breaks the first boot (it diverts `update-initramfs`). | `corrycleanup` purges the live packages before `initramfs` runs. |
| 5 | Live images ship only `grub-*-bin`; without `grub-pc`/`grub-efi-amd64`, kernel and GRUB updates stop updating the boot loader. | `corrygrub` installs the right package from the boot medium's pool, or online; if neither works but the GRUB files exist, it continues with a warning. |
| 6 | A broken image (no kernel, no way to get GRUB) is only discovered after the disk has been formatted. | `preflight.py` lists the squashfs before Calamares starts. A kernel and initramfs-tools must be in the image; GRUB may come from the image, the ISO's package pool or the internet. |
| 7 | Debian 12+ disables os-prober, so other systems disappear from the boot menu. | `grubcfg` writes `GRUB_DISABLE_OS_PROBER=false`. |
| 8 | Half-configured or broken packages in the image make the first boot or first update fail. | `corryupdate` always runs `dpkg --configure -a`; online it also runs `apt-get --fix-broken install` and updates. |
| 9 | `apt` inside the target can start services and has no DNS. | `corryupdate`, `corryinit` and `corrybootloader` add a temporary `policy-rc.d` and the live session's `resolv.conf`, and always restore both. |
| 10 | `full-upgrade` on Debian testing can remove packages during a transition. | The default is `upgrade --with-new-pkgs`, which never removes packages. Network failures are warnings, never errors. |
| 11 | BIOS + GPT without a `bios_grub` partition fails at `grub-install`, after formatting. | Erase-disk uses MBR on BIOS and GPT+ESP on UEFI. For manual GPT layouts on BIOS, Calamares' warning is kept. |
| 12 | The installed system still contains the installer (menu entries, desktop icons, `/etc/calamares`, the `calamares` package). | `corrycleanup` purges `calamares`/`calamares-settings-debian`, deletes every file in `/usr/lib/corry/manifest` and all launchers. |
| 13 | GParted changes disks behind Calamares' back. | The partition page re-reads all disks when GParted closes and discards the old plan. |
| 14 | An EFI partition without the ESP flag is not bootable. | The EFI role sets the boot/ESP flag automatically; 300 MiB is proposed and can be changed. |
| 15 | The launcher started the engine with `-c /etc/calamares`, a testing option that makes it look for QML only in `/etc/calamares/qml`. | The launcher no longer passes `-c`; CI starts the installed package to catch this. |
| 16 | Debian's `calamares-settings-debian` would stay next to Corry. | The packages conflict with and replace it; leftovers are deleted and its record purged. |
| 17 | Automated full-disk encryption is not tested with Debian's initramfs/GRUB integration. | Not offered in automatic mode yet. |
| 18 | **Switching the init system:** Debian's `elogind` conflicts with the `systemd` package itself, `systemd-sysv` is *Essential* on Debian 13 and testing, and apt refuses to remove manually installed packages on its own (a live image marks every package as manual). A plain `apt install sysvinit-core` therefore fails ("two conflicting assignments"). `dbus-user-session` depends on systemd, and without a session bus apt would drop dconf, GTK and the whole desktop. | `corryinit` asks for the removals explicitly (`systemd-sysv- libpam-systemd- systemd- libnss-systemd-`), passes `--allow-remove-essential`, installs `dbus-x11` (session bus), `rsyslog` and `cron` with the init system, and reads the simulation first. Proven by the probe and `init-switch` workflows on both bases. |
| 19 | The switch can drag the desktop along: GDM and GNOME require systemd, and other packages may depend on it. | The System page hides the alternatives when GDM/GNOME Shell is in the image; the job refuses again if they are installed, and refuses whenever apt would remove anything outside systemd's own family (the names are in the warning). systemd stays and the system boots. |
| 20 | After the switch two init systems or systemd leftovers could remain. | `/sbin/init` is verified to belong to the new package; systemd's packages are purged when that removes nothing else; otherwise they stay installed but inactive, with a warning. |
| 21 | Debian's `systemd-boot` package depends on the `systemd` package, which `elogind` removes. | systemd-boot is unavailable on the page as soon as another init system is chosen (and the job falls back to GRUB if apt cannot install it). |
| 22 | `refind` is not in every Debian suite (missing from testing at the time of writing). | When apt cannot install the loader, `corrybootloader` keeps GRUB and says so; the page notes it. |
| 23 | Secure Boot: Debian signs GRUB (and, since Debian 13, systemd-boot through shim), not rEFInd or EXTLINUX. | With Secure Boot on, only GRUB is offered. systemd-boot's shim path (`systemd-boot-efi-amd64-signed`) is prepared by Debian's own postinst after GRUB is purged (`dpkg-reconfigure systemd-boot`), but it is not validated yet: roadmap 0.5. |
| 24 | EXTLINUX cannot read Corry's compressed Btrfs; rEFInd has no XFS driver; systemd-boot keeps kernels on the EFI partition. | The page refuses EXTLINUX on compressed Btrfs and rEFInd on XFS `/boot`; `corrybootloader` needs 120 MB free on the ESP for systemd-boot, otherwise GRUB. |
| 25 | Kernel updates must keep the alternative loader working. | systemd-boot: Debian's `kernel-install` hooks, or Corry's own hooks when `kernel-install` is absent; EXTLINUX: Corry's `zz-corry-extlinux` hooks regenerate `extlinux.conf`; U-Boot: `u-boot-menu`'s hooks. |

## Recommended next steps

In order of benefit for a smooth installation:

1. **VM test matrix in CI** (roadmap 0.4). Boot real Edukasaun OS and DebION ISOs in
   QEMU with SeaBIOS and OVMF, install unattended with every init system and boot
   loader, and reboot. This is the only way to prove the whole chain works.
2. **Secure Boot on real firmware** (0.5): GRUB first, then systemd-boot through
   Debian's signed `systemd-boot-efi` and shim, then rEFInd with a MOK.
3. **An APT repository** for the Corry packages (signed with the distribution's key).
4. **Btrfs snapshots** (Snapper or Timeshift with `grub-btrfs`) so a broken update can
   be rolled back from the boot menu.
5. **Hardware support:** detect NVIDIA/Broadcom hardware and offer the drivers when
   online; include `firmware-linux` and `firmware-misc-nonfree` in the image.
6. **zram swap** for low-memory classroom computers.
7. **Translations** of Corry's own texts: Tetum, Bahasa Indonesia and Portuguese.
8. **Accessibility:** high-contrast theme and screen reader (Orca) on the live session.
9. **Tested full-disk encryption** (LUKS2 with `cryptsetup-initramfs`) before it is offered.
10. **An optional "save installation log" button** on the Finish page, written to a USB
    stick rather than the installed system.
11. **OEM mode** for schools that prepare many computers.
