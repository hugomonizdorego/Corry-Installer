#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
# End-to-end test of an installation with Corry's real job modules.
#
#   tools/ci/e2e-install.sh DISTRO FIRMWARE INIT LOADER [FILESYSTEM]
#     DISTRO      edukasaun | debion (the corry-<distro> package must be installed)
#     FIRMWARE    efi | bios
#     INIT        systemd | sysvinit (an option of the Init system page)
#     LOADER      grub | systemd-boot | refind | extlinux (an option of the Boot loader page)
#     FILESYSTEM  btrfs (default, Corry's default) | ext4
#
# Builds a small Debian live image (debootstrap + squashfs), partitions a disk
# image as Corry's "Erase disk" does, runs the installation jobs in the order
# of /etc/calamares/settings.conf with Calamares' loadmodule (global storage is
# carried from job to job), then boots the disk in QEMU and waits for the
# installed system to report itself on the serial console.
#
# The pages' jobs that need a person (partitioning, keyboard, users) are done
# here directly. Runs as root in a throw-away privileged container only: it
# uses loop devices and mounts. Set E2E_WORK to keep the files elsewhere.
set -euo pipefail
distro=$1 firmware=$2 init=$3 loader=$4 fs=${5:-btrfs}
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)
work=${E2E_WORK:-/tmp/corry-e2e}
loadmodule=${LOADMODULE:-$work/loadmodule}
base=$(python3 -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))["debian"])' "$repo/config/distros/$distro/distro.yaml")
log() { printf '\n=== %s\n' "$*"; }
mkdir -p "$work"

# Firmware the container must not touch: grub-install and efibootmgr would
# otherwise write the boot entries of the machine running the test. Without
# efivars Corry's bootloader retries with --no-nvram and the disk boots from
# the removable-media path, as QEMU with empty firmware variables needs.
if [[ -d /sys/firmware/efi ]]; then
 mount -t tmpfs none /sys/firmware/efi 2>/dev/null || true
fi

log "Live image: Debian $base"
medium=$work/medium
if [[ ! -f $medium/live/filesystem.squashfs ]]; then
 rootfs=$work/rootfs
 rm -rf "$rootfs"
 debootstrap --variant=minbase --include=ca-certificates "$base" "$rootfs" http://deb.debian.org/debian \
  || { tail -n 40 "$rootfs/debootstrap/debootstrap.log"; exit 1; }
 # What a live image has: a kernel, an init system and the tools the jobs use.
 mount -t proc proc "$rootfs/proc"
 mount --bind /dev "$rootfs/dev"
 printf '#!/bin/sh\nexit 101\n' > "$rootfs/usr/sbin/policy-rc.d"; chmod 755 "$rootfs/usr/sbin/policy-rc.d"
 chroot "$rootfs" env DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
  linux-image-amd64 initramfs-tools systemd-sysv udev kmod dbus locales keyboard-configuration sudo \
  grub-common grub-pc-bin grub-efi-amd64-bin efibootmgr btrfs-progs dosfstools e2fsprogs
 rm -f "$rootfs/usr/sbin/policy-rc.d"
 umount "$rootfs/dev" "$rootfs/proc"
 # The marker: the installed system reports its init and powers off.
 cat > "$rootfs/etc/systemd/system/corry-e2e.service" <<'EOF'
[Unit]
Description=Corry end-to-end test marker
After=multi-user.target
[Service]
Type=oneshot
ExecStart=/bin/sh -c 'echo "CORRY-E2E-BOOTED init=$(readlink -f /sbin/init) root=$(findmnt -no FSTYPE /)" | tee /dev/ttyS0 /dev/console'
ExecStartPost=/bin/systemctl --no-block poweroff
[Install]
WantedBy=multi-user.target
EOF
 ln -sf ../corry-e2e.service "$rootfs/etc/systemd/system/multi-user.target.wants/corry-e2e.service"
 cat > "$rootfs/etc/rc.local" <<'EOF'
