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
import shutil
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
        shown = settings['sequence'][0]['show']
        self.assertEqual(shown, ['welcome', 'locale', 'keyboard', 'partition', 'users', 'summary'])
        jobs = settings['sequence'][1]['exec']
        # The software page and its network jobs were removed: installs are offline.
        for removed in ['packagechooser', 'corryprepare', 'corrypackages']:
            self.assertNotIn(removed, shown + jobs)
            self.assertFalse((ROOT / 'src/modules' / removed / 'module.desc').exists())
        self.assertEqual(jobs[0], 'partition')
        self.assertLess(jobs.index('unpackfs'), jobs.index('corrycleanup'))
        self.assertLess(jobs.index('users'), jobs.index('corrycleanup'))
        self.assertLess(jobs.index('corrycleanup'), jobs.index('initramfs'))
        self.assertLess(jobs.index('initramfs'), jobs.index('corrygrub'))
        self.assertLess(jobs.index('corrygrub'), jobs.index('grubcfg'))
        self.assertLess(jobs.index('grubcfg'), jobs.index('bootloader'))
        self.assertEqual(jobs[-1], 'umount')
        build = (ROOT / 'tools/build-corry.sh').read_text()
        for name in shown + jobs + ['finished']:
            self.assertIn(' ' + name + ' ', build)
        partition = yaml.safe_load((PROFILE / 'modules/partition.conf').read_text())
        self.assertEqual(partition['defaultFileSystemType'], 'btrfs')
        self.assertEqual(partition['initialPartitioningChoice'], 'none')

    def test_both_distro_profiles_are_separate_and_complete(self):
        names=[]
        for distro in ['edukasaun','debion']:
            with tempfile.TemporaryDirectory() as temp:
                subprocess.run(['bash', str(ROOT/'tools/install-profile.sh'), '--distro', distro,
                                '--image', '/tmp/live/Corry image.squashfs'],
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
                for entry in json.loads((brand/'slides/slides.json').read_text()):
                    self.assertTrue(entry['title'].isascii() and entry['description'].isascii())
                self.assertFalse((config/'modules/packagechooser.conf').exists())
                self.assertFalse((config/'corry-software.yaml').exists())
                self.assertEqual(yaml.safe_load((config/'modules/corrygrub.conf').read_text())['medium'], '/tmp')
                root=Path(temp)
                launcher=(root/'usr/share/applications/corry-installer.desktop').read_text()
                self.assertIn('Name=Install '+desc['strings']['productName']+'\n', launcher)
                self.assertNotIn('[id]', launcher)
                self.assertTrue((root/'etc/skel/Desktop/corry-installer.desktop').is_file())
                self.assertFalse((root/'etc/xdg/autostart/corry-installer.desktop').exists())
                for hidden in ['calamares', 'install-debian']:
                    self.assertIn('Hidden=true', (root/f'usr/local/share/applications/{hidden}.desktop').read_text())
                self.assertIn('/usr/bin/corry-installer', (root/'usr/local/bin/install-debian').read_text())
                accent=yaml.safe_load((ROOT/f'config/distros/{distro}/profile.yaml').read_text())['accent']
                for themed in ['stylesheet.qss', 'show.qml', 'corry-mark.svg']:
                    self.assertIn(accent, (brand/themed).read_text())
        self.assertEqual(names,['Edukasaun OS','DebION GNU/Linux'])
        with tempfile.TemporaryDirectory() as temp:
            subprocess.run(['bash', str(ROOT/'tools/install-profile.sh'), '--distro', 'edukasaun', '--autostart'],
                           env={**__import__('os').environ,'DESTDIR':temp}, check=True, stdout=subprocess.PIPE)
            self.assertIn('Exec=corry-installer', (Path(temp)/'etc/xdg/autostart/corry-installer.desktop').read_text())

    def test_debian_base_detection(self):
        script = ROOT / 'tools/debian-base.sh'
        def base(version, override=''):
            with tempfile.NamedTemporaryFile('w') as stub:
                stub.write(version)
                stub.flush()
                source = script.read_text().replace('/etc/debian_version', stub.name)
                return subprocess.run(['bash', '-c', source + '\ncorry_detect_base && echo "$corry_base"'],
                                      env={'PATH': '/usr/bin:/bin', 'CORRY_DEBIAN_BASE': override},
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(base('13.1\n').stdout.strip(), 'stable')
        self.assertEqual(base('forky/sid\n').stdout.strip(), 'testing')
        self.assertEqual(base('14.0\n').stdout.strip(), 'testing')
        self.assertNotEqual(base('12.9\n').returncode, 0)
        self.assertEqual(base('12.9\n', 'testing').stdout.strip(), 'testing')
        self.assertNotEqual(base('13\n', 'sid').returncode, 0)

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

    def load_module(self, name, fake):
        with patch.dict(sys.modules, {'libcalamares': fake}):
            spec = importlib.util.spec_from_file_location(name, ROOT / f'src/modules/{name}/main.py')
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
        return module

    def test_cleanup_removes_installer_launchers_from_target(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            launchers = ['usr/share/applications/corry-installer.desktop', 'etc/skel/Desktop/corry-installer.desktop',
                         'home/hugo/Desktop/corry-installer.desktop', 'usr/local/bin/install-debian', 'opt/live-only']
            for relative in launchers + ['home/hugo/Desktop/notes.txt']:
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text('x')
            fake = types.SimpleNamespace(
                globalstorage=types.SimpleNamespace(value=lambda key: temp if key == 'rootMountPoint' else 'hugo'),
                job=types.SimpleNamespace(configuration={'liveUser': 'user', 'removeFiles': ['opt/live-only']}),
                utils=types.SimpleNamespace(target_env_call=lambda args: 1 if args[0] in ('dpkg-query', 'id') else 0))
            self.assertIsNone(self.load_module('corrycleanup', fake).run())
            self.assertFalse(any((root / relative).exists() for relative in launchers))
            self.assertTrue((root / 'home/hugo/Desktop/notes.txt').exists())
            fake.job.configuration['removeFiles'] = ['../outside']
            self.assertIsNotNone(self.load_module('corrycleanup', fake).run())

    def test_grub_package_selection_and_medium(self):
        fake = types.SimpleNamespace(globalstorage=types.SimpleNamespace(value=lambda key: None),
                                     job=types.SimpleNamespace(configuration={}), utils=types.SimpleNamespace())
        grub = self.load_module('corrygrub', fake)
        self.assertEqual(grub.wanted('efi', 'amd64'), ('grub-efi-amd64', 'x86_64-efi'))
        self.assertEqual(grub.wanted('bios', 'amd64'), ('grub-pc', 'i386-pc'))
        self.assertEqual(grub.wanted('bios', 'arm64'), (None, None))
        self.assertIsNotNone(grub.run())  # No target mounted.
        with tempfile.TemporaryDirectory() as temp:
            medium = Path(temp) / 'medium'
            (medium / 'pool/main/g/grub2').mkdir(parents=True)
            (medium / 'dists/trixie').mkdir(parents=True)
            self.assertEqual(grub.medium_sources(medium, 'grub-pc'), [])
            (medium / 'pool/main/g/grub2/grub-pc_2.12-9_amd64.deb').write_text('')
            (medium / 'dists/trixie/Release').write_text('Suite: stable\nComponents: main non-free-firmware\n')
            (medium / 'dists/stable').symlink_to('trixie')
            self.assertEqual(grub.medium_sources(medium, 'grub-pc'),
                             ['deb [trusted=yes] file:/media/corry-medium trixie main non-free-firmware'])
            target = Path(temp) / 'target'
            (target / 'var/lib/dpkg').mkdir(parents=True)
            (target / 'var/lib/dpkg/status').write_text(
                'Package: grub-pc\nStatus: deinstall ok config-files\n\nPackage: grub-pc-bin\nStatus: install ok installed\n')
            self.assertFalse(grub.installed(target, 'grub-pc'))
            self.assertTrue(grub.installed(target, 'grub-pc-bin'))
            # Without the package on the medium, platform files allow a warning only.
            warnings = []
            fake.globalstorage.value = lambda key: {'rootMountPoint': str(target), 'firmwareType': 'bios'}[key]
            fake.job.configuration = {'medium': str(Path(temp) / 'empty')}
            fake.utils.warning = warnings.append
            (Path(temp) / 'empty/pool').mkdir(parents=True)
            with patch.object(grub.subprocess, 'run', return_value=types.SimpleNamespace(stdout='amd64\n', returncode=0)):
                self.assertIsNotNone(grub.run())
                (target / 'usr/lib/grub/i386-pc').mkdir(parents=True)
                self.assertIsNone(grub.run())
            self.assertIn('grub-pc', warnings[-1])

    @unittest.skipUnless(shutil.which('mksquashfs') and shutil.which('unsquashfs'), 'squashfs-tools not installed')
    def test_preflight_checks_image_contents(self):
        spec = importlib.util.spec_from_file_location('preflight_image', ROOT / 'tools/preflight.py')
        preflight = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preflight)
        with tempfile.TemporaryDirectory() as temp:
            tree = Path(temp) / 'tree'
            for relative in ['boot/vmlinuz-6.12.0-1-amd64', 'usr/sbin/update-initramfs', 'usr/sbin/grub-install',
                             'usr/lib/grub/x86_64-efi/grub.efi']:
                (tree / relative).parent.mkdir(parents=True, exist_ok=True)
                (tree / relative).write_text('x')
            image = str(Path(temp) / 'filesystem.squashfs')
            subprocess.run(['mksquashfs', str(tree), image, '-quiet', '-noappend'], check=True, stdout=subprocess.DEVNULL)
            self.assertEqual(preflight.missing_from_image(image, True, 'amd64'), [])
            missing = preflight.missing_from_image(image, False, 'amd64')
            self.assertEqual(len(missing), 1)
            self.assertIn('i386-pc', missing[0])


if __name__ == '__main__':
    unittest.main()
