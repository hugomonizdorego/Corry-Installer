#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate the shipped profile against the actual module schemas and job order."""
from pathlib import Path
import importlib.util
import sys
import tempfile
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
        self.assertLess(jobs.index('corrycleanup'), jobs.index('initramfs'))
        self.assertLess(jobs.index('initramfs'), jobs.index('bootloader'))
        self.assertEqual(jobs[-1], 'umount')
        partition = yaml.safe_load((PROFILE / 'modules/partition.conf').read_text())
        self.assertEqual(partition['defaultFileSystemType'], 'btrfs')
        self.assertEqual(partition['initialPartitioningChoice'], 'none')

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

    def test_preflight_missing_image(self):
        spec = importlib.util.spec_from_file_location('preflight', ROOT / 'tools/preflight.py')
        preflight = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preflight)
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp)
            (config / 'modules').mkdir()
            (config / 'settings.conf').write_text('branding: corry\n')
            (config / 'modules/unpackfs.conf').write_text('unpack:\n- source: /missing/corry.squashfs\n')
            with patch.object(preflight.shutil, 'which', return_value='/usr/bin/tool'):
                errors = preflight.check(config)
            self.assertEqual(errors, ['Live system image not found: /missing/corry.squashfs'])


if __name__ == '__main__':
    unittest.main()