#!/bin/sh
# Corry end-to-end test marker for init systems other than systemd.
echo "CORRY-E2E-BOOTED init=$(readlink -f /sbin/init) root=$(findmnt -no FSTYPE /)" | tee /dev/ttyS0 /dev/console
( sleep 3; poweroff ) &
exit 0
EOF
 chmod 755 "$rootfs/etc/rc.local"
 chroot "$rootfs" apt-get clean
 mkdir -p "$medium/live"
 mksquashfs "$rootfs" "$medium/live/filesystem.squashfs" -comp zstd -noappend -quiet
 rm -rf "$rootfs"
fi
ls -lh "$medium/live/filesystem.squashfs"

log "Disk: $firmware, / on $fs"
disk=$work/disk.img
rm -f "$disk"
truncate -s 8G "$disk"
if [[ $firmware == efi ]]; then
 parted -s "$disk" mklabel gpt mkpart ESP fat32 1MiB 301MiB set 1 esp on mkpart root "$fs" 301MiB 100%
else
 parted -s "$disk" mklabel msdos mkpart primary "$fs" 1MiB 100% set 1 boot on
fi
loop=$(losetup -fP --show "$disk")
# A container's /dev does not get the partition nodes from udev.
for sys in /sys/block/"$(basename "$loop")"/"$(basename "$loop")"p*; do
 node=/dev/$(basename "$sys")
 [[ -b $node ]] || mknod "$node" b "$(cut -d: -f1 "$sys/dev")" "$(cut -d: -f2 "$sys/dev")"
done
cleanup() {
 set +e
 grep " $work/" /proc/mounts | awk '{print $2}' | sort -r | xargs -r -n1 umount -l
 grep ' /tmp/calamares-root' /proc/mounts | awk '{print $2}' | sort -r | xargs -r -n1 umount -l
 losetup -d "$loop"
}
trap cleanup EXIT
if [[ $firmware == efi ]]; then esp=${loop}p1 root=${loop}p2; else esp= root=${loop}p1; fi
[[ -z $esp ]] || mkfs.vfat -F 32 -n EFI "$esp" >/dev/null
if [[ $fs == btrfs ]]; then mkfs.btrfs -f -L root "$root" >/dev/null; else mkfs.ext4 -F -q -L root "$root"; fi
uuid() { blkid -s UUID -o value "$1"; }
partuuid() { blkid -s PARTUUID -o value "$1"; }
# What udev would create on a live system.
mkdir -p /dev/disk/by-uuid /dev/disk/by-partuuid
for part in $esp $root; do
 ln -sf "$part" "/dev/disk/by-uuid/$(uuid "$part")"
 ln -sf "$part" "/dev/disk/by-partuuid/$(partuuid "$part")"
done

log "Global storage, as the pages leave it"
conf=$work/conf
rm -rf "$conf"; cp -r /etc/calamares "$conf"
gs=$work/global.yaml
python3 - "$gs" "$conf" "$repo" "$firmware" "$init" "$loader" "$fs" "$loop" "$esp" "$root" \
 "$( [[ -z $esp ]] || uuid "$esp")" "$( [[ -z $esp ]] || partuuid "$esp")" "$(uuid "$root")" "$(partuuid "$root")" \
 "$medium" <<'PY'
import sys, yaml
from pathlib import Path
(gs, conf, repo, firmware, init, loader, fs, loop, esp, root,
 esp_uuid, esp_partuuid, root_uuid, root_partuuid, medium) = sys.argv[1:]
conf = Path(conf)
modules = conf / 'modules'
desc = yaml.safe_load((conf / 'branding/corry/branding.desc').read_text())
partitions = []
if esp:
    partitions.append({'device': esp, 'fs': 'fat32', 'fsName': 'fat32', 'mountPoint': '/boot/efi', 'uuid': esp_uuid,
                       'partuuid': esp_partuuid, 'claimed': True, 'features': {}, 'partattrs': 0, 'parttype': ''})
