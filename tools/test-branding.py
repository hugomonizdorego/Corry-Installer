#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
from pathlib import Path
import json
import os
import shutil
import subprocess
import tempfile
import unittest
import yaml
from branding import ROOT, compile_brand, load


class BrandingTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.source=self.root/'brand';shutil.copytree(ROOT/'config/distros/debion',self.source)
        self.file=self.source/'branding.yaml';self.data=yaml.safe_load(self.file.read_text())
    def tearDown(self):self.temp.cleanup()
    def save(self):self.file.write_text(yaml.safe_dump(self.data,allow_unicode=True))
    def test_text_photos_palette_and_media_compile_from_one_manifest(self):
        self.data['product']['name']='My OS é';self.data['welcome']['title']='Own welcome';self.data['palette']['accent']='#123456';self.save()
        out=self.root/'out';compiled=compile_brand(self.source,out)
        self.assertIn('My OS é',compiled['welcome']['description'])
        self.assertEqual(json.loads((out/'brand.json').read_text())['welcome']['title'],'Own welcome')
        self.assertIn('#123456',(out/'stylesheet.qss').read_text());self.assertNotIn('@accent@',(out/'stylesheet.qss').read_text())
        self.assertTrue((out/compiled['welcome']['video']).is_file());self.assertTrue((out/compiled['installation']['music']).is_file())
    def test_empty_video_and_music_are_supported(self):
        self.data['welcome']['video']='';self.data['installation']['music']='';self.save()
        compiled=compile_brand(self.source,self.root/'out')
        self.assertEqual(compiled['welcome']['video'],'');self.assertEqual(compiled['installation']['music'],'')
    def test_external_paths_and_symlinks_are_rejected(self):
        outside=self.root/'outside.svg';outside.write_text('<svg/>')
        for name in ['../outside.svg',str(outside),'images/link.svg']:
            if name.endswith('link.svg'):(self.source/name).symlink_to(outside)
            self.data['welcome']['image']=name;self.save()
            with self.assertRaises(ValueError):load(self.source)
    def test_invalid_media_cannot_replace_the_working_profile(self):
        stage=self.root/'stage';config=stage/'etc/calamares';config.mkdir(parents=True)
        (config/'settings.conf').write_text('keep this existing profile')
        (self.source/'video/welcome.webm').write_bytes(b'corrupt')
        result=subprocess.run(['bash',str(ROOT/'tools/install-profile.sh'),'--branding',str(self.source)],env={**os.environ,'DESTDIR':str(stage)},capture_output=True)
        self.assertNotEqual(result.returncode,0);self.assertEqual((config/'settings.conf').read_text(),'keep this existing profile')
    def test_invalid_palette_and_volume_are_rejected(self):
        self.data['palette']['accent']='purple';self.save()
        with self.assertRaises(ValueError):load(self.source)
        self.data['palette']['accent']='#123456';self.data['installation']['musicVolume']=101;self.save()
        with self.assertRaises(ValueError):load(self.source)
    def test_custom_brand_folder_and_software_catalog(self):
        self.data['product']['name']='Custom distro';self.save()
        stage=self.root/'custom'
        result=subprocess.run(['bash',str(ROOT/'tools/install-profile.sh'),'--distro','custom-os','--branding',str(self.source)],env={**os.environ,'DESTDIR':str(stage)},capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)
        config=stage/'etc/calamares'
        self.assertEqual(yaml.safe_load((config/'branding/corry/branding.desc').read_text())['strings']['productName'],'Custom distro')
        self.assertEqual((config/'corry-distro').read_text().strip(),'custom-os')

if __name__=='__main__':unittest.main()
