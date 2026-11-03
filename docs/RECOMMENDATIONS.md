<!-- SPDX-License-Identifier: CC0-1.0 -->
# Calamares and Debian review, recommendations (Corry 1.0)

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
| 19 | The switch can drag the desktop along: GDM and GNOME require systemd, and other packages may depend on it. | The Init system page disables the alternatives when GDM/GNOME Shell is in the image; the job refuses again if they are installed, and refuses whenever apt would remove anything outside systemd's own family (the names are in the warning). systemd stays and the system boots. |
| 20 | After the switch two init systems or systemd leftovers could remain. | `/usr/sbin/init` is verified to be shipped by the new init package (runit's is a link to a file of the `runit` package, so the link's owner counts); systemd's packages are purged when that removes nothing else; otherwise they stay installed but inactive, with a warning. |
| 21 | Debian's `systemd-boot` package depends on the `systemd` package, which `elogind` removes. | systemd-boot is unavailable on the page as soon as another init system is chosen (and the job falls back to GRUB if apt cannot install it). |
| 22 | `refind` is not in every Debian suite (missing from testing at the time of writing); U-Boot is for ARM boards, but Corry's packages are amd64. | Each option lists the bases whose archive has it (`availableOn`); the page offers only those, and CI checks the list against the real archives. U-Boot is not offered. When apt still cannot install a loader, `corrybootloader` keeps GRUB and says so. |
| 23 | Secure Boot: Debian signs GRUB (and, since Debian 13, systemd-boot through shim), not rEFInd or EXTLINUX. | With Secure Boot on, only GRUB is offered; the removable-media path gets the whole shim chain (shim, signed GRUB, MokManager, the config stub), since the firmware trusts only shim. systemd-boot's shim path is prepared by Debian's own postinst after GRUB is purged (`dpkg-reconfigure systemd-boot`), not validated on real firmware yet. |
| 24 | EXTLINUX cannot read Corry's compressed Btrfs; rEFInd has no XFS driver; neither reads LUKS; systemd-boot keeps kernels on the EFI partition. | The page reads the planned layout and refuses these cases; `corrybootloader` checks again with the real partition list before downloading, and needs 120 MB free on the ESP for systemd-boot, otherwise GRUB. |
| 25 | Kernel updates must keep the alternative loader working. | systemd-boot: Debian's `kernel-install` hooks, or Corry's own hooks when `kernel-install` is absent; EXTLINUX: Corry's `zz-corry-extlinux` hooks regenerate `extlinux.conf`. |
| 26 | Calamares 3.3's `target_env_process_output` returns the exit code, not the output (its docstring says otherwise). Corry's jobs read text from it, so every alternative init system failed with a TypeError in a real installation, while tests with a fake that returned text passed. | Output is read with `check_target_env_output`; the test fakes and `tools/ci/run-job.py` now behave exactly like the real API; the `e2e` job runs the real modules. |
| 27 | GRUB's EFI directory must match what Debian's grub-efi upgrades derive from `GRUB_DISTRIBUTOR` (its first word, lowercased); otherwise updates write a second copy and the first goes stale. | `efiBootloaderId` and `corrybootloader`'s `grubEfiDirectory` follow `bootloader-name` (`EFI/debion`, `EFI/edukasaun`); `bootloader-name` is "DebION"/"Edukasaun" because GRUB adds " GNU/Linux". |
| 28 | `keyscript=/bin/cat` in crypttab reads a key file that only the luksbootkeyfile module creates; without it an encrypted root cannot be unlocked. | crypttab gets `luks` only; the initramfs asks for the passphrase. |
| 29 | A reused EFI partition holds other systems' `EFI/debian` and boot entries; GRUB is not on the ESP yet when an alternative loader replaces it. | Only an EFI partition formatted by this installation is cleaned, and only its own firmware entry is removed. |
| 30 | Fixed timeouts kill `apt-get` and dpkg mid-transaction on a slow line. | Downloads first (interruptible), then installs without a time limit. |
| 31 | Packages that came into the live image only as Corry's dependencies stay "automatically installed" after Corry is purged; `apt autoremove` would then remove lvm2 or cryptsetup-initramfs and the system would not boot. | `corrycleanup` marks the system's own tools as manually installed first. |
| 32 | Qt's SVG image plugin is not a library dependency, and `qt6-svg-plugins \| libqt6svg6` is satisfied by the library alone: SVG logos, slides and icons stay blank. | The package that ships `libqsvg.so` is found at build time and named in Depends; CI checks that the plugin is installed. |
| 33 | `postinst` ran `install -d -o USER` as root on paths in users' homes; a symbolic link or `XDG_DESKTOP_DIR` could make root change another directory. | Every file in a home is written by its owner (`runuser`). |
| 34 | The partition page fills global storage `partitions` only when the installation starts, so later pages cannot see the plan. | The partition page publishes `corryPlannedPartitions` (`/`, `/boot`, filesystem, encryption) when it is left. |
| 35 | 32-bit UEFI (tablets with a 64-bit CPU) needs GRUB's `i386-efi` platform; Debian has no signed shim for it. | `corrygrub` installs `grub-efi-ia32` there and no shim; the alternatives are not offered. |
| 36 | A failed installation gave no log the user could find, and Calamares quit when the error dialog closed. | The whole log goes to `/tmp/Corry/install.log`, owned by the user, with **Open log**; Corry stays on the Finished page. Crashes and preflight failures are logged there too. |

## Recommended next steps

In order of benefit for a smooth installation:

1. **Real-hardware matrix before each release**: UEFI with Secure Boot on, dual boot
   with Windows, encrypted `/`, OpenRC and runit desktops, rEFInd and EXTLINUX, slow
   internet (see the checklist in [CORRY-DEVELOPMENT.md](CORRY-DEVELOPMENT.md)).
2. **ISO-level CI**: build a live ISO with live-build in CI, boot it in QEMU and drive
   Corry's pages with the same unattended settings the `e2e` job uses, so the pages
   (not only the jobs) are part of the test.
3. **An APT repository** for the Corry packages, signed with the distribution's key,
   so live images and installed systems get fixes through apt.
4. **Translations** of Corry's own texts: Tetum, Bahasa Indonesia and Portuguese
   (the strings already go through Qt's translation system).

## Recommended features

Additions that fit Corry's purpose (schools and home users, often offline):

| Feature | Why |
| --- | --- |
| **Btrfs snapshots** with Snapper or Timeshift and `grub-btrfs` | Roll back a broken update from the boot menu; Corry already lays out `@`, `@home`, `@log`, `@cache` |
| **zram swap** (`zram-tools`) on computers with little memory | Classroom computers with 2–4 GB stay responsive without a swap partition |
| **Driver assistant** when online (NVIDIA, Broadcom Wi-Fi, firmware) | Graphics and wireless work after the first boot |
| **Automatic encryption** in Erase disk (LUKS2, `cryptsetup-initramfs`, one passphrase) | Laptops that leave the school; the manual path already works |
| **OEM mode** | A school prepares many computers; each pupil creates the account at first boot |
| **Unattended install file** (the `e2e` job's global storage as a template) | Mass deployment from a USB stick without clicks |
| **Copy the log to a USB stick** from the Finished page | `/tmp` is lost at restart on a live system |
| **High-contrast theme** and Orca on the live session | Accessibility; the theme system makes a third theme a YAML file |
| **Language packs** and keyboard layouts chosen from the location | Offline installs in Tetum or Indonesian get spell-checkers and fonts |
| **Restore a `/home` from a backup** during installation | Reinstall without losing the user's files |
