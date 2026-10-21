#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate the shipped profile against the actual module schemas and job order."""
from pathlib import Path
import importlib.util
import sys
import tempfile
import subprocess
import json
import types
import unittest
from unittest.mock import patch
import yaml
import jsonschema

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'config/corry'


class ProfileTests(unittest.TestCase):
    def test_schemas_and_sequence(self):
        settings = yaml.safe_load((PROFILE / 'settings.conf').read_text())
        self.assertEqual(settings, yaml.safe_load((ROOT / 'settings.conf').read_text()))
        self.assertTrue(settings['prompt-install'])
        for phase in settings['sequence']:
            for name in next(iter(phase.values())):
                module = ROOT / 'src/modules' / name
                self.assertTrue((module / 'module.desc').exists() or (module / 'CMakeLists.txt').exists(), name)
        for config in (PROFILE / 'modules').glob('*.conf'):
            data = yaml.safe_load(config.read_text())
            schema = ROOT / f'src/modules/{config.stem}/{config.stem}.schema.yaml'
            if schema.exists():
                jsonschema.Draft7Validator(yaml.safe_load(schema.read_text())).validate(data)
        jobs = settings['sequence'][1]['exec']
        self.assertEqual(jobs[0], 'corryprepare')
        self.assertLess(jobs.index('unpackfs'), jobs.index('corrypackages'))
        self.assertLess(jobs.index('corrypackages'), jobs.index('corrycleanup'))
        self.assertLess(jobs.index('corrycleanup'), jobs.index('initramfs'))
        self.assertLess(jobs.index('initramfs'), jobs.index('bootloader'))
        self.assertEqual(jobs[-1], 'umount')
        partition = yaml.safe_load((PROFILE / 'modules/partition.conf').read_text())
        self.assertEqual(partition['defaultFileSystemType'], 'btrfs')
        self.assertEqual(partition['initialPartitioningChoice'], 'none')

    def test_both_distro_profiles_are_separate_and_complete(self):
        names=[]
        for distro in ['edukasaun','debion']:
            with tempfile.TemporaryDirectory() as temp:
                subprocess.run(['bash', str(ROOT/'tools/install-profile.sh'), '--distro', distro,
                                '--image', '/tmp/Corry image.squashfs'],
                               env={**__import__('os').environ,'DESTDIR':temp}, check=True,
                               stdout=subprocess.PIPE)
                config=Path(temp)/'etc/calamares'
                brand=config/'branding/corry'
                desc=yaml.safe_load((brand/'branding.desc').read_text())
                names.append(desc['strings']['productName'])
                self.assertEqual(desc['sidebar'],'qml,top')
                self.assertTrue((brand/'slides/Slides.js').is_file())
                for entry in json.loads((brand/'slides/slides.json').read_text()):
                    self.assertTrue((brand/'slides'/entry['image']).is_file())
                chooser=yaml.safe_load((config/'modules/packagechooser.conf').read_text())
                catalog=yaml.safe_load((config/'corry-software.yaml').read_text())
                self.assertEqual(chooser['mode'],'optionalmultiple')
                self.assertEqual(chooser['items'][1:],catalog['groups'])
                self.assertNotIn('default',chooser)
                self.assertEqual(yaml.safe_load((config/'modules/corryprepare.conf').read_text())['image'],'/tmp/Corry image.squashfs')
        self.assertEqual(names,['Edukasaun OS','DebION GNU/Linux'])

    def test_cleanup_never_touches_live_root(self):
        module_path = ROOT / 'src/modules/corrycleanup/main.py'
        fake = types.SimpleNamespace(globalstorage=types.SimpleNamespace(value=lambda key: '/'), utils=types.SimpleNamespace(), job=types.SimpleNamespace(configuration={}))
        with patch.dict(sys.modules, {'libcalamares': fake}):
            spec = importlib.util.spec_from_file_location('corrycleanup', module_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        self.assertIsNotNone(module.run())
        calls = []
        fake.globalstorage.value = lambda key: '/tmp/test-target'
        def call(args):
            calls.append(args)
            if args[0] == 'dpkg-query':
                return 0 if args[-1] == 'live-config' else 1
            return 0
        fake.utils.target_env_call = call
        self.assertIsNone(module.run())
        self.assertEqual(calls[-1], ['dpkg', '--purge', 'live-config'])
        self.assertFalse(any('autoremove' in args for args in calls))

    def test_cleanup_preserves_existing_home(self):
        calls = []
        fake = types.SimpleNamespace(
            globalstorage=types.SimpleNamespace(value=lambda key: '/tmp/test-target' if key=='rootMountPoint' else 'hugo'),
            job=types.SimpleNamespace(configuration={'liveUser': 'user'}),
            utils=types.SimpleNamespace(target_env_call=lambda args: calls.append(args) or (1 if args[0]=='dpkg-query' else 0)))
        with patch.dict(sys.modules, {'libcalamares': fake}):
            spec = importlib.util.spec_from_file_location('corrycleanup_home', ROOT / 'src/modules/corrycleanup/main.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        self.assertIsNone(module.run())
        self.assertEqual(calls[-1], ['userdel', '--', 'user'])
        self.assertFalse(any('--remove' in args or '-r' in args for args in calls))
        calls.clear()
        fake.globalstorage.value = lambda key: '/tmp/test-target' if key=='rootMountPoint' else 'user'
        self.assertIsNone(module.run())
        self.assertFalse(any(args[0]=='userdel' for args in calls))

    def test_preflight_missing_image(self):
        spec = importlib.util.spec_from_file_location('preflight', ROOT / 'tools/preflight.py')
        preflight = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preflight)
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp)
            (config / 'modules').mkdir()
            (config / 'settings.conf').write_text('branding: corry\n')
            (config / 'modules/unpackfs.conf').write_text('unpack:\n- source: /missing/corry.squashfs\n')
            with patch.object(preflight.shutil, 'which', return_value='/usr/bin/tool') as probe:
                errors = preflight.check(config)
            self.assertTrue(all('/usr/sbin' in call.kwargs['path'] for call in probe.call_args_list))
            self.assertEqual(errors, ['Live system image not found: /missing/corry.squashfs'])


if __name__ == '__main__':
    unittest.main()