partitions.append({'device': root, 'fs': fs, 'fsName': fs, 'mountPoint': '/', 'uuid': root_uuid,
                   'partuuid': root_partuuid, 'claimed': True, 'features': {}, 'partattrs': 0, 'parttype': ''})

def option(page, section, wanted):
    data = yaml.safe_load((modules / page).read_text())
    chosen = next(o for o in data[section] if o['id'] == wanted)
    return {'id': chosen['id'], 'name': chosen['name'], 'packages': chosen.get('packages', []),
            'default': bool(chosen.get('default')), 'filesystems': chosen.get('filesystems', [])}

storage = {
    'partitions': partitions,
    'firmwareType': firmware,
    'efiSystemPartition': '/boot/efi',
    'branding': dict(desc['strings']),
    'username': 'hugo',
    'hostname': 'corry-e2e',
    'localeConf': {'LANG': 'en_US.UTF-8', 'LC_TIME': 'en_US.UTF-8'},
    'locationRegion': 'Asia', 'locationZone': 'Dili',
    'hasInternet': True,
    'corrySystem': {'init': option('corrysystem-init.conf', 'init', init),
                    'bootloader': option('corrysystem-bootloader.conf', 'bootloader', loader),
                    'online': True},
}
if firmware == 'bios':
    storage['bootLoader'] = {'installPath': loop}
Path(gs).write_text(yaml.safe_dump(storage, sort_keys=False))

# The test's own medium and a serial console for the boot check.
def change(name, update):
    path = modules / name
    data = yaml.safe_load(path.read_text())
    update(data)
    path.write_text(yaml.safe_dump(data, sort_keys=False))
change('unpackfs.conf', lambda d: d['unpack'][0].update(source=medium + '/live/filesystem.squashfs'))
# The target must not see the firmware variables of the machine running the test.
change('mount.conf', lambda d: d.update(extraMounts=[m for m in d.get('extraMounts', []) if m.get('fs') != 'efivarfs']))
change('corrygrub.conf', lambda d: d.update(medium=medium))
change('grubcfg.conf', lambda d: (d.update(kernel_params=['console=ttyS0,115200']),
                                    d.setdefault('defaults', {}).update(GRUB_TERMINAL='serial console',
                                                                        GRUB_SERIAL_COMMAND='serial --unit=0 --speed=115200',
                                                                        GRUB_TIMEOUT=2)))
change('bootloader.conf', lambda d: d.update(kernelParams=['console=ttyS0,115200']))
change('corrybootloader.conf', lambda d: d.update(kernelParams=['console=ttyS0,115200']))
print(yaml.safe_dump(storage, sort_keys=False))
PY

run() {
 local module=$1
 log "Job: $module"
 local config=$conf/modules/$module.conf
 [[ -f $config ]] || config=
 # -P: run commands for real (no injected subprocess stubs).
 (cd "$work" && "$loadmodule" -P -S "$conf/settings.conf" -g "$gs" -G "$gs" "$module" ${config:+"$config"}) \
  > "$work/job-$module.log" 2>&1 || { tail -n 60 "$work/job-$module.log"; echo "FAILED: $module"; exit 1; }
 grep -E 'WARNING|ERROR' "$work/job-$module.log" | grep -v 'No Branding\|nullptr JobQueue' | tail -n 20 || true
}
target() { python3 -c 'import sys, yaml; print(yaml.safe_load(open(sys.argv[1]))["rootMountPoint"])' "$gs"; }

