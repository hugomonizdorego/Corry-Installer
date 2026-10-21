#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Validate Corry's profile, branding and job modules without touching any disk."""
from pathlib import Path
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
from unittest.mock import patch
import yaml
import jsonschema

ROOT = Path(__file__).resolve().parents[1]
PROFILE = ROOT / 'config/corry'
DISTROS = ['edukasaun', 'debion']


def fake_calamares(values=None, configuration=None, call=None):
    values = values or {}
    log = types.SimpleNamespace(warnings=[], progress=[])
    return types.SimpleNamespace(
        globalstorage=types.SimpleNamespace(value=lambda key: values.get(key)),
        job=types.SimpleNamespace(configuration=configuration or {}, setprogress=log.progress.append),
        utils=types.SimpleNamespace(target_env_call=call or (lambda *args: 0), warning=log.warnings.append,
                                    debug=lambda *args: None),
        log=log)


def load_module(name, fake, path=None):
    with patch.dict(sys.modules, {'libcalamares': fake}):
        spec = importlib.util.spec_from_file_location(name, path or ROOT / f'src/modules/{name}/main.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
    module.libcalamares = fake
    return module


def stage(distro, *extra):
    temp = tempfile.TemporaryDirectory()
    subprocess.run(['bash', str(ROOT / 'tools/install-profile.sh'), '--distro', distro,
                    '--image', '/tmp/live/Corry image.squashfs', *extra],
                   env={**os.environ, 'DESTDIR': temp.name}, check=True, stdout=subprocess.PIPE)
    return temp


class SequenceTests(unittest.TestCase):
    def test_schemas_and_sequence(self):
        settings = yaml.safe_load((PROFILE / 'settings.conf').read_text())
        self.assertEqual(settings, yaml.safe_load((ROOT / 'settings.conf').read_text()))
        self.assertTrue(settings['prompt-install'])
        instances = {f"{i['module']}@{i['id']}": i for i in settings['instances']}
        for phase in settings['sequence']:
            for name in next(iter(phase.values())):
                module = ROOT / 'src/modules' / name.split('@')[0]
                self.assertTrue((module / 'module.desc').exists() or (module / 'CMakeLists.txt').exists(), name)
                if '@' in name:
                    self.assertIn(name, instances)
        schemas = {'welcomecheck': 'welcome'}
        for config in (PROFILE / 'modules').glob('*.conf'):
            module = schemas.get(config.stem, config.stem)
            schema = ROOT / f'src/modules/{module}/{module}.schema.yaml'
            if schema.exists():
                jsonschema.Draft7Validator(yaml.safe_load(schema.read_text())).validate(yaml.safe_load(config.read_text()))
        shown = settings['sequence'][0]['show']
        self.assertEqual(shown, ['welcome', 'welcome@check', 'locale', 'keyboard', 'partition', 'users', 'summary'])
        jobs = settings['sequence'][1]['exec']
        for removed in ['packagechooser', 'corryprepare', 'corrypackages']:
            self.assertNotIn(removed, shown + jobs)
            self.assertFalse((ROOT / 'src/modules' / removed / 'module.desc').exists())
        self.assertEqual(jobs[0], 'partition')
        order = ['unpackfs', 'users', 'corrycleanup', 'corryupdate', 'corrygrub', 'initramfs', 'grubcfg', 'bootloader']
        for before, after in zip(order, order[1:]):
            self.assertLess(jobs.index(before), jobs.index(after), (before, after))
        self.assertEqual(jobs[-1], 'umount')
        build = (ROOT / 'tools/build-corry.sh').read_text()
        for name in shown + jobs + ['finished']:
            self.assertIn(' ' + name.split('@')[0] + ' ', build)

    def test_profile_choices(self):
        modules = PROFILE / 'modules'
        partition = yaml.safe_load((modules / 'partition.conf').read_text())
        self.assertEqual(partition['defaultFileSystemType'], 'btrfs')
        self.assertEqual(partition['efi']['recommendedSize'], '300MiB')
        users = yaml.safe_load((modules / 'users.conf').read_text())
        self.assertTrue(users['setRootPassword'])
        self.assertTrue(users['doReusePassword'])
        greeting = yaml.safe_load((modules / 'welcome.conf').read_text())
        check = yaml.safe_load((modules / 'welcomecheck.conf').read_text())
        self.assertEqual((greeting['corryPage'], check['corryPage']), ('greeting', 'check'))
        self.assertEqual(greeting['requirements']['check'], [])
        self.assertIn('internet', check['requirements']['check'])
        self.assertNotIn('internet', check['requirements']['required'])
        grub = yaml.safe_load((modules / 'grubcfg.conf').read_text())
        self.assertFalse(grub['defaults']['GRUB_DISABLE_OS_PROBER'])
        self.assertEqual((ROOT / 'VERSION').read_text().strip(), '0.1')


class BrandingTests(unittest.TestCase):
    def branding(self):
        spec = importlib.util.spec_from_file_location('corry_branding', ROOT / 'tools/corry-branding.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_both_distro_profiles_are_separate_and_complete(self):
        names = []
        for distro in DISTROS:
            with stage(distro) as temp:
                root = Path(temp)
                config = root / 'etc/calamares'
                brand = config / 'branding/corry'
                desc = yaml.safe_load((brand / 'branding.desc').read_text())
                names.append(desc['strings']['productName'])
                self.assertEqual(desc['sidebar'], 'qml,top')
                self.assertTrue((brand / desc['images']['productWelcome']).is_file())
                source = yaml.safe_load((ROOT / f'config/distros/{distro}/distro.yaml').read_text())
                slides = json.loads((brand / 'slides/Slides.js').read_text().split('var slides = ')[1].rstrip(';\n'))
                self.assertGreaterEqual(len(slides), 5)
                for slide in slides:
                    self.assertTrue((brand / 'slides' / slide['image']).is_file())
                    self.assertTrue(slide['title'].isascii() and slide['description'].isascii())
                media = json.loads((brand / 'media.js').read_text().split('var media = ')[1].rstrip(';\n'))
                self.assertTrue((brand / media['video']).is_file())
                self.assertTrue((brand / media['sound']).is_file())
                accent = source['colors']['accent']
                for themed in ['stylesheet.qss', 'show.qml', 'corry-mark.svg', 'calamares-sidebar.qml']:
                    self.assertIn(accent, (brand / themed).read_text())
                self.assertIn('Corry 0.1', (brand / 'calamares-sidebar.qml').read_text())
                self.assertFalse((config / 'modules/packagechooser.conf').exists())
                grub = yaml.safe_load((config / 'modules/corrygrub.conf').read_text())
                self.assertEqual(grub['medium'], '/tmp')
                self.assertEqual(grub['checkUrl'], source['internet-check-url'])
                self.assertEqual(yaml.safe_load((config / 'modules/unpackfs.conf').read_text())['unpack'][0]['source'],
                                 '/tmp/live/Corry image.squashfs')
                launcher = (root / 'usr/share/applications/corry-installer.desktop').read_text()
                self.assertIn('Name=Install ' + desc['strings']['productName'] + '\n', launcher)
                self.assertFalse((root / 'etc/skel').exists())  # Desktop icon comes from the autostart helper.
                self.assertIn('/usr/lib/corry/corry-desktop-icon',
                              (root / 'etc/xdg/autostart/corry-desktop-icon.desktop').read_text())
                self.assertFalse((root / 'etc/xdg/autostart/corry-installer.desktop').exists())
                for hidden in ['calamares', 'install-debian']:
                    self.assertIn('Hidden=true', (root / f'usr/local/share/applications/{hidden}.desktop').read_text())
                self.assertIn('/usr/bin/corry-installer', (root / 'usr/local/bin/install-debian').read_text())
                manifest = (root / 'usr/lib/corry/manifest').read_text().split()
                for path in ['/etc/calamares', '/usr/bin/corry-installer', '/usr/lib/corry']:
                    self.assertIn(path, manifest)
        self.assertEqual(names, ['Edukasaun OS', 'DebION GNU/Linux'])
        with stage('edukasaun', '--autostart') as temp:
            self.assertIn('Exec=corry-installer', (Path(temp) / 'etc/xdg/autostart/corry-installer.desktop').read_text())

    def test_package_mode_writes_only_profile_files(self):
        with stage('debion', '--package') as temp:
            root = Path(temp)
            files = sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() or p.is_symlink())
            self.assertTrue(all(f.startswith(('etc/calamares/', 'usr/share/applications/', 'usr/bin/install-debian'))
                                for f in files), files)
            self.assertEqual(os.readlink(root / 'usr/bin/install-debian'), 'corry-installer')
            self.assertIn('Name=Install DebION GNU/Linux', (root / 'usr/share/applications/corry-installer.desktop').read_text())

    def test_debian_packaging(self):
        control = (ROOT / 'debian/control').read_text()
        engine = control.split('\nPackage: ')[1]
        for field in ['Conflicts', 'Replaces']:
            line = next(l for l in engine.splitlines() if l.startswith(field + ':'))
            self.assertIn('calamares,', line + ',')
            self.assertIn('calamares-settings-debian', line)
        self.assertIn('Provides: calamares', engine)
        for distro in DISTROS:
            self.assertIn(f'Package: corry-{distro}', control)
        self.assertEqual((ROOT / 'debian/changelog').read_text().split('(')[1].split(')')[0],
                         (ROOT / 'VERSION').read_text().strip())
        install = (ROOT / 'debian/corry.install').read_text()
        for path in ['tools/remove-calamares', 'config/corry/apt/80corry-remove-calamares', 'tools/corry-desktop-icon']:
            self.assertIn(path, install)
        rules = (ROOT / 'debian/rules').read_text()
        build = (ROOT / 'tools/build-corry.sh').read_text()
        block = re.search(r'^KEEP := ((?:.*\\\n)*.*)$', rules, re.M).group(1)
        self.assertEqual(set(block.replace('\\', ' ').split()), set(build.split("keep='")[1].split("'")[0].split()))

    def test_remove_calamares_helper(self):
        script = ROOT / 'tools/remove-calamares'
        with tempfile.TemporaryDirectory() as temp:
            bin_dir = Path(temp)
            log = bin_dir / 'log'
            leftover = bin_dir / 'calamares-desktop-icon.desktop'
            kept = bin_dir / 'settings.conf'
            for path in (leftover, kept):
                path.write_text('x')
            (bin_dir / 'dpkg-query').write_text(f'''#!/bin/sh
case "$1" in
 -W) printf 'rc |calamares-settings-debian\\nii |calamares\\n';;
 -L) printf '{leftover}\\n{kept}\\n';;
 -S) case "$2" in {kept}) echo 'corry-edukasaun, calamares-settings-debian: $2';; *) echo 'calamares-settings-debian: $2';; esac;;
esac
''')
            for tool in ['dpkg', 'apt-get']:
                (bin_dir / tool).write_text(f'#!/bin/sh\necho {tool} "$@" >> {log}\n')
            for tool in ['dpkg-query', 'dpkg', 'apt-get']:
                (bin_dir / tool).chmod(0o755)
            env = {'PATH': f'{bin_dir}:/usr/bin:/bin'}
            run = lambda mode: subprocess.run(['sh', str(script), mode], env=env, check=True, stdout=subprocess.PIPE)
            run('--leftovers')
            self.assertFalse(leftover.exists())
            self.assertTrue(kept.exists())
            run('--purge-rc')
            run('--purge')
            lines = log.read_text().splitlines()
            self.assertIn('dpkg --purge calamares-settings-debian', lines)
            self.assertIn('apt-get purge -y calamares calamares-settings-debian', lines)

    def test_branding_validation(self):
        branding = self.branding()
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'mine'
            shutil.copytree(ROOT / 'config/distros/debion', folder)
            data = yaml.safe_load((folder / 'distro.yaml').read_text())
            self.assertEqual(len(branding.load(folder)['slides']), len(data['slides']))
            for change, message in [
                (lambda d: d.update(slides=d['slides'][:4]), 'at least 5'),
                (lambda d: d['colors'].update(accent='green'), 'colors.accent'),
                (lambda d: d['slides'][0].update(image='../escape.svg'), 'inside'),
                (lambda d: d['welcome'].update(video='media/missing.webm'), 'not found'),
                (lambda d: d['sound'].update(volume=3), 'volume')]:
                broken = json.loads(json.dumps(data))
                change(broken)
                (folder / 'distro.yaml').write_text(yaml.safe_dump(broken))
                with self.assertRaisesRegex(branding.BrandingError, message):
                    branding.load(folder)
            data['welcome']['video'] = ''
            data['sound']['file'] = ''
            (folder / 'distro.yaml').write_text(yaml.safe_dump(data))
            self.assertEqual(branding.load(folder)['welcome']['video'], '')

    def test_media_size_advice(self):
        branding = self.branding()
        self.assertEqual(branding.media_warnings(ROOT / 'config/distros/debion',
                                                 branding.load(ROOT / 'config/distros/debion')), [])
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'mine'
            shutil.copytree(ROOT / 'config/distros/debion', folder)
            square = folder / 'slides/photo.png'
            # A 800x800 PNG header is enough for the size check.
            square.write_bytes(b'\x89PNG\r\n\x1a\n' + b'\x00\x00\x00\rIHDR' + (800).to_bytes(4, 'big') * 2 + b'\x08\x02\x00\x00\x00')
            self.assertEqual(branding.image_size(square), (800, 800))
            data = yaml.safe_load((folder / 'distro.yaml').read_text())
            data['slides'][0]['image'] = 'photo.png'
            (folder / 'distro.yaml').write_text(yaml.safe_dump(data))
            warnings = branding.media_warnings(folder, branding.load(folder))
            self.assertTrue(any('not 16:9' in w for w in warnings), warnings)
            self.assertTrue(any('at least 1280x720' in w for w in warnings), warnings)
            self.assertEqual(branding.image_size(folder / 'slides/welcome.svg'), (800.0, 450.0))

    def test_new_distro_tool(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp) / 'repo'
            for part in ['tools', 'config/distros/debion']:
                shutil.copytree(ROOT / part, repo / part)
            subprocess.run([sys.executable, str(repo / 'tools/new-distro.py'), 'demo-os', 'Demo OS',
                            '--accent', '#123456', '--no-media'], check=True, stdout=subprocess.PIPE)
            data = yaml.safe_load((repo / 'config/distros/demo-os/distro.yaml').read_text())
            self.assertEqual((data['name'], data['colors']['accent']), ('Demo OS', '#123456'))
            self.assertEqual(data['slides'][0]['title'], 'Welcome to Demo OS')

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


class CleanupTests(unittest.TestCase):
    def test_cleanup_never_touches_live_root(self):
        fake = fake_calamares({'rootMountPoint': '/'})
        self.assertIsNotNone(load_module('corrycleanup', fake).run())

    def test_cleanup_purges_live_and_installer_packages(self):
        calls = []

        def call(args):
            calls.append(args)
            if args[0] == 'dpkg-query':
                return 0 if args[-1] in ('live-config', 'calamares') else 1
            return 0
        with tempfile.TemporaryDirectory() as temp:
            fake = fake_calamares({'rootMountPoint': temp, 'username': 'hugo'}, {'liveUser': 'user'}, call)
            self.assertIsNone(load_module('corrycleanup', fake).run())
        self.assertIn(['dpkg', '--purge', 'live-config', 'calamares'], calls)
        self.assertFalse(any('autoremove' in args for args in calls))
        self.assertIn(['userdel', '--', 'user'], calls)
        self.assertFalse(any('--remove' in args or '-r' in args for args in calls))

    def test_cleanup_keeps_new_user_named_like_live_user(self):
        calls = []
        with tempfile.TemporaryDirectory() as temp:
            fake = fake_calamares({'rootMountPoint': temp, 'username': 'user'}, {'liveUser': 'user'},
                                  lambda args: calls.append(args) or (1 if args[0] == 'dpkg-query' else 0))
            self.assertIsNone(load_module('corrycleanup', fake).run())
        self.assertFalse(any(args[0] == 'userdel' for args in calls))

    def test_cleanup_removes_every_trace_of_corry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            corry = ['usr/share/applications/corry-installer.desktop', 'etc/skel/Desktop/corry-installer.desktop',
                     'home/hugo/Desktop/corry-installer.desktop', 'usr/local/bin/install-debian',
                     'etc/calamares/settings.conf', 'etc/calamares/branding/corry/show.qml',
                     'usr/lib/x86_64-linux-gnu/libcalamares.so.3.3.15', 'usr/share/calamares/qml/x',
                     'usr/lib/corry/preflight.py', 'usr/bin/calamares', 'opt/live-only']
            keep = ['home/hugo/Desktop/notes.txt', 'usr/share/applications/firefox.desktop', 'usr/bin/bash']
            for relative in corry + keep:
                (root / relative).parent.mkdir(parents=True, exist_ok=True)
                (root / relative).write_text('x')
            (root / 'usr/lib/corry/manifest').write_text(
                '/usr/lib/x86_64-linux-gnu/libcalamares.so.3.3.15\n/usr/share/applications\n/etc/calamares\n')
            fake = fake_calamares({'rootMountPoint': temp, 'username': 'hugo'},
                                  {'liveUser': 'user', 'removeFiles': ['opt/live-only']},
                                  lambda args: 1 if args[0] in ('dpkg-query', 'id') else 0)
            self.assertIsNone(load_module('corrycleanup', fake).run())
            self.assertEqual([p for p in corry if (root / p).exists()], [])
            for directory in ['etc/calamares', 'usr/lib/corry', 'usr/share/calamares']:
                self.assertFalse((root / directory).exists(), directory)
            self.assertTrue(all((root / p).exists() for p in keep))
            self.assertTrue((root / 'usr/share/applications').is_dir())
            fake.job.configuration['removeFiles'] = ['../outside']
            self.assertIsNotNone(load_module('corrycleanup', fake).run())


class GrubTests(unittest.TestCase):
    def test_grub_package_selection_and_medium(self):
        fake = fake_calamares()
        grub = load_module('corrygrub', fake)
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
            (Path(temp) / 'empty/pool').mkdir(parents=True)
            values = {'rootMountPoint': str(target), 'firmwareType': 'bios'}
            fake.globalstorage.value = values.get
            fake.job.configuration = {'medium': str(Path(temp) / 'empty')}
            arch = types.SimpleNamespace(stdout='amd64\n', returncode=0)
            with patch.object(grub.subprocess, 'run', return_value=arch), patch.object(grub, 'online', return_value=False):
                self.assertIsNotNone(grub.run())  # No package, no GRUB files: stop.
                (target / 'usr/lib/grub/i386-pc').mkdir(parents=True)
                self.assertIsNone(grub.run())  # GRUB files present: warn and continue.
            self.assertIn('grub-pc', fake.log.warnings[-1])
            # Online fallback uses the target's own sources.
            calls = []
            fake.utils.target_env_call = lambda args: calls.append(args) or 0
            (target / 'etc').mkdir()
            (target / 'etc/resolv.conf').symlink_to('../run/systemd/resolve/stub-resolv.conf')
            with patch.object(grub.subprocess, 'run', return_value=arch), patch.object(grub, 'online', return_value=True), \
                    patch.object(grub.shutil, 'copyfile', side_effect=lambda src, dst: Path(dst).write_text('nameserver 1.1.1.1\n')):
                self.assertIsNone(grub.run())
            self.assertEqual(calls[-1][-1], 'grub-pc')
            self.assertTrue((target / 'etc/resolv.conf').is_symlink())


class UpdateTests(unittest.TestCase):
    def run_update(self, online, failing=()):
        calls = []

        def call(args, stdin='', timeout=0):
            calls.append(args[2:])
            return 1 if any(word in args for word in failing) else 0
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'etc').mkdir()
            (root / 'etc/resolv.conf').write_text('# target\n')
            fake = fake_calamares({'rootMountPoint': temp}, {'upgrade': 'safe'}, call)
            update = load_module('corryupdate', fake)
            with patch.object(update, 'online', return_value=online):
                self.assertIsNone(update.run())
            # Temporary files are always restored.
            self.assertFalse((root / 'usr/sbin/policy-rc.d').exists())
            self.assertEqual((root / 'etc/resolv.conf').read_text(), '# target\n')
        return calls, fake.log.warnings

    def test_offline_only_repairs_locally(self):
        calls, warnings = self.run_update(False)
        self.assertEqual(calls[0], ['dpkg', '--configure', '-a'])
        self.assertIn('--no-download', calls[1])
        self.assertFalse(any(c[:2] == ['apt-get', 'update'] for c in calls))
        self.assertEqual(warnings, [])

    def test_online_repairs_and_updates(self):
        calls, warnings = self.run_update(True)
        commands = [c[:2] for c in calls]
        self.assertIn(['apt-get', 'update'], commands)
        self.assertIn(['apt-get', '--fix-broken'], commands)
        self.assertIn(['apt-get', 'upgrade'], commands)
        self.assertNotIn(['apt-get', 'full-upgrade'], commands)

    def test_network_problems_never_fail_installation(self):
        calls, warnings = self.run_update(True, failing=('update',))
        self.assertFalse(any(c[:2] == ['apt-get', 'upgrade'] for c in calls))
        self.assertTrue(warnings)


class PreflightTests(unittest.TestCase):
    def preflight(self):
        spec = importlib.util.spec_from_file_location('preflight', ROOT / 'tools/preflight.py')
        preflight = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preflight)
        return preflight

    def test_preflight_missing_image(self):
        preflight = self.preflight()
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp)
            (config / 'modules').mkdir()
            (config / 'settings.conf').write_text('branding: corry\n')
            (config / 'modules/unpackfs.conf').write_text('unpack:\n- source: /missing/corry.squashfs\n')
            with patch.object(preflight.shutil, 'which', return_value='/usr/bin/tool') as probe:
                errors = preflight.check(config)
            self.assertTrue(all('/usr/sbin' in call.kwargs['path'] for call in probe.call_args_list))
            self.assertEqual(errors, ['Live system image not found: /missing/corry.squashfs'])

    @unittest.skipUnless(shutil.which('mksquashfs') and shutil.which('unsquashfs'), 'squashfs-tools not installed')
    def test_preflight_checks_image_contents(self):
        preflight = self.preflight()
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
