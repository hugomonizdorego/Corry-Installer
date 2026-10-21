#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
repo=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
destination=${DESTDIR:-}
image=/run/live/medium/live/filesystem.squashfs
distro=debion
while [[ $# -gt 0 ]]; do
 case "$1" in
  --image) [[ $# -ge 2 && $2 == /* ]] || { echo '--image requires an absolute path' >&2; exit 2; }; image=$2; shift 2;;
  --distro) [[ $# -ge 2 ]] || exit 2; distro=$2; shift 2;;
  *) echo 'Usage: install-profile.sh [--distro edukasaun|debion] [--image /absolute/image.squashfs]' >&2; exit 2;;
 esac
done
case "$distro" in edukasaun|debion) ;; *) echo 'Unknown distribution profile' >&2; exit 2;; esac
[[ -n $destination || $EUID == 0 ]] || { echo 'Run as root or set DESTDIR for staging.' >&2; exit 1; }
config="$destination/etc/calamares"
if [[ -f $config/settings.conf ]]; then
 backup="$config/backup-corry-$(date +%Y%m%d-%H%M%S)-$$"
 mkdir -p "$backup"
 cp -a "$config/settings.conf" "$backup/"
 for item in modules branding corry-software.yaml; do
  [[ ! -e $config/$item ]] || cp -a "$config/$item" "$backup/"
 done
fi
install -d "$config/modules" "$config/branding/corry" "$destination/usr/bin" "$destination/usr/lib/corry" "$destination/usr/share/applications"
install -m644 "$repo/config/corry/settings.conf" "$config/settings.conf"
install -m644 "$repo/config/corry/modules/"*.conf "$config/modules/"
# Replace product assets together so switching an ISO profile cannot mix images.
rm -rf -- "$config/branding/corry/slides"
cp -r "$repo/src/branding/corry/". "$config/branding/corry/"
cp -r "$repo/config/distros/$distro/slides" "$config/branding/corry/"
install -m644 "$repo/config/distros/$distro/branding.desc" "$config/branding/corry/branding.desc"
install -m644 "$repo/config/distros/$distro/software.yaml" "$config/corry-software.yaml"
python3 - "$repo" "$config" "$image" "$distro" <<'INNER'
import json, pathlib, sys, yaml
repo, config = map(pathlib.Path, sys.argv[1:3]); image, distro=sys.argv[3:]
(config/'modules/unpackfs.conf').write_text(yaml.safe_dump({'unpack':[{'source':image,'sourcefs':'squashfs','destination':''}]},sort_keys=False))
for job in ['corryprepare','corrypackages']:
 (config/f'modules/{job}.conf').write_text(yaml.safe_dump({'image':image,'catalog':'/etc/calamares/corry-software.yaml'}))
catalog=yaml.safe_load((config/'corry-software.yaml').read_text())
intro={'id':'','name':'Pilih aplikasi tambahan','description':'Klik aplikasi untuk memilih; klik lagi untuk membatalkan. Tidak memilih apa pun memungkinkan instalasi offline jika image dasar lengkap. Pemeriksaan repositori dapat dicoba ulang.','screenshot':'slides/welcome.svg'}
chooser={'mode':'optionalmultiple','method':'legacy','corryRepositories':True,'labels':{'step':'Software','step[id]':'Aplikasi'},'items':[intro]+catalog['groups']}
(config/'modules/packagechooser.conf').write_text(yaml.safe_dump(chooser,sort_keys=False,allow_unicode=True))
profile=yaml.safe_load((repo/f'config/distros/{distro}/profile.yaml').read_text())
qss=(config/'branding/corry/stylesheet.qss').read_text().replace('#6445a4',profile['accent']).replace('#f0ecf8',profile['tint'])
(config/'branding/corry/stylesheet.qss').write_text(qss)
mark=config/'branding/corry/corry-mark.svg'
mark.write_text(mark.read_text().replace('#6445a4',profile['accent']))
(config/'corry-distro').write_text(distro+'\n')
slides=config/'branding/corry/slides'
entries=json.loads((slides/'slides.json').read_text())
if not entries:
 raise SystemExit('A distribution must provide at least one slideshow image')
for entry in entries:
 image=pathlib.Path(entry['image'])
 if image.is_absolute() or '..' in image.parts or not (slides/image).is_file():
  raise SystemExit('Invalid local slideshow image: '+str(image))
(slides/'Slides.js').write_text('// SPDX-License-Identifier: CC0-1.0\nvar slides = '+json.dumps(entries,ensure_ascii=False)+';\n')
INNER
install -m755 "$repo/tools/preflight.py" "$repo/tools/repository-check.py" "$destination/usr/lib/corry/"
install -m644 "$repo/tools/apt_support.py" "$destination/usr/lib/corry/apt_support.py"
install -m755 "$repo/tools/corry-installer" "$destination/usr/bin/corry-installer"
install -m644 "$repo/config/corry/corry-installer.desktop" "$destination/usr/share/applications/corry-installer.desktop"
echo "Corry profile installed for $distro. Run corry-installer from the live session."
