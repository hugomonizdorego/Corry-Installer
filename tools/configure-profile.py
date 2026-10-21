#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
import argparse
from pathlib import Path
import re
import shutil
import yaml
from branding import ROOT, compile_brand
from apt_support import selected_packages


def configure(source, output, image, distro):
    if not Path(image).is_absolute():raise ValueError('The live image path must be absolute')
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    data=compile_brand(source,output/'branding/corry')
    shutil.copy2(ROOT/'config/corry/settings.conf',output/'settings.conf')
    shutil.copytree(ROOT/'config/corry/modules',output/'modules',dirs_exist_ok=True)
    catalog_path=Path(source)/'software.yaml'
    if not catalog_path.is_file():catalog_path=ROOT/'config/corry/software.yaml'
    catalog=yaml.safe_load(catalog_path.read_text())
    ids=[g['id'] for g in catalog['groups']]
    if any(not re.fullmatch(r'[a-z0-9][a-z0-9-]*',p) for p in ids) or len(set(ids))!=len(ids):raise ValueError('Software group IDs must be unique lowercase names')
    selected_packages(catalog,','.join(ids))
    for group in catalog['groups']:
        photo=output/'branding/corry'/str(group.get('screenshot',''))
        if not photo.is_file() or not photo.resolve().is_relative_to((output/'branding/corry').resolve()):group['screenshot']=data['welcome']['image']
    def write(path,value):(output/path).write_text(yaml.safe_dump(value,sort_keys=False,allow_unicode=True))
    write('corry-software.yaml',catalog)
    intro={'id':'','name':'Pilih aplikasi tambahan','description':'Klik untuk memilih; klik lagi untuk membatalkan. Paket tambahan diunduh sebelum partisi diubah. Anda dapat melanjutkan tanpa paket tambahan jika image dasar lengkap.','screenshot':data['welcome']['image']}
    write('modules/packagechooser.conf',{'mode':'optionalmultiple','method':'legacy','corryRepositories':True,'labels':{'step':'Software','step[id]':'Aplikasi'},'items':[intro]+catalog['groups']})
    write('modules/unpackfs.conf',{'unpack':[{'source':image,'sourcefs':'squashfs','destination':''}]})
    for job in ['corryprepare','corrypackages']:write(f'modules/{job}.conf',{'image':image,'catalog':'/etc/calamares/corry-software.yaml'})
    welcome=yaml.safe_load((output/'modules/welcome.conf').read_text());welcome.update(corryWelcomeTitle=data['welcome']['title'],corryWelcomeDescription=data['welcome']['description']);write('modules/welcome.conf',welcome)
    finished=yaml.safe_load((output/'modules/finished.conf').read_text());finished.update(corryFinishedTitle=data['finish']['title'],corryFinishedDescription=data['finish']['description'],corryContinueLiveText=data['finish']['continueLive'],corryRestartText=data['finish']['restart']);write('modules/finished.conf',finished)
    (output/'corry-distro').write_text(distro+'\n')


def main():
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--image',required=True);p.add_argument('--distro',required=True);a=p.parse_args()
    try:configure(a.source,a.output,a.image,a.distro)
    except (OSError,ValueError,KeyError,TypeError,yaml.YAMLError) as exc:p.exit(1,'Profile error: '+str(exc)+'\n')

if __name__=='__main__':main()
