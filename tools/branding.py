#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Compile one editable distro branding.yaml into native/QML installer assets."""
import argparse
import json
from pathlib import Path
import re
import shutil
import subprocess
import yaml

ROOT=Path(__file__).resolve().parents[1]
COMMON=ROOT/'src/branding/corry'
DEFAULT_PALETTE={'accent':'#08786f','hover':'#075e57','tint':'#e6f4f1','soft':'#9fcfc5'}


def local_asset(folder, name, extensions, optional=False):
    if optional and not name:return None
    if not isinstance(name,str) or not name or Path(name).is_absolute():raise ValueError('Use a relative local asset path: '+str(name))
    path=(folder/name).resolve()
    if not path.is_relative_to(folder.resolve()) or not path.is_file():raise ValueError('Missing or unsafe branding asset: '+name)
    if path.suffix.lower() not in extensions:raise ValueError('Unsupported branding asset type: '+name)
    return path


def inspect_media(path, kind):
    if path is None:return
    if not shutil.which('ffprobe'):raise ValueError('Install ffmpeg to validate video/music before compiling branding.')
    try:
        result=subprocess.run(['ffprobe','-v','error','-show_streams','-of','json',str(path)],capture_output=True,text=True,timeout=20,check=True)
        streams=json.loads(result.stdout)['streams']
        codecs={'video':{'vp8','vp9','h264'},'audio':{'vorbis','opus','pcm_s16le','mp3','flac','aac'}}
        if not any(s.get('codec_type')==kind and s.get('codec_name') in codecs[kind] for s in streams):raise ValueError('Unsupported '+kind+' codec: '+str(path))
    except (subprocess.SubprocessError,KeyError,json.JSONDecodeError) as exc:raise ValueError('Invalid media file: '+str(path)) from exc


def load(folder):
    folder=Path(folder).resolve();data=yaml.safe_load((folder/'branding.yaml').read_text())
    if not isinstance(data,dict):raise ValueError('branding.yaml must contain a mapping')
    name=data['product']['name']
    if not isinstance(name,str) or not name.strip():raise ValueError('product.name must not be empty')
    palette={**DEFAULT_PALETTE,**data.get('palette',{})}
    for color in palette.values():
        if not isinstance(color,str) or not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise ValueError('Palette colors must use #RRGGBB')
    data['palette']=palette
    assets=set()
    def image(name):
        path=local_asset(folder,name,{'.svg','.png','.jpg','.jpeg','.webp'});assets.add(name);return path
    image(data['product']['logo']);image(data['welcome']['image'])
    for section in ['welcome','finish']:
        for key in ['title','description']:
            if not isinstance(data[section][key],str):raise ValueError(section+'.'+key+' must be text')
            data[section][key]=data[section][key].replace('{product}',name)
    installation=data['installation']
    installation.setdefault('music','')
    installation.setdefault('musicEnabled',False)
    installation.setdefault('musicVolume',20)
    installation.setdefault('slideInterval',9000)
    installation.setdefault('eyebrow','INSTALLING YOUR SYSTEM')
    data['welcome'].setdefault('video','')
    data['welcome'].setdefault('videoAutoplay',False)
    data['welcome'].setdefault('videoMuted',True)
    for section,keys in [('installation',['eyebrow']),('finish',['continueLive','restart'])]:
        for key in keys:
            if not isinstance(data[section][key],str):raise ValueError(section+'.'+key+' must be text')
    volume=installation.get('musicVolume',20)
    if isinstance(volume,bool) or not isinstance(volume,(int,float)) or not 0<=volume<=100:raise ValueError('musicVolume must be between 0 and 100')
    interval=installation.get('slideInterval',9000)
    if isinstance(interval,bool) or not isinstance(interval,int) or not 3000<=interval<=120000:raise ValueError('slideInterval must be 3000–120000 ms')
    for section,key in [('welcome','videoAutoplay'),('welcome','videoMuted'),('installation','musicEnabled')]:
        if not isinstance(data[section].get(key,False),bool):raise ValueError(section+'.'+key+' must be true or false')
    slides=installation['slides']
    if not isinstance(slides,list) or not slides:raise ValueError('Provide at least one installation slide')
    for slide in slides:
        image(slide['image'])
        for key in ['title','description']:
            if not isinstance(slide[key],str):raise ValueError('Slide text must be a string')
            slide[key]=slide[key].replace('{product}',name)
    for section,key,extensions,kind in [('welcome','video',{'.webm','.mp4'},'video'),('installation','music',{'.ogg','.wav','.mp3','.flac'},'audio')]:
        value=data[section].get(key,'')
        media=local_asset(folder,value,extensions,optional=True)
        inspect_media(media,kind)
        if media:assets.add(value)
    return data,assets


def compile_brand(folder, output):
    folder=Path(folder).resolve();output=Path(output)
    data,assets=load(folder)  # Validate before changing the output or system profile.
    output.mkdir(parents=True,exist_ok=True)
    for p in COMMON.iterdir():
        if p.is_file() and p.suffix in {'.qml','.svg'}:shutil.copy2(p,output/p.name)
    for name in assets:
        target=output/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(folder/name,target)
    palette=data['palette'];qss=(COMMON/'stylesheet.qss.in').read_text()
    for key,color in palette.items():qss=qss.replace('@'+key+'@',color)
    (output/'stylesheet.qss').write_text(qss)
    (output/'Brand.js').write_text('// Generated from branding.yaml; do not edit.\nvar config = '+json.dumps(data,ensure_ascii=True)+';\n')
    (output/'brand.json').write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    desc=yaml.safe_load((COMMON/'branding.desc').read_text())
    for key in ['productName','shortProductName','versionedName','shortVersionedName','bootloaderEntryName']:desc['strings'][key]=data['product']['name']
    desc['strings']['productUrl']=data['product'].get('url','');desc['strings']['supportUrl']=data['product'].get('supportUrl','')
    desc['images']={'productIcon':data['product']['logo'],'productLogo':data['product']['logo'],'productWelcome':data['welcome']['image']}
    desc['style']={'SidebarBackground':'#ffffff','SidebarText':'#526970','SidebarTextCurrent':palette['accent'],'SidebarBackgroundCurrent':palette['tint']}
    (output/'branding.desc').write_text(yaml.safe_dump(desc,sort_keys=False,allow_unicode=True))
    return data


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--source',type=Path,required=True);parser.add_argument('--output',type=Path);args=parser.parse_args()
    try:
        data=compile_brand(args.source,args.output) if args.output else load(args.source)[0]
    except (OSError,KeyError,TypeError,ValueError,yaml.YAMLError) as exc:parser.exit(1,'Branding error: '+str(exc)+'\n')
    print('Branding valid: '+data['product']['name'])

if __name__=='__main__':main()
