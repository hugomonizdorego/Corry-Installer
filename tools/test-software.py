#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Failure-path tests for the preparation-before-partition contract."""
from pathlib import Path
import json
import tempfile
import types
import unittest
from unittest.mock import patch
import apt_support as apt
import yaml

STATUS='Package: linux-image-6.1-corry\nStatus: install ok installed\nArchitecture: amd64\n\nPackage: sudo\nStatus: install ok installed\nArchitecture: amd64\n\n'
CATALOG={'required':['sudo'], 'groups':[{'id':'office','packages':['libreoffice-writer']}]}


class SoftwareTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(); self.root=Path(self.temp.name)
        self.image=self.root/'image.squashfs'; self.image.touch()
        self.catalog=self.root/'software.yaml'; self.catalog.write_text(yaml.safe_dump(CATALOG))
        self.target=self.root/'target'; (self.target/'var/lib/dpkg').mkdir(parents=True)
        (self.target/'var/lib/dpkg/status').write_text(STATUS)
        self.gs={'rootMountPoint':str(self.target)}; self.target_calls=[]; self.commands=[]
        self.lib=types.SimpleNamespace(job=types.SimpleNamespace(configuration={'image':str(self.image),'catalog':str(self.catalog)}),
            globalstorage=types.SimpleNamespace(value=self.gs.get,insert=self.gs.__setitem__),
            utils=types.SimpleNamespace(target_env_call=self.target_call))
        self.mock=patch.object(apt,'run_command',side_effect=self.command); self.mock.start()

    def tearDown(self):
        self.mock.stop()
        if self.gs.get('corryPrepared'):
            apt.shutil.rmtree(self.gs['corryPrepared'],ignore_errors=True)
        self.temp.cleanup()

    def command(self,args,**kwargs):
        self.commands.append((args,kwargs))
        if args[:2]==['unsquashfs','-cat']:return STATUS
        if args[0]=='unsquashfs':
            payload=Path(args[args.index('-d')+1]); (payload/'etc/apt/sources.list.d').mkdir(parents=True)
            (payload/'usr/share/keyrings').mkdir(parents=True)
            (payload/'etc/apt/sources.list.d/base.sources').write_text('Types: deb\nURIs: https://example.invalid/debian\nSuites: stable\nComponents: main\nSigned-By: /usr/share/keyrings/distro.gpg\n')
        elif '--download-only' in args:
            folder=Path(kwargs['env']['APT_CONFIG']).parent
            (folder/'archives/office.deb').write_bytes(b'authenticated download fixture')
        return ''

    def target_call(self,args):
        self.target_calls.append(args)
        if 'install' in args:
            (self.target/'var/lib/dpkg/status').write_text(STATUS+'Package: libreoffice-writer\nStatus: install ok installed\nArchitecture: amd64\n\n')
        return 0

    def test_offline_base_uses_no_apt_or_network(self):
        apt.prepare(self.lib)
        self.assertEqual([a[0][0] for a in self.commands],['unsquashfs'])
        folder=Path(self.gs['corryPrepared']); apt.install(self.lib)
        self.assertFalse(self.target_calls); self.assertFalse(folder.exists())

    def test_selected_packages_download_then_install_without_network(self):
        self.gs['packagechooser_packagechooser']='office'
        apt.prepare(self.lib)
        self.assertFalse(self.target_calls)
        calls=[(args,kw) for args,kw in self.commands if args[0]=='apt-get']
        self.assertEqual(len(calls),3)
        folder=Path(self.gs['corryPrepared'])
        self.assertEqual((folder/'status').read_text(),STATUS)
        conf=(folder/'apt.conf').read_text()
        self.assertIn('Dir::Etc::parts "-"',conf)
        self.assertIn('APT::Update::Error-Mode "any"',conf)
        self.assertNotIn('trusted=yes',(folder/'etc/apt/sources.list.d/base.sources').read_text())
        self.assertTrue(json.loads((folder/'manifest.json').read_text())['archives'])
        apt.install(self.lib)
        self.assertIn('--no-download',self.target_calls[0]); self.assertIn('--no-remove',self.target_calls[0])
        self.assertEqual(self.target_calls[1][-1],'check')

    def test_repository_failure_stops_before_target_operations(self):
        self.gs['packagechooser_packagechooser']='office'
        def failure(args,**kwargs):
            if args[0]=='apt-get':raise RuntimeError('repository unavailable')
            return self.command(args,**kwargs)
        with patch.object(apt,'run_command',side_effect=failure):
            with self.assertRaisesRegex(RuntimeError,'unavailable'):apt.prepare(self.lib)
        self.assertNotIn('corryPrepared',self.gs); self.assertFalse(self.target_calls)

    def test_modified_download_never_reaches_target_apt(self):
        self.gs['packagechooser_packagechooser']='office'; apt.prepare(self.lib)
        (Path(self.gs['corryPrepared'])/'archives/office.deb').write_bytes(b'changed')
        with self.assertRaisesRegex(RuntimeError,'changed'):apt.install(self.lib)
        self.assertFalse(self.target_calls)

    def test_failed_target_install_is_not_ignored(self):
        self.gs['packagechooser_packagechooser']='office'; apt.prepare(self.lib)
        self.lib.utils.target_env_call=lambda args:1
        with self.assertRaisesRegex(RuntimeError,'could not install'):apt.install(self.lib)

    def test_live_root_and_missing_preparation_are_rejected(self):
        self.gs['rootMountPoint']='/'
        with self.assertRaisesRegex(ValueError,'live root'):apt.install(self.lib)
        self.gs['rootMountPoint']=str(self.target)
        with self.assertRaisesRegex(ValueError,'not prepared'):apt.install(self.lib)

    def test_bad_selections_and_package_names_are_rejected(self):
        with self.assertRaises(ValueError):apt.selected_packages(CATALOG,'office,--allow-unauthenticated')
        with self.assertRaises(ValueError):apt.selected_packages({'required':['-oBad=1'],'groups':[]},'')

    def test_unsigned_sources_are_rejected(self):
        folder=self.root/'repo'; (folder/'etc/apt').mkdir(parents=True)
        for text in ['deb [trusted=yes] https://example.invalid stable main', 'Types: deb\nTrusted: yes\n', 'deb [allow-insecure=yes] https://example.invalid stable main']:
            (folder/'etc/apt/sources.list').write_text(text)
            with self.assertRaisesRegex(RuntimeError,'signature'):apt.require_signed_sources(folder)

    def test_image_without_kernel_is_rejected(self):
        with patch.object(apt,'run_command',return_value=''):
            with self.assertRaisesRegex(RuntimeError,'kernel'):apt.prepare(self.lib)


if __name__=='__main__':unittest.main()