# The installation, in the order of settings.conf. "partition" is done above;
# keyboard and the user account are what their pages' jobs would do.
for module in $(python3 -c 'import sys, yaml; print(" ".join(yaml.safe_load(open(sys.argv[1]))["sequence"][1]["exec"]))' \
                "$conf/settings.conf"); do
 case $module in
  partition|locale|keyboard|displaymanager) echo "(skipped in this test: $module)";;
  users)
   log "Job: users (account)"
   chroot "$(target)" useradd -m -s /bin/bash -G sudo hugo
   echo 'hugo:corry-e2e' | chroot "$(target)" chpasswd
   echo corry-e2e > "$(target)/etc/hostname";;
  umount)
   log "Boot configuration of the installed system"
   t=$(target)
   echo "--- /etc/fstab"; grep -v '^#' "$t/etc/fstab" || true
   echo "--- /etc/crypttab"; grep -v '^#' "$t/etc/crypttab" 2>/dev/null || true
   echo "--- kernels"; ls "$t/boot" || true
   echo "--- grub.cfg entries"; grep -E "^\s*(linux|search|menuentry)" "$t/boot/grub/grub.cfg" 2>/dev/null | head -12 || true
   echo "--- /etc/default/grub"; grep -E "^GRUB_" "$t/etc/default/grub" 2>/dev/null || true
   echo "--- EFI partition"; find "$t/boot/efi" -maxdepth 4 2>/dev/null | head -40 || true
   for f in "$t"/boot/efi/EFI/*/grub.cfg; do [[ -f $f ]] && { echo "--- $f"; cat "$f"; }; done
   [[ ! -d $t/boot/efi/loader ]] || { echo "--- systemd-boot"; cat "$t/boot/efi/loader/loader.conf" "$t"/boot/efi/loader/entries/*.conf || true; }
   for m in bootloader corrybootloader corrygrub grubcfg; do
    [[ -f $work/job-$m.log ]] && { echo "--- job-$m.log (warnings)"; grep -E "WARNING|ERROR|grub-install|Installing for|No error" "$work/job-$m.log" | tail -n 15 || true; }
   done
   run umount;;
  *) run "$module";;
 esac
done
python3 - "$gs" <<'PY'
import sys, yaml
system = yaml.safe_load(open(sys.argv[1])).get('corrySystem', {})
for section in ('init', 'bootloader'):
    print(section, '->', (system.get(section) or {}).get('installed') or (system.get(section) or {}).get('id'),
          (system.get(section) or {}).get('message', ''))
PY
cleanup; trap - EXIT

log "Boot the installed disk"
serial=$work/serial.log
rm -f "$serial"
qemu=(qemu-system-x86_64 -m 2048 -smp 2 -accel kvm -accel tcg -display none -monitor none -no-reboot
      -serial "file:$serial" -drive "file=$disk,format=raw,if=virtio")
if [[ $firmware == efi ]]; then
 code=$(ls /usr/share/OVMF/OVMF_CODE_4M.fd /usr/share/OVMF/OVMF_CODE.fd 2>/dev/null | head -1)
 vars=$work/vars.fd
 cp "$(ls /usr/share/OVMF/OVMF_VARS_4M.fd /usr/share/OVMF/OVMF_VARS.fd 2>/dev/null | head -1)" "$vars"
 qemu+=(-drive "if=pflash,format=raw,readonly=on,file=$code" -drive "if=pflash,format=raw,file=$vars")
fi
timeout "${E2E_BOOT_TIMEOUT:-900}" "${qemu[@]}" || echo "QEMU ended with $?"
echo "--- last lines of the serial console"
tail -n 40 "$serial" || true
marker=$(grep -a 'CORRY-E2E-BOOTED' "$serial" | head -1 || true)
[[ -n $marker ]] || { echo "The installed system did not report that it booted."; exit 1; }
echo "$marker"
# /sbin/init resolves to systemd's binary, or to SysVinit's own /usr/sbin/init.
case $init in
 systemd) [[ $marker == *"init=/usr/lib/systemd/systemd"* ]] || { echo "Expected systemd in: $marker"; exit 1; };;
 sysvinit) [[ $marker == *"init=/usr/sbin/init"* ]] || { echo "Expected SysVinit in: $marker"; exit 1; };;
esac
[[ $marker == *"root=$fs"* ]] || { echo "Unexpected root filesystem in: $marker"; exit 1; }
echo "End-to-end installation of $distro ($firmware, $init, $loader, $fs) booted."
