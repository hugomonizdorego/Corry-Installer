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


def fake_calamares(values=None, configuration=None, call=None, process_output=None):
    """A stand-in for libcalamares: global storage, job configuration and logging.

    @p call answers target_env_call (an exit code); @p process_output answers
    check_target_env_output (a string, or raise CalledProcessError). As in
    Calamares 3.3, target_env_process_output returns only the exit code.
    """
    values = values if values is not None else {}
    log = types.SimpleNamespace(warnings=[], progress=[])

    def default_output(args, *rest):
        return ''
    answer = process_output or default_output

    def check_output(args, stdin='', timeout=0):
        return answer(args, None, stdin, timeout)

    def exit_code_only(args, callback=None, stdin='', timeout=0):
        try:
            answer(args, callback, stdin, timeout)
        except subprocess.CalledProcessError as exc:
            return exc.returncode
        return 0
    return types.SimpleNamespace(
        globalstorage=types.SimpleNamespace(value=lambda key: values.get(key), insert=values.__setitem__,
                                            contains=lambda key: key in values),
        job=types.SimpleNamespace(configuration=configuration or {}, setprogress=log.progress.append),
        utils=types.SimpleNamespace(target_env_call=call or (lambda *args: 0),
                                    target_env_process_output=exit_code_only,
                                    check_target_env_call=call or (lambda *args: 0),
                                    check_target_env_output=check_output,
                                    warning=log.warnings.append, debug=lambda *args: None,
                                    gettext_path=lambda: None, gettext_languages=lambda: []),
        log=log, values=values)


def load_module(name, fake, path=None):
    with patch.dict(sys.modules, {'libcalamares': fake, 'libcalamares.utils': fake.utils}):
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
        schemas = {'welcomecheck': 'welcome', 'corrysystem-init': 'corrysystem',
                   'corrysystem-bootloader': 'corrysystem'}
        for config in (PROFILE / 'modules').glob('*.conf'):
            module = schemas.get(config.stem, config.stem)
            schema = ROOT / f'src/modules/{module}/{module}.schema.yaml'
            if schema.exists():
                jsonschema.Draft7Validator(yaml.safe_load(schema.read_text())).validate(yaml.safe_load(config.read_text()))
        shown = settings['sequence'][0]['show']
        # Init system and boot loader are two separate pages, in that order.
        self.assertEqual(shown, ['welcome', 'welcome@check', 'locale', 'keyboard', 'partition', 'users',
                                 'corrysystem@init', 'corrysystem@bootloader', 'summary'])
        self.assertEqual(instances['corrysystem@init']['config'], 'corrysystem-init.conf')
        self.assertEqual(instances['corrysystem@bootloader']['config'], 'corrysystem-bootloader.conf')
        self.assertFalse((PROFILE / 'modules/corrysystem.conf').exists())
        jobs = settings['sequence'][1]['exec']
        for removed in ['packagechooser', 'corryprepare', 'corrypackages']:
            self.assertNotIn(removed, shown + jobs)
            self.assertFalse((ROOT / 'src/modules' / removed / 'module.desc').exists())
        self.assertEqual(jobs[0], 'partition')
        # The init system is switched after the online repair and before the
        # initramfs; the alternative boot loader is installed after the initramfs
        # exists and before GRUB would be configured.
        order = ['unpackfs', 'users', 'corrycleanup', 'corryupdate', 'corryinit', 'corrygrub', 'initramfs',
                 'corrybootloader', 'grubcfg', 'bootloader']
        for before, after in zip(order, order[1:]):
            self.assertLess(jobs.index(before), jobs.index(after), (before, after))
        self.assertEqual(jobs[-1], 'umount')
        build = (ROOT / 'tools/build-corry.sh').read_text()
        for name in shown + jobs + ['finished']:
            self.assertIn(' ' + name.split('@')[0] + ' ', build)
        # The profile ships the same module settings the modules are tested with.
        for module, name in [('corrysystem', 'corrysystem-init'), ('corrysystem', 'corrysystem-bootloader'),
                             ('corryinit', 'corryinit'), ('corrybootloader', 'corrybootloader')]:
            self.assertEqual((PROFILE / f'modules/{name}.conf').read_text(),
                             (ROOT / f'src/modules/{module}/{name}.conf').read_text(), name)

    def test_workflows_have_no_duplicate_keys(self):
        # GitHub rejects a workflow file with a repeated key; PyYAML would keep the last one.
        class Strict(yaml.SafeLoader):
            pass

        def mapping(loader, node, deep=False):
            keys = [str(loader.construct_object(key, deep=deep)) for key, _ in node.value]
            self.assertEqual(len(keys), len(set(keys)), keys)
            return yaml.SafeLoader.construct_mapping(loader, node, deep)
        Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, mapping)
        for workflow in (ROOT / '.github/workflows').glob('*.yml'):
            data = yaml.load(workflow.read_text(), Loader=Strict)
            self.assertIn('jobs', data, workflow.name)
        corry = yaml.safe_load((ROOT / '.github/workflows/corry.yml').read_text())
        self.assertEqual(list(corry['jobs']), ['package', 'init-switch', 'e2e', 'release'])
        self.assertEqual(corry['jobs']['release']['needs'], ['package', 'init-switch', 'e2e'])
        self.assertEqual(corry['jobs']['init-switch']['strategy']['matrix']['init'], ['sysvinit', 'openrc', 'runit'])

    def test_system_components_options(self):
        init_page = yaml.safe_load((PROFILE / 'modules/corrysystem-init.conf').read_text())
        loader_page = yaml.safe_load((PROFILE / 'modules/corrysystem-bootloader.conf').read_text())
        self.assertEqual((init_page['section'], loader_page['section']), ('init', 'bootloader'))
        # Each page holds only its own options; the base is filled in per distribution.
        self.assertNotIn('bootloader', init_page)
        self.assertNotIn('init', loader_page)
        self.assertEqual((init_page['base'], loader_page['base']), ('', ''))
        init, loaders = init_page['init'], loader_page['bootloader']
        self.assertEqual([o['id'] for o in init], ['systemd', 'sysvinit', 'openrc', 'runit'])
        self.assertEqual([o['id'] for o in loaders], ['grub', 'systemd-boot', 'refind', 'extlinux'])
        for group in (init, loaders):
            self.assertTrue(group[0].get('default'))
            self.assertFalse(group[0].get('packages'))
            self.assertNotIn('availableOn', group[0])
            for option in group[1:]:
                self.assertFalse(option.get('default'), option['id'])
                self.assertTrue(option['packages'], option['id'])
                self.assertTrue(option['description'].isascii())
                self.assertTrue(set(option['availableOn']) <= {'stable', 'testing'}, option['id'])
        # Each init option names exactly one provider of /sbin/init (verified after the
        # switch; OpenRC runs on SysVinit's init), elogind for sessions, and the pieces
        # systemd used to provide: a session bus, a syslog and cron.
        for option in init[1:]:
            providers = [p for p in option['packages'] if p in ('sysvinit-core', 'runit-init')]
            self.assertEqual(len(providers), 1, option['id'])
            for needed in ['elogind', 'libpam-elogind', 'dbus-x11', 'rsyslog', 'cron']:
                self.assertIn(needed, option['packages'], option['id'])
            self.assertEqual(option['availableOn'], ['stable', 'testing'], option['id'])
        self.assertEqual(init[2]['packages'][0], 'openrc')
        by_id = {o['id']: o for o in loaders}
        self.assertEqual(by_id['systemd-boot']['firmware'], ['efi'])
        self.assertTrue(by_id['systemd-boot']['needsSystemd'])
        self.assertEqual(by_id['refind']['firmware'], ['efi'])
        self.assertEqual(by_id['extlinux']['firmware'], ['bios'])
        self.assertNotIn('btrfs', by_id['extlinux']['filesystems'])
        self.assertNotIn('xfs', by_id['refind']['filesystems'])
        # rEFInd is not in Debian testing; U-Boot is not offered (amd64 packages).
        self.assertEqual(by_id['refind']['availableOn'], ['stable'])
        self.assertNotIn('uboot', by_id)
        self.assertTrue(by_id['grub'].get('secureBoot'))
        self.assertFalse(any(o.get('secureBoot') for o in loaders[1:]))
        # The boot loader job has an installer for every alternative on the page.
        job = load_module('corrybootloader', fake_calamares())
        self.assertEqual(sorted(job.INSTALLERS), sorted(o['id'] for o in loaders[1:]))

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
        # Timor-Leste: Dili is preselected; the live session's clock is left alone.
        locale = yaml.safe_load((modules / 'locale.conf').read_text())
        self.assertEqual((locale['region'], locale['zone']), ('Asia', 'Dili'))
        self.assertFalse(locale['useSystemTimezone'])
        self.assertEqual(locale['geoip']['style'], 'none')
        self.assertEqual((ROOT / 'VERSION').read_text().strip(), '1.0')


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
                branding = self.branding()
                data = branding.load(ROOT / f'config/distros/{distro}')
                theme = data['theme-data']
                self.assertEqual(desc['sidebar'], 'qml,' + theme['layout'])
                self.assertTrue((brand / desc['images']['productWelcome']).is_file())
                source = yaml.safe_load((ROOT / f'config/distros/{distro}/distro.yaml').read_text())
                slides = json.loads((brand / 'slides/Slides.js').read_text().split('var slides = ')[1].rstrip(';\n'))
                self.assertGreaterEqual(len(slides), 5)
                for slide in slides:
                    self.assertTrue((brand / 'slides' / slide['image']).is_file())
                    self.assertTrue(slide['title'].isascii() and slide['description'].isascii())
                # Images only: no video anywhere in the profile.
                media = json.loads((brand / 'media.js').read_text().split('var media = ')[1].rstrip(';\n'))
                self.assertEqual(sorted(media), ['poster', 'sound', 'volume'])
                self.assertTrue((brand / media['poster']).is_file())
                self.assertTrue((brand / media['sound']).is_file())
                self.assertFalse(list(brand.rglob('*.webm')) + list(brand.rglob('CorryVideo*')))
                self.assertNotIn('video', (brand / 'welcome-media.qml').read_text().lower())
                version = (ROOT / 'VERSION').read_text().strip()
                values = branding.tokens(data)
                # Every themed file is its source with the theme tokens and the version
                # filled in, and no token is left.
                for themed in branding.THEMED:
                    expected = branding.themed_text((ROOT / 'src/branding/corry' / themed).read_text(), values, themed)
                    expected = expected.replace('@CORRY_VERSION@', version)
                    text = (brand / themed).read_text()
                    self.assertEqual(text, expected, themed)
                    self.assertIsNone(branding.TOKEN.search(text), themed)
                stylesheet = (brand / 'stylesheet.qss').read_text()
                for key in ['page', 'accent', 'accent-light', 'accent-dark', 'surface', 'text']:
                    self.assertIn(data['colors'][key], stylesheet, key)
                header = (brand / 'calamares-sidebar.qml').read_text()
                self.assertEqual(header, branding.themed_text(
                    (ROOT / 'src/branding/corry' / branding.HEADERS[theme['layout']]).read_text(), values,
                    'header').replace('@CORRY_VERSION@', version))
                self.assertIn(version, header)
                for source_header in branding.HEADERS.values():
                    self.assertFalse((brand / source_header).exists(), source_header)
                # GRUB's EFI directory is what Debian's grub-efi upgrades derive from
                # GRUB_DISTRIBUTOR (the boot menu name), so updates refresh it.
                efi = {'edukasaun': 'edukasaun', 'debion': 'debion'}[distro]
                self.assertEqual(yaml.safe_load((config / 'modules/bootloader.conf').read_text())['efiBootloaderId'], efi)
                self.assertEqual(yaml.safe_load((config / 'modules/corrybootloader.conf').read_text())['grubEfiDirectory'],
                                 efi)
                self.assertEqual(desc['strings']['bootloaderEntryName'], {'edukasaun': 'Edukasaun', 'debion': 'DebION'}[distro])
                for page in ['corrysystem-init', 'corrysystem-bootloader']:
                    self.assertEqual(yaml.safe_load((config / f'modules/{page}.conf').read_text())['base'],
                                     source['debian'], page)
                self.assertFalse((config / 'modules/packagechooser.conf').exists())
                grub = yaml.safe_load((config / 'modules/corrygrub.conf').read_text())
                self.assertEqual(grub['medium'], '/tmp')
                self.assertEqual(grub['checkUrl'], source['internet-check-url'])
                for job in ['corryupdate', 'corryinit', 'corrybootloader']:
                    self.assertEqual(yaml.safe_load((config / f'modules/{job}.conf').read_text())['checkUrl'],
                                     source['internet-check-url'], job)
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
        # The two distributions: Edukasaun on Debian stable with the warm pastel
        # theme and a side menu; DebION on Debian testing with the soft blue one.
        branding = self.branding()
        edukasaun, debion = (branding.load(ROOT / f'config/distros/{d}') for d in DISTROS)
        self.assertEqual((edukasaun['debian'], edukasaun['theme'], edukasaun['theme-data']['layout']),
                         ('stable', 'warm-pastel', 'left'))
        self.assertEqual((debion['debian'], debion['theme'], debion['theme-data']['layout']),
                         ('testing', 'soft-blue', 'top'))
        with stage('edukasaun', '--autostart') as temp:
            self.assertIn('Exec=corry-installer', (Path(temp) / 'etc/xdg/autostart/corry-installer.desktop').read_text())

    def test_package_mode_writes_only_profile_files(self):
        with stage('debion', '--package') as temp:
            root = Path(temp)
            files = sorted(str(p.relative_to(root)) for p in root.rglob('*') if p.is_file() or p.is_symlink())
            self.assertTrue(all(f.startswith(('etc/calamares/', 'usr/share/applications/', 'usr/bin/install-debian',
                                              'usr/share/icons/hicolor/scalable/apps/corry-installer.svg'))
                                for f in files), files)
            self.assertEqual(os.readlink(root / 'usr/bin/install-debian'), 'corry-installer')
            self.assertIn('Name=Install DebION GNU/Linux', (root / 'usr/share/applications/corry-installer.desktop').read_text())

    def test_debian_packaging(self):
        control = (ROOT / 'debian/control').read_text()
        packages = {block.split('\n')[0]: block for block in control.split('\nPackage: ')[1:]}
        # One complete installer package per distribution, nothing else.
        self.assertEqual(sorted(packages), ['corry-debion', 'corry-edukasaun'])
        for name, other in [('corry-edukasaun', 'corry-debion'), ('corry-debion', 'corry-edukasaun')]:
            fields = {l.split(':', 1)[0]: l.split(':', 1)[1] for l in packages[name].splitlines() if ':' in l and l[0] != ' '}
            self.assertEqual(fields['Architecture'].strip(), 'any')
            for field in ['Conflicts', 'Replaces']:
                for conflict in [other, 'corry (<< 0.2)', 'calamares', 'calamares-settings-debian']:
                    self.assertIn(conflict, [c.strip() for c in fields[field].split(',')], (name, field))
            self.assertIn('calamares', fields['Provides'])
            install = (ROOT / f'debian/{name}.install').read_text()
            for path in ['usr/bin/calamares', 'tools/remove-calamares', 'tools/corry-desktop-icon', 'tools/corry-session',
                         'config/corry/polkit/io.github.corry-installer.session.policy',
                         'config/corry/apt/80corry-remove-calamares']:
                self.assertIn(path, install)
            postinst = (ROOT / f'debian/{name}.postinst').read_text()
            self.assertIn('corry-desktop-icon --all-users', postinst)
            self.assertIn('remove-calamares --leftovers', postinst)
            self.assertIn('corry-desktop-icon --remove-all', (ROOT / f'debian/{name}.prerm').read_text())
        self.assertIn('Debian stable', packages['corry-edukasaun'])
        self.assertIn('Debian testing', packages['corry-debion'])
        self.assertEqual((ROOT / 'debian/changelog').read_text().split('(')[1].split(')')[0],
                         (ROOT / 'VERSION').read_text().strip())
        rules = (ROOT / 'debian/rules').read_text()
        self.assertIn('--no-automatic-dbgsym', rules)
        build = (ROOT / 'tools/build-corry.sh').read_text()
        block = re.search(r'^KEEP := ((?:.*\\\n)*.*)$', rules, re.M).group(1)
        self.assertEqual(set(block.replace('\\', ' ').split()), set(build.split("keep='")[1].split("'")[0].split()))

    def test_desktop_shortcut_for_every_user(self):
        script = ROOT / 'tools/corry-desktop-icon'
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            bin_dir, launcher = temp / 'bin', temp / 'corry-installer.desktop'
            bin_dir.mkdir()
            launcher.write_text('[Desktop Entry]\nName=Install Edukasaun OS\nExec=corry-installer\n')
            homes = {'user': temp / 'home/user', 'hugo': temp / 'home/hugo'}
            for home in homes.values():
                home.mkdir(parents=True)
            (homes['hugo'] / 'Desktop').mkdir()
            (homes['hugo'] / 'Desktop/notes.desktop').write_text('Exec=other\n')
            passwd = ''.join(f'{u}:x:{1000 + i}:{1000 + i}::{h}:/bin/bash\n' for i, (u, h) in enumerate(homes.items()))
            passwd += f'nobody:x:65534:65534::{temp}:/usr/sbin/nologin\nroot:x:0:0::/root:/bin/bash\n'
            stubs = {
                'getent': f'cat <<"EOF"\n{passwd}EOF',
                # runuser -u USER -- xdg-user-dir DESKTOP: answer per user ("Escritorio" for one).
                # runuser -u USER -- xdg-user-dir DESKTOP answers per user ("Escritorio" for one);
                # other commands run as the test's own user.
                'runuser': f'u=$2; shift 3; if [ "$1" = xdg-user-dir ]; then case "$u" in user) echo {homes["user"]}/Escritorio;; '
                           f'*) echo {homes["hugo"]}/Desktop;; esac; else echo "$u $*" >> {temp}/runuser.log; exec "$@"; fi',
                'install': 'args=""; while [ $# -gt 0 ]; do case "$1" in -o|-g) shift 2;; *) args="$args $1"; shift;; esac; done; exec /usr/bin/install $args',
                'id': 'echo users',
            }
            for name, body in stubs.items():
                (bin_dir / name).write_text('#!/bin/sh\n' + body + '\n')
                (bin_dir / name).chmod(0o755)
            source = script.read_text().replace('/usr/share/applications/corry-installer.desktop', str(launcher))
            env = {'PATH': f'{bin_dir}:/usr/bin:/bin'}
            run = lambda mode: subprocess.run(['sh', '-c', source, 'corry-desktop-icon', mode], env=env, check=True)
            run('--all-users')
            shortcut_user = homes['user'] / 'Escritorio/corry-installer.desktop'
            shortcut_hugo = homes['hugo'] / 'Desktop/corry-installer.desktop'
            for shortcut in (shortcut_user, shortcut_hugo):
                self.assertIn('Exec=corry-installer', shortcut.read_text())
                self.assertTrue(os.access(shortcut, os.X_OK))
            self.assertTrue((homes['hugo'] / '.config/corry/desktop-icon-done').exists())
            # Root never wrote into a home itself: every write ran as the home's owner.
            as_users = (temp / 'runuser.log').read_text()
            self.assertIn('user sh -c mkdir', as_users)
            self.assertIn('hugo sh -c mkdir', as_users)
            self.assertNotIn('install -d -o', script.read_text())
            run('--remove-all')
            self.assertFalse(shortcut_user.exists() or shortcut_hugo.exists())
            self.assertTrue((homes['hugo'] / 'Desktop/notes.desktop').exists())

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
                (lambda d: d.update(colors={'accent': 'green'}), 'colors.accent'),
                (lambda d: d.update(colors={'acent': '#123456'}), 'not a theme color'),
                (lambda d: d.update(theme='neon'), 'Unknown theme'),
                (lambda d: d.update({'bootloader-name': 'Educação OS'}), 'plain ASCII word'),
                (lambda d: d.update(debian='sid'), 'Debian base'),
                (lambda d: d.pop('debian'), 'Debian base'),
                (lambda d: d['slides'][0].update(image='../escape.svg'), 'inside'),
                (lambda d: d['welcome'].update(image='slides/missing.png'), 'not found'),
                (lambda d: d['sound'].update(volume=3), 'volume')]:
                broken = json.loads(json.dumps(data))
                change(broken)
                (folder / 'distro.yaml').write_text(yaml.safe_dump(broken))
                with self.assertRaisesRegex(branding.BrandingError, message):
                    branding.load(folder)
            data['sound']['file'] = ''
            (folder / 'distro.yaml').write_text(yaml.safe_dump(data))
            self.assertEqual(branding.load(folder)['sound']['file'], '')
            # A video from an older distro.yaml is ignored with a note, not an error.
            data['welcome']['video'] = 'media/welcome.webm'
            (folder / 'distro.yaml').write_text(yaml.safe_dump(data))
            loaded = branding.load(folder)
            self.assertNotIn('video', loaded['welcome'])
            self.assertTrue(any('welcome.video' in w for w in branding.media_warnings(folder, loaded)))

    def test_themes(self):
        branding = self.branding()
        themes = sorted(p.stem for p in branding.THEMES.glob('*.yaml'))
        self.assertEqual(themes, ['soft-blue', 'warm-pastel'])
        used = set()
        for name in [*branding.THEMED, *branding.HEADERS.values()]:
            used |= set(branding.TOKEN.findall((ROOT / 'src/branding/corry' / name).read_text()))
        for name in themes:
            theme = branding.load_theme(name)
            self.assertEqual(set(theme['colors']), set(branding.THEME_COLORS), name)
            self.assertTrue(theme['font'], name)
            # Every token the sources use exists for every theme.
            values = branding.tokens({'theme-data': theme, 'colors': theme['colors']})
            self.assertEqual(used - set(values), set(), name)
            # Readable text: at least 4.5:1 for body text on the surfaces.
            def luminance(color):
                channel = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
                r, g, b = (channel(int(color[i:i + 2], 16) / 255) for i in (1, 3, 5))
                return 0.2126 * r + 0.7152 * g + 0.0722 * b
            def contrast(a, b):
                la, lb = sorted([luminance(a), luminance(b)], reverse=True)
                return (la + 0.05) / (lb + 0.05)
            colors = theme['colors']
            for text, background in [('text', 'surface'), ('text', 'page'), ('nav-text', 'nav'),
                                     ('warning-text', 'warning-bg'), ('danger-text', 'danger-bg')]:
                self.assertGreaterEqual(contrast(colors[text], colors[background]), 4.5, (name, text, background))
            self.assertGreaterEqual(contrast(colors['on-accent'], colors['accent-dark']), 3.0, name)
        with self.assertRaisesRegex(branding.BrandingError, 'unknown theme token'):
            branding.themed_text('color: "@nope@"', {}, 'test')

    def test_efi_directory_follows_grub_distributor(self):
        branding = self.branding()
        self.assertEqual(branding.efi_directory('DebION'), 'debion')
        self.assertEqual(branding.efi_directory('Edukasaun OS'), 'edukasaun')
        self.assertEqual(branding.efi_directory('Devuan GNU+Linux'), 'debian')
        self.assertEqual(branding.efi_directory(''), 'debian')

    def test_derived_accent_shades(self):
        branding = self.branding()
        for accent in ['#246452', '#2563eb', '#6445a4']:
            light, dark = branding.shade(accent, 1.45, 1.1), branding.shade(accent, 0.72)
            self.assertTrue(branding.COLOR.match(light) and branding.COLOR.match(dark), accent)
            luminance = lambda c: sum(int(c[i:i + 2], 16) for i in (1, 3, 5))
            self.assertGreater(luminance(light), luminance(accent))
            self.assertLess(luminance(dark), luminance(accent))
        # distro.yaml may set the shades itself.
        with tempfile.TemporaryDirectory() as temp:
            folder = Path(temp) / 'mine'
            shutil.copytree(ROOT / 'config/distros/debion', folder)
            data = yaml.safe_load((folder / 'distro.yaml').read_text())
            theme = branding.load_theme(data['theme'])
            self.assertEqual(branding.load(folder)['colors'], theme['colors'])
            data['colors'] = {'accent': '#246452'}
            (folder / 'distro.yaml').write_text(yaml.safe_dump(data))
            colors = branding.load(folder)['colors']
            self.assertEqual(colors['accent-light'], branding.shade('#246452', 1.45, 1.1))
            self.assertEqual(colors['accent-dark'], branding.shade('#246452', 0.72))
            data['colors']['accent-light'] = '#abcdef'
            (folder / 'distro.yaml').write_text(yaml.safe_dump(data))
            self.assertEqual(branding.load(folder)['colors']['accent-light'], '#abcdef')
            data['colors']['accent-dark'] = 'dark'
            (folder / 'distro.yaml').write_text(yaml.safe_dump(data))
            with self.assertRaisesRegex(branding.BrandingError, 'accent-dark'):
                branding.load(folder)

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
            for part in ['tools', 'config/distros/debion', 'config/themes']:
                shutil.copytree(ROOT / part, repo / part)
            subprocess.run([sys.executable, str(repo / 'tools/new-distro.py'), 'demo-os', 'Demo OS',
                            '--accent', '#123456', '--theme', 'warm-pastel', '--debian', 'stable', '--no-media'],
                           check=True, stdout=subprocess.PIPE)
            data = yaml.safe_load((repo / 'config/distros/demo-os/distro.yaml').read_text())
            self.assertEqual((data['name'], data['colors']['accent']), ('Demo OS', '#123456'))
            self.assertEqual((data['theme'], data['debian']), ('warm-pastel', 'stable'))
            self.assertEqual(data['bootloader-name'], 'Demo')
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

        def call(args, *rest):
            calls.append(args)
            if args[0] == 'dpkg-query':
                return 0 if args[-1] in ('live-config', 'calamares', 'lvm2', 'cryptsetup-initramfs') else 1
            return 0
        with tempfile.TemporaryDirectory() as temp:
            fake = fake_calamares({'rootMountPoint': temp, 'username': 'hugo'}, {'liveUser': 'user'}, call)
            self.assertIsNone(load_module('corrycleanup', fake).run())
        self.assertIn(['dpkg', '--purge', 'live-config', 'calamares'], calls)
        self.assertFalse(any('autoremove' in args for args in calls))
        # What the system needs stays even if it came in only for Corry.
        marks = [args for args in calls if args[:2] == ['apt-mark', 'manual']]
        self.assertEqual(len(marks), 1)
        self.assertLess(calls.index(marks[0]), calls.index(['dpkg', '--purge', 'live-config', 'calamares']))
        self.assertIn(['userdel', '--', 'user'], calls)
        self.assertFalse(any('--remove' in args or '-r' in args for args in calls))

    def test_cleanup_never_fails_when_dpkg_refuses(self):
        # A live meta-package depends on live-config: dpkg refuses the set and that
        # one package, the others are purged one by one; the installation goes on.
        calls = []

        def call(args, *rest):
            calls.append(args)
            if args[0] == 'dpkg-query':
                return 0 if args[-1] in ('live-config', 'live-boot', 'calamares') else 1
            if args[:2] == ['dpkg', '--purge']:
                return 1 if 'live-config' in args else 0
            return 0
        with tempfile.TemporaryDirectory() as temp:
            fake = fake_calamares({'rootMountPoint': temp, 'username': 'hugo'}, {}, call)
            self.assertIsNone(load_module('corrycleanup', fake).run())
        self.assertIn(['dpkg', '--purge', 'live-boot'], calls)
        self.assertIn(['dpkg', '--purge', 'calamares'], calls)
        self.assertFalse(any('apt-get' in args for args in calls))
        self.assertTrue(any('live-config stay installed' in w for w in fake.log.warnings), fake.log.warnings)

    def test_cleanup_keeps_new_user_named_like_live_user(self):
        calls = []
        with tempfile.TemporaryDirectory() as temp:
            fake = fake_calamares({'rootMountPoint': temp, 'username': 'user'}, {'liveUser': 'user'},
                                  lambda args, *rest: calls.append(args) or (1 if args[0] == 'dpkg-query' else 0))
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
                                  lambda args, *rest: 1 if args[0] in ('dpkg-query', 'id') else 0)
            self.assertIsNone(load_module('corrycleanup', fake).run())
            self.assertEqual([p for p in corry if (root / p).exists()], [])
            for directory in ['etc/calamares', 'usr/lib/corry', 'usr/share/calamares']:
                self.assertFalse((root / directory).exists(), directory)
            self.assertTrue(all((root / p).exists() for p in keep))
            self.assertTrue((root / 'usr/share/applications').is_dir())
            # An unsafe path is refused and reported; it never stops the installation.
            fake.job.configuration['removeFiles'] = ['../outside']
            self.assertIsNone(load_module('corrycleanup', fake).run())
            self.assertTrue(any('Unsafe path' in w for w in fake.log.warnings), fake.log.warnings)


class GrubTests(unittest.TestCase):
    def test_grub_package_selection_and_medium(self):
        fake = fake_calamares()
        grub = load_module('corrygrub', fake)
        self.assertEqual(grub.wanted('efi', 'amd64'), ('grub-efi-amd64', 'x86_64-efi'))
        self.assertEqual(grub.wanted('bios', 'amd64'), ('grub-pc', 'i386-pc'))
        self.assertEqual(grub.wanted('bios', 'arm64'), (None, None))
        # 32-bit UEFI firmware with a 64-bit CPU: GRUB's i386-efi platform.
        self.assertEqual(grub.wanted('efi', 'amd64', '32'), ('grub-efi-ia32', 'i386-efi'))
        self.assertEqual(grub.wanted('efi', 'amd64', '64'), ('grub-efi-amd64', 'x86_64-efi'))
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
            # UEFI: signed GRUB and shim for Secure Boot, best effort.
            values['firmwareType'] = 'efi'
            calls.clear()
            with patch.object(grub.subprocess, 'run', return_value=arch), patch.object(grub, 'online', return_value=True), \
                    patch.object(grub.shutil, 'copyfile', side_effect=lambda src, dst: Path(dst).write_text('x')):
                self.assertIsNone(grub.run())
            installed_packages = [c[-1] for c in calls if 'install' in c]
            self.assertEqual(installed_packages, ['grub-efi-amd64', 'shim-signed', 'grub-efi-amd64-signed'])
            # If they cannot be installed, the installation still continues.
            fake.utils.target_env_call = lambda args: 1 if 'shim-signed' in args else 0
            with patch.object(grub.subprocess, 'run', return_value=arch), patch.object(grub, 'online', return_value=True), \
                    patch.object(grub.shutil, 'copyfile', side_effect=lambda src, dst: Path(dst).write_text('x')):
                self.assertIsNone(grub.run())
            self.assertIn('Secure Boot', fake.log.warnings[-1])


class UpdateTests(unittest.TestCase):
    def run_update(self, online, failing=()):
        calls = []

        self.timeouts = {}

        def call(args, stdin='', timeout=0):
            calls.append(args[2:])
            self.timeouts[' '.join(args[2:5])] = timeout
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
        # Downloaded first (safe to interrupt), then installed without a time limit.
        download = next(c for c in calls if '--download-only' in c)
        install = next(c for c in calls if '--no-download' in c and 'upgrade' in c)
        self.assertIn('upgrade', download)
        self.assertLess(calls.index(download), calls.index(install))
        # dpkg is never killed half-way: no time limit once packages are installed.
        self.assertEqual(self.timeouts[' '.join(install[:3])], 0)
        self.assertGreater(self.timeouts[' '.join(download[:3])], 0)
        self.assertFalse(any('full-upgrade' in c for c in calls))

    def test_network_problems_never_fail_installation(self):
        calls, warnings = self.run_update(True, failing=('update',))
        self.assertFalse(any('upgrade' in c for c in calls))
        self.assertTrue(warnings)


class InitTests(unittest.TestCase):
    """corryinit: switch the init system only when apt removes nothing but systemd."""

    def setup(self, wanted='sysvinit', online=True, removed='systemd-sysv libpam-systemd', install_code=0,
              owner='sysvinit-core', purge_extra='', configuration=None, download_code=0):
        calls = []
        self.timeouts = []
        system = {'init': {'id': wanted, 'name': wanted, 'default': wanted == 'systemd',
                           'packages': [] if wanted == 'systemd' else
                           {'sysvinit': ['sysvinit-core', 'elogind', 'libpam-elogind'],
                            'runit': ['runit-init', 'elogind', 'libpam-elogind']}[wanted]}}

        def call(args, stdin='', timeout=0):
            calls.append(args)
            self.timeouts.append((args, timeout))
            if 'install' in args and '-s' not in args and 'apt-get' in args:
                return download_code if '--download-only' in args else install_code
            return 0

        def process_output(args, callback=None, stdin='', timeout=0):
            calls.append(args)
            if '-s' in args and 'install' in args:
                return ''.join(f'Remv {p} [1]\n' for p in removed.split()) + 'Inst sysvinit-core (3.14 Debian)\n'
            if '-s' in args and 'purge' in args:
                requested = args[args.index('purge') + 1:]
                # Purging systemd itself may drag another package along (purge_extra).
                # A simulated purge reports "Purg", as real apt does.
                return ''.join(f'Purg {p} [1]\n' for p in requested) + (purge_extra if 'systemd' in requested else '')
            if args[0] == 'dpkg-query' and '-W' in args:
                return 'ii ' if args[-1] in ('systemd-sysv', 'libpam-systemd', 'systemd', 'sysvinit-core', 'sysv-rc') else 'un '
            if args[0] == 'readlink':
                return '/usr/sbin/init\n'
            if args[0] == 'dpkg-query' and '-S' in args:
                return f'{owner}: /usr/sbin/init\n'
            return ''
        temp = tempfile.TemporaryDirectory()
        root = Path(temp.name)
        (root / 'etc').mkdir()
        (root / 'etc/resolv.conf').write_text('# target\n')
        fake = fake_calamares({'rootMountPoint': temp.name, 'corrySystem': system},
                              configuration or yaml.safe_load((PROFILE / 'modules/corryinit.conf').read_text()),
                              call, process_output)
        module = load_module('corryinit', fake)
        with patch.object(module, 'online', return_value=online):
            result = module.run()
        self.assertFalse((root / 'usr/sbin/policy-rc.d').exists())
        self.assertEqual((root / 'etc/resolv.conf').read_text(), '# target\n')
        temp.cleanup()
        return result, calls, fake

    def test_default_init_changes_nothing(self):
        result, calls, fake = self.setup('systemd')
        self.assertIsNone(result)
        self.assertEqual(calls, [])
        self.assertEqual(fake.log.warnings, [])

    def test_offline_keeps_systemd(self):
        result, calls, fake = self.setup(online=False)
        self.assertIsNone(result)
        self.assertEqual(calls, [])
        self.assertIn('offline', fake.log.warnings[0])
        self.assertEqual(fake.values['corrySystem']['init']['installed'], 'systemd')

    def test_desktop_that_needs_systemd_blocks_the_switch(self):
        result, calls, fake = self.setup(removed='systemd-sysv gdm3 gnome-shell')
        self.assertIsNone(result)
        self.assertFalse(any('install' in c and '-s' not in c for c in calls if 'apt-get' in c))
        self.assertIn('gdm3', fake.log.warnings[0])
        self.assertIn('gnome-shell', fake.log.warnings[0])
        self.assertEqual(fake.values['corrySystem']['init']['installed'], 'systemd')

    def test_installed_gdm_is_refused_before_apt_runs(self):
        calls = []

        def process_output(args, callback=None, stdin='', timeout=0):
            calls.append(args)
            if args[0] == 'dpkg-query' and '-W' in args:
                return 'ii ' if args[-1] in ('gdm3', 'systemd-sysv') else 'un '
            return ''
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / 'etc').mkdir()
            system = {'init': {'id': 'runit', 'name': 'runit', 'packages': ['runit-init', 'elogind']}}
            fake = fake_calamares({'rootMountPoint': temp, 'corrySystem': system},
                                  yaml.safe_load((PROFILE / 'modules/corryinit.conf').read_text()),
                                  lambda args, *rest: calls.append(args) or 0, process_output)
            module = load_module('corryinit', fake)
            with patch.object(module, 'online', return_value=True):
                self.assertIsNone(module.run())
        self.assertFalse(any('apt-get' in c and 'clean' not in c for c in calls))
        self.assertIn('gdm3 need systemd', fake.log.warnings[-1])
        self.assertEqual(fake.values['corrySystem']['init']['installed'], 'systemd')

    def test_apt_flags_for_debian_testing(self):
        module = load_module('corryinit', fake_calamares())
        self.assertIn('--allow-remove-essential', module.APT)  # systemd-sysv is Essential on Debian testing
        self.assertIn('--no-install-recommends', module.APT)

    def test_switch_then_retire_systemd(self):
        result, calls, fake = self.setup()
        self.assertIsNone(result)
        # The packages are downloaded first; then the switch installs them, with
        # explicit removal of the installed systemd packages (apt keeps manually
        # installed packages unless asked), and no time limit.
        downloads = [c for c in calls if 'apt-get' in c and '--download-only' in c]
        self.assertEqual(downloads[0][downloads[0].index('install') + 1:],
                         ['sysvinit-core', 'elogind', 'libpam-elogind', 'systemd-sysv-', 'libpam-systemd-', 'systemd-'])
        installs = [c for c in calls if 'apt-get' in c and 'install' in c and '--no-download' in c]
        self.assertEqual(installs[0][installs[0].index('install') + 1:],
                         ['sysvinit-core', 'elogind', 'libpam-elogind', 'systemd-sysv-', 'libpam-systemd-', 'systemd-'])
        self.assertIn((installs[0], 0), self.timeouts)
        self.assertLess(calls.index(downloads[0]), calls.index(installs[0]))
        simulations = [c for c in calls if 'apt-get' in c and '-s' in c and 'install' in c]
        self.assertEqual(simulations[0][simulations[0].index('install') + 1:], installs[0][installs[0].index('install') + 1:])
        purges = [c for c in calls if 'apt-get' in c and 'purge' in c and '-s' not in c]
        self.assertEqual(len(purges), 1)
        self.assertEqual(sorted(purges[0][purges[0].index('purge') + 1:]), ['libpam-systemd', 'systemd', 'systemd-sysv'])
        self.assertEqual(fake.log.warnings, [])
        self.assertEqual(fake.values['corrySystem']['init']['installed'], 'sysvinit')
        message = fake.values['corrySystem']['init']['message']
        self.assertTrue(all(name in message for name in ['removed:', 'systemd-sysv', 'libpam-systemd', 'systemd']), message)

    def test_resolved_stub_link_is_replaced_after_the_switch(self):
        module = load_module('corryinit', fake_calamares(process_output=lambda args, *rest: 'un '))
        with tempfile.TemporaryDirectory() as temp:
            etc = Path(temp) / 'etc'
            etc.mkdir()
            (etc / 'resolv.conf').symlink_to('../run/systemd/resolve/stub-resolv.conf')
            self.assertTrue(module.fix_resolv_conf(temp))
            self.assertFalse((etc / 'resolv.conf').is_symlink())
            self.assertIn('systemd-resolved', (etc / 'resolv.conf').read_text())
            # A regular file, or a link to something else, stays as it is.
            self.assertFalse(module.fix_resolv_conf(temp))
        module = load_module('corryinit', fake_calamares(process_output=lambda args, *rest: 'ii '))
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / 'etc').mkdir()
            (Path(temp) / 'etc/resolv.conf').symlink_to('../run/systemd/resolve/stub-resolv.conf')
            self.assertFalse(module.fix_resolv_conf(temp))  # systemd-resolved still installed

    def test_systemd_stays_when_something_still_needs_it(self):
        # Purging systemd would also remove another package: keep it, drop only what is safe.
        result, calls, fake = self.setup(purge_extra='Purg something-else [1]\n')
        purges = [c for c in calls if 'apt-get' in c and 'purge' in c and '-s' not in c]
        self.assertEqual(len(purges), 1)
        self.assertEqual(sorted(purges[0][purges[0].index('purge') + 1:]), ['libpam-systemd', 'systemd-sysv'])
        self.assertTrue(any('stay installed' in w for w in fake.log.warnings))
        self.assertEqual(fake.values['corrySystem']['init']['installed'], 'sysvinit')

    def test_failed_switch_restores_systemd(self):
        result, calls, fake = self.setup('runit', install_code=1, owner='systemd-sysv')
        self.assertIsNone(result)
        self.assertTrue(any('--fix-broken' in c for c in calls))
        self.assertIn('keeps systemd', fake.log.warnings[-1])
        self.assertEqual(fake.values['corrySystem']['init']['installed'], 'systemd')
        self.assertFalse(any('purge' in c for c in calls))

    def test_failed_download_changes_nothing(self):
        result, calls, fake = self.setup(download_code=1)
        self.assertIsNone(result)
        self.assertFalse(any('--no-download' in c for c in calls))
        self.assertIn('could not be downloaded', fake.log.warnings[-1])
        self.assertEqual(fake.values['corrySystem']['init']['installed'], 'systemd')

    def test_unexpected_error_keeps_systemd(self):
        # removed=None makes the apt simulation fake raise inside the job.
        result, calls, fake = self.setup(removed=None, owner='systemd-sysv')
        self.assertIsNone(result)
        self.assertTrue(any('unexpected AttributeError' in w for w in fake.log.warnings), fake.log.warnings)
        self.assertEqual(fake.values['corrySystem']['init']['installed'], 'systemd')

    def test_wrong_init_owner_is_reported(self):
        result, calls, fake = self.setup(owner='systemd-sysv')
        self.assertIn('/sbin/init still belongs to systemd-sysv', fake.log.warnings[-1])
        self.assertFalse(any('purge' in c and '-s' not in c for c in calls))
        # OpenRC's list starts with openrc, but /sbin/init belongs to sysvinit-core: that is right.
        module = load_module('corryinit', fake_calamares())
        self.assertEqual([p for p in ['openrc', 'sysvinit-core', 'elogind'] if p in module.INIT_PROVIDERS], ['sysvinit-core'])

    def test_openrc_replaces_sysv_rc_and_apt_refusals_are_explained(self):
        calls = []

        def process_output(args, callback=None, stdin='', timeout=0):
            calls.append(args)
            if '-s' in args and 'install' in args:
                raise subprocess.CalledProcessError(100, args, output='E: Unable to satisfy dependencies. Reached two '
                                                    'conflicting assignments:\n   1. systemd-sysv:amd64 is selected for install\n')
            if args[0] == 'dpkg-query' and '-W' in args:
                return 'ii ' if args[-1] in ('systemd-sysv', 'sysv-rc') else 'un '
            return ''
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / 'etc').mkdir()
            system = {'init': {'id': 'openrc', 'name': 'OpenRC', 'packages': ['openrc', 'sysvinit-core', 'elogind']}}
            fake = fake_calamares({'rootMountPoint': temp, 'corrySystem': system},
                                  yaml.safe_load((PROFILE / 'modules/corryinit.conf').read_text()),
                                  lambda args, *rest: 0, process_output)
            module = load_module('corryinit', fake)
            with patch.object(module, 'online', return_value=True):
                self.assertIsNone(module.run())
        simulation = [c for c in calls if '-s' in c][0]
        self.assertEqual(simulation[simulation.index('install') + 1:], ['openrc', 'sysvinit-core', 'elogind', 'systemd-sysv-', 'sysv-rc-'])
        self.assertIn('systemd-sysv:amd64 is selected for install', fake.log.warnings[-1])
        self.assertIn('keeps systemd', fake.log.warnings[-1])
        module = load_module('corryinit', fake_calamares())
        self.assertTrue(module.allowed_removal('systemd-timesyncd', set()))
        self.assertTrue(module.allowed_removal('libsystemd-shared', set()))
        self.assertTrue(module.allowed_removal('systemd', set()))
        self.assertFalse(module.allowed_removal('systemd-boot-manager-x', set()) is False)  # family prefix
        self.assertFalse(module.allowed_removal('gdm3', set()))
        self.assertFalse(module.allowed_removal('network-manager', set()))


class BootLoaderTests(unittest.TestCase):
    """corrybootloader: install an alternative loader, remove GRUB, or fall back to GRUB."""

    def make_root(self, temp, efi=True):
        root = Path(temp)
        for relative in ['boot/vmlinuz-6.12.0-1-amd64', 'boot/initrd.img-6.12.0-1-amd64', 'boot/vmlinuz-6.11.0-1-amd64',
                         'boot/initrd.img-6.11.0-1-amd64', 'boot/grub/grub.cfg', 'etc/default/grub', 'etc/grub.d/40_custom',
                         'usr/lib/EXTLINUX/mbr.bin', 'usr/lib/EXTLINUX/gptmbr.bin',
                         'usr/share/refind/refind/refind_x64.efi', 'usr/share/refind/refind/drivers_x64/ext4_x64.efi',
                         'usr/share/refind/refind/drivers_x64/btrfs_x64.efi', 'usr/share/refind/refind/icons/os_linux.png']:
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_text('x')
        (root / 'etc/machine-id').write_text('0123456789abcdef0123456789abcdef\n')
        (root / 'etc/resolv.conf').write_text('# target\n')
        if efi:
            (root / 'boot/efi/EFI/debian').mkdir(parents=True)
            (root / 'boot/efi/EFI/debian/grubx64.efi').write_bytes(b'GRUB binary')
            (root / 'boot/efi/EFI/BOOT').mkdir(parents=True)
            (root / 'boot/efi/EFI/BOOT/BOOTX64.EFI').write_bytes(b'GRUB fallback')
        return root

    def partitions(self, efi=True, fs='btrfs', separate_boot=False, esp_claimed=True):
        parts = [{'device': '/dev/sda2', 'fs': fs, 'mountPoint': '/', 'uuid': 'root-uuid'},
                 {'device': '/dev/sda3', 'fs': 'linuxswap', 'mountPoint': '', 'uuid': 'swap-uuid', 'claimed': True}]
        if efi:
            parts.insert(0, {'device': '/dev/sda1', 'fs': 'fat32', 'mountPoint': '/boot/efi', 'uuid': 'ESP1-2345',
                             'partuuid': 'esp-partuuid', 'claimed': esp_claimed})
        if separate_boot:
            parts.append({'device': '/dev/sda4', 'fs': 'ext4', 'mountPoint': '/boot', 'uuid': 'boot-uuid'})
        return parts

    def setup(self, temp, loader='systemd-boot', firmware='efi', fs='btrfs', online=True, bootctl_code=0,
              kernel_install=False, separate_boot=False, packages=None, esp_claimed=True, extra=None,
              parted_listing='', partitions=None):
        root = self.make_root(temp, efi=firmware == 'efi')
        hosts = []
        calls = []
        system = {'bootloader': {'id': loader, 'name': loader, 'default': loader == 'grub',
                                 'packages': packages if packages is not None else
                                 {'grub': [], 'systemd-boot': ['systemd-boot'], 'refind': ['refind'],
                                  'extlinux': ['extlinux', 'syslinux-common']}[loader]}}
        values = {'rootMountPoint': temp, 'corrySystem': system, 'firmwareType': firmware,
                  'efiSystemPartition': '/boot/efi',
                  'partitions': partitions or self.partitions(firmware == 'efi', fs, separate_boot, esp_claimed),
                  'btrfsRootSubvolume': '@' if fs == 'btrfs' else '', 'branding': {'bootloaderEntryName': 'Edukasaun OS'}}
        values.update(extra or {})

        def call(args, stdin='', timeout=0):
            calls.append(args)
            if args[0] == 'bootctl':
                if bootctl_code == 0 or '--no-variables' in args:
                    (root / 'boot/efi/EFI/systemd').mkdir(parents=True, exist_ok=True)
                    (root / 'boot/efi/EFI/systemd/systemd-bootx64.efi').write_text('systemd-boot')
                    (root / 'boot/efi/EFI/BOOT/BOOTX64.EFI').write_bytes(b'systemd-boot copy')
                    return 0
                return 1
            if args[0] == 'sh' and 'command -v kernel-install' in args[-1]:
                return 0 if kernel_install else 1
            if args[0] == 'kernel-install':
                (root / 'boot/efi/loader/entries').mkdir(parents=True, exist_ok=True)
                (root / f'boot/efi/loader/entries/id-{args[2]}.conf').write_text('title x\n')
                return 0
            if args[0] == 'extlinux':
                (root / 'boot/extlinux/ldlinux.sys').write_text('x')
                return 0
            return 0

        def process_output(args, callback=None, stdin='', timeout=0):
            calls.append(args)
            if args[0] == 'dpkg-query':
                return 'ii ' if args[-1] in ('grub-pc', 'grub-efi-amd64', 'grub2-common', 'grub-common', 'shim-signed',
                                             'systemd-boot', 'refind') else 'un '
            if args[0] == 'dpkg':
                return 'amd64\n'
            return ''

        def host(args, timeout=0):
            hosts.append(args)
            stdout = 'gpt\n' if args[0] == 'blkid' and firmware == 'efi' else 'dos\n' if args[0] == 'blkid' else ''
            if args[0] == 'efibootmgr' and '-v' in args:
                # Our ESP holds GRUB's entry and Windows; another disk has its own Debian.
                stdout = ('BootOrder: 0001,0002,0003\n'
                          'Boot0001* debian\tHD(1,GPT,esp-partuuid,0x800,0x96000)/File(\\EFI\\debian\\shimx64.efi)\n'
                          'Boot0002* Windows Boot Manager\tHD(1,GPT,esp-partuuid,0x800,0x96000)/File(\\EFI\\Microsoft\\Boot\\bootmgfw.efi)\n'
                          'Boot0003* debian\tHD(1,GPT,other-disk,0x800,0x96000)/File(\\EFI\\debian\\shimx64.efi)\n')
            if args[0] == 'parted' and '-m' in args:
                stdout = parted_listing
            return types.SimpleNamespace(returncode=0, stdout=stdout)
        fake = fake_calamares(values, yaml.safe_load((PROFILE / 'modules/corrybootloader.conf').read_text()), call,
                              process_output)
        module = load_module('corrybootloader', fake)
        with patch.object(module, 'online', return_value=online), patch.object(module, 'host', side_effect=host):
            result = module.run()
        self.assertFalse((root / 'usr/sbin/policy-rc.d').exists())
        self.assertEqual((root / 'etc/resolv.conf').read_text(), '# target\n')
        return result, calls, hosts, fake, root

    def test_grub_default_changes_nothing(self):
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'grub')
            self.assertIsNone(result)
            self.assertEqual(calls, [])
            self.assertTrue((root / 'boot/grub/grub.cfg').exists())

    def test_offline_falls_back_to_grub(self):
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'refind', online=False)
            self.assertIsNone(result)
            self.assertEqual(calls, [])
            self.assertIn('offline', fake.log.warnings[0])
            self.assertIn('GRUB is installed instead', fake.log.warnings[0])
            self.assertEqual(fake.values['corrySystem']['bootloader']['id'], 'grub')

    def test_firmware_mismatch_falls_back_to_grub(self):
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'systemd-boot', firmware='bios')
            self.assertIn('needs UEFI', fake.log.warnings[0])
            self.assertEqual(fake.values['corrySystem']['bootloader']['id'], 'grub')
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'extlinux', firmware='efi')
            self.assertIn('BIOS boot loader', fake.log.warnings[0])
            self.assertEqual(fake.values['corrySystem']['bootloader']['id'], 'grub')

    def test_systemd_boot_without_kernel_install_and_grub_removal(self):
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'systemd-boot')
            self.assertIsNone(result)
            self.assertEqual(fake.log.warnings, [])
            cmdline = (root / 'etc/kernel/cmdline').read_text()
            self.assertEqual(cmdline.split(), ['quiet', 'root=UUID=root-uuid', 'rootflags=subvol=@', 'resume=UUID=swap-uuid', 'rw'])
            esp = root / 'boot/efi'
            self.assertIn('timeout 5', (esp / 'loader/loader.conf').read_text())
            entries = sorted(p.name for p in (esp / 'loader/entries').glob('*.conf'))
            self.assertEqual(entries, ['0123456789abcdef0123456789abcdef-6.11.0-1-amd64.conf',
                                       '0123456789abcdef0123456789abcdef-6.12.0-1-amd64.conf'])
            entry = (esp / 'loader/entries' / entries[1]).read_text()
            self.assertIn('title Edukasaun OS', entry)
            self.assertIn('linux /0123456789abcdef0123456789abcdef/6.12.0-1-amd64/linux', entry)
            self.assertIn('options quiet root=UUID=root-uuid rootflags=subvol=@', entry)
            self.assertTrue((esp / '0123456789abcdef0123456789abcdef/6.12.0-1-amd64/initrd').exists())
            for hook in ['etc/kernel/postinst.d/zz-corry-systemd-boot', 'etc/initramfs/post-update.d/zz-corry-systemd-boot',
                         'etc/kernel/postrm.d/zz-corry-systemd-boot']:
                self.assertTrue(os.access(root / hook, os.X_OK), hook)
            # GRUB is gone: packages purged, files and, on this installation's freshly
            # formatted EFI partition, its EFI directory and its own NVRAM entry.
            purges = [c for c in calls if 'apt-get' in c and 'purge' in c]
            self.assertEqual(len(purges), 1)
            self.assertEqual(sorted(purges[0][purges[0].index('purge') + 1:]),
                             ['grub-common', 'grub-efi-amd64', 'grub-pc', 'grub2-common', 'shim-signed'])
            for gone in ['boot/grub', 'etc/default/grub', 'etc/grub.d', 'boot/efi/EFI/debian']:
                self.assertFalse((root / gone).exists(), gone)
            self.assertTrue((esp / 'EFI/systemd/systemd-bootx64.efi').exists())
            self.assertTrue((esp / 'EFI/BOOT/BOOTX64.EFI').exists())  # systemd-boot's own copy stays
            self.assertIn(['efibootmgr', '-b', '0001', '-B'], hosts)
            self.assertFalse(any(h[:3] == ['efibootmgr', '-b', '0002'] for h in hosts))  # Windows stays
            self.assertFalse(any(h[:3] == ['efibootmgr', '-b', '0003'] for h in hosts))  # another disk's Debian stays
            self.assertEqual(fake.values['corrySystem']['bootloader']['id'], 'systemd-boot')
            self.assertIn('GRUB removed', fake.values['corrySystem']['bootloader']['message'])

    def test_reused_efi_partition_keeps_other_systems(self):
        # Installed next to another Debian on its EFI partition: EFI/debian is that
        # system's (GRUB is not written to the ESP before this job), so it stays.
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'systemd-boot', esp_claimed=False)
            self.assertEqual(fake.values['corrySystem']['bootloader']['id'], 'systemd-boot')
            self.assertTrue((root / 'boot/efi/EFI/debian/grubx64.efi').exists())
            self.assertFalse(any(h[:2] == ['efibootmgr', '-b'] for h in hosts))
            self.assertFalse((root / 'boot/grub').exists())  # the target's own GRUB files are removed
            self.assertTrue(any('apt-get' in c and 'purge' in c for c in calls))

    def assert_falls_back(self, fake, calls, words):
        self.assertEqual(fake.values['corrySystem']['bootloader']['id'], 'grub')
        self.assertIn(words, fake.log.warnings[-1])
        self.assertIn('GRUB is installed instead', fake.log.warnings[-1])
        self.assertFalse(any('apt-get' in c for c in calls), calls)  # checked before anything is downloaded

    def test_32_bit_uefi_keeps_grub(self):
        with tempfile.TemporaryDirectory() as temp:
            module = load_module('corrybootloader', fake_calamares())
            with patch.object(Path, 'read_text', return_value='32\n'):
                self.assertEqual(module.efi_bits(), '32')
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            values = {'rootMountPoint': temp, 'firmwareType': 'efi', 'efiSystemPartition': '/boot/efi',
                      'partitions': self.partitions(fs='ext4'),
                      'corrySystem': {'bootloader': {'id': 'systemd-boot', 'name': 'systemd-boot',
                                                     'packages': ['systemd-boot']}}}
            calls = []
            fake = fake_calamares(values, {}, lambda args, *rest: calls.append(args) or 0)
            module = load_module('corrybootloader', fake)
            with patch.object(module, 'efi_bits', return_value='32'):
                self.assertIsNone(module.run())
            self.assert_falls_back(fake, calls, '32-bit UEFI')

    def test_unsuitable_layouts_keep_grub(self):
        encrypted = self.partitions(fs='ext4')
        encrypted[1]['luksMapperName'] = 'luks-root'
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'refind', partitions=encrypted)
            self.assert_falls_back(fake, calls, 'encrypted /boot')
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'refind', fs='xfs')
            self.assert_falls_back(fake, calls, 'cannot read a xfs /boot')
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'extlinux', firmware='bios', fs='btrfs')
            self.assert_falls_back(fake, calls, 'cannot read a btrfs /boot')
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(
                temp, 'extlinux', firmware='bios', fs='ext4',
                extra={'osproberLines': ['/dev/sda1:Windows 10:Windows:chain']})
            self.assert_falls_back(fake, calls, 'another operating system (Windows 10)')
        logical = self.partitions(efi=False, fs='ext4')
        logical[0]['device'] = '/dev/sda5'
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'extlinux', firmware='bios', partitions=logical)
            self.assert_falls_back(fake, calls, 'logical partition')
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(
                temp, 'extlinux', firmware='bios', fs='ext4',
                parted_listing='BYT;\n/dev/sda:100GB:scsi:512:512:msdos:Disk:;\n1:1MB:500MB:499MB:ntfs::boot;\n'
                               '2:500MB:90GB:89GB:ext4::;\n')
            self.assert_falls_back(fake, calls, 'partition 1 of /dev/sda is the active')

    def test_unexpected_error_restores_grub(self):
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            values = {'rootMountPoint': temp, 'firmwareType': 'efi', 'efiSystemPartition': '/boot/efi',
                      'partitions': self.partitions(fs='ext4'),
                      'corrySystem': {'bootloader': {'id': 'refind', 'name': 'rEFInd', 'packages': ['refind']}}}
            calls = []
            purged = set()

            def call(args, stdin='', timeout=0):
                calls.append(args)
                if 'purge' in args:
                    purged.update(args[args.index('purge') + 1:])
                    if 'grub-common' in args:
                        raise RuntimeError('unexpected')  # after GRUB's packages are gone
                return 0

            def output(args, *rest):
                if args[0] == 'dpkg-query':
                    return 'un ' if args[-1] in purged else 'ii '
                return 'amd64\n' if args[0] == 'dpkg' else ''
            fake = fake_calamares(values, {}, call, output)
            module = load_module('corrybootloader', fake)
            with patch.object(module, 'online', return_value=True), \
                    patch.object(module, 'host', return_value=types.SimpleNamespace(returncode=0, stdout='')):
                self.assertIsNone(module.run())
            self.assertEqual(fake.values['corrySystem']['bootloader']['id'], 'grub')
            self.assertIn('unexpected RuntimeError', fake.log.warnings[-1])
            restore = [c for c in calls if 'install' in c and 'grub-common' in c]
            self.assertTrue(restore, calls)

    def test_systemd_boot_with_kernel_install(self):
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'systemd-boot', kernel_install=True)
            adds = [c for c in calls if c[0] == 'kernel-install']
            self.assertEqual([c[2] for c in adds], ['6.12.0-1-amd64', '6.11.0-1-amd64'])
            self.assertEqual(adds[0][3:], ['/boot/vmlinuz-6.12.0-1-amd64', '/boot/initrd.img-6.12.0-1-amd64'])
            self.assertFalse((root / 'etc/kernel/postinst.d/zz-corry-systemd-boot').exists())
            self.assertEqual(fake.values['corrySystem']['bootloader']['id'], 'systemd-boot')

    def test_failed_alternative_keeps_grub_and_leaves_nothing_behind(self):
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'systemd-boot', bootctl_code=1)
            # The second bootctl attempt (--no-variables) succeeds in this scenario; make it fail too.
        with tempfile.TemporaryDirectory() as temp:
            root = self.make_root(temp)
            values = {'rootMountPoint': temp, 'firmwareType': 'efi', 'efiSystemPartition': '/boot/efi',
                      'partitions': self.partitions(), 'btrfsRootSubvolume': '@',
                      'corrySystem': {'bootloader': {'id': 'systemd-boot', 'name': 'systemd-boot', 'packages': ['systemd-boot']}}}
            calls = []

            def call(args, stdin='', timeout=0):
                calls.append(args)
                return 1 if args[0] == 'bootctl' else 0
            fake = fake_calamares(values, {}, call, lambda args, *rest: 'ii ' if args[0] == 'dpkg-query' else '')
            module = load_module('corrybootloader', fake)
            with patch.object(module, 'online', return_value=True), \
                    patch.object(module, 'host', return_value=types.SimpleNamespace(returncode=0, stdout='')):
                self.assertIsNone(module.run())
            self.assertIn('bootctl could not install systemd-boot', fake.log.warnings[0])
            self.assertIn('GRUB is installed instead', fake.log.warnings[0])
            self.assertEqual(fake.values['corrySystem']['bootloader']['id'], 'grub')
            purges = [c for c in calls if 'apt-get' in c and 'purge' in c]
            self.assertEqual(purges[0][-1], 'systemd-boot')  # the half-installed alternative, not GRUB
            self.assertTrue((root / 'boot/grub/grub.cfg').exists())
            self.assertTrue((root / 'boot/efi/EFI/debian/grubx64.efi').exists())

    def test_refind_is_copied_to_both_efi_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'refind', fs='ext4')
            self.assertEqual(fake.log.warnings, [])
            esp = root / 'boot/efi'
            for path in ['EFI/refind/refind_x64.efi', 'EFI/refind/refind.conf', 'EFI/refind/drivers_x64/ext4_x64.efi',
                         'EFI/refind/icons/os_linux.png', 'EFI/BOOT/BOOTX64.EFI', 'EFI/BOOT/refind.conf',
                         'EFI/BOOT/drivers_x64/ext4_x64.efi']:
                self.assertTrue((esp / path).exists(), path)
            self.assertFalse((esp / 'EFI/refind/drivers_x64/btrfs_x64.efi').exists())
            self.assertEqual((esp / 'EFI/BOOT/BOOTX64.EFI').read_text(), 'x')  # rEFInd, not GRUB's copy
            conf = (root / 'boot/refind_linux.conf').read_text().splitlines()
            self.assertEqual(conf[0], '"Boot with standard options"  "quiet root=UUID=root-uuid resume=UUID=swap-uuid rw"')
            self.assertIn('single', conf[1])
            self.assertEqual(conf[2], '"Boot with minimal options"   "ro root=UUID=root-uuid"')
            self.assertTrue(any(h[:2] == ['efibootmgr', '-c'] and 'rEFInd Boot Manager' in h for h in hosts))
            self.assertFalse((esp / 'EFI/debian').exists())
            preseed = [c for c in calls if c[0] == 'sh' and 'debconf-set-selections' in c[-1]]
            self.assertTrue(preseed)
            self.assertEqual(fake.values['corrySystem']['bootloader']['id'], 'refind')

    def test_extlinux_on_bios(self):
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'extlinux', firmware='bios', fs='ext4')
            self.assertEqual(fake.log.warnings, [])
            conf = (root / 'boot/extlinux/extlinux.conf').read_text()
            self.assertIn('LINUX /boot/vmlinuz-6.12.0-1-amd64', conf)
            self.assertIn('INITRD /boot/initrd.img-6.12.0-1-amd64', conf)
            self.assertIn('APPEND quiet root=UUID=root-uuid resume=UUID=swap-uuid rw', conf)
            self.assertLess(conf.index('6.12.0'), conf.index('6.11.0'))
            self.assertIn(['extlinux', '--install', '/boot/extlinux'], calls)
            dd = [h for h in hosts if h[0] == 'dd'][0]
            self.assertIn('of=/dev/sda', dd)
            self.assertTrue(dd[1].endswith('usr/lib/EXTLINUX/mbr.bin'))
            self.assertIn(['parted', '-s', '/dev/sda', 'set', '2', 'boot', 'on'], hosts)
            self.assertTrue(os.access(root / 'etc/kernel/postinst.d/zz-corry-extlinux', os.X_OK))
            self.assertFalse((root / 'boot/grub').exists())
            self.assertEqual(fake.values['corrySystem']['bootloader']['id'], 'extlinux')

    def test_extlinux_with_separate_boot_uses_relative_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'extlinux', firmware='bios', fs='btrfs', separate_boot=True)
            conf = (root / 'boot/extlinux/extlinux.conf').read_text()
            self.assertIn('LINUX /vmlinuz-6.12.0-1-amd64', conf)
            self.assertIn('rootflags=subvol=@', conf)
            self.assertIn(['parted', '-s', '/dev/sda', 'set', '4', 'boot', 'on'], hosts)

    def test_refind_minimal_entry_keeps_the_btrfs_subvolume(self):
        with tempfile.TemporaryDirectory() as temp:
            result, calls, hosts, fake, root = self.setup(temp, 'refind', fs='btrfs')
            conf = (root / 'boot/refind_linux.conf').read_text().splitlines()
            self.assertEqual(conf[2], '"Boot with minimal options"   "ro root=UUID=root-uuid rootflags=subvol=@"')

    def test_helpers(self):
        module = load_module('corrybootloader', fake_calamares())
        self.assertEqual(module.disk_of('/dev/sda3'), ('/dev/sda', 3))
        self.assertEqual(module.disk_of('/dev/nvme0n1p2'), ('/dev/nvme0n1', 2))
        self.assertEqual(module.disk_of('/dev/mmcblk0p1'), ('/dev/mmcblk0', 1))
        self.assertEqual(module.disk_of('/dev/vda'), (None, None))
        versions = ['6.1.0-25-amd64', '6.12.0-1-amd64', '6.9.7+bpo-amd64']
        self.assertEqual(sorted(versions, key=module.version_key), ['6.1.0-25-amd64', '6.9.7+bpo-amd64', '6.12.0-1-amd64'])

    def test_bios_install_gets_grub_in_the_mbr(self):
        # The partition module always sets efiSystemPartition, also on BIOS. The
        # bootloader module must still run grub-install --target=i386-pc for the
        # disk (found by the e2e test: a BIOS installation had no boot loader).
        calls = []
        values = {'firmwareType': 'bios', 'efiSystemPartition': '/boot/efi', 'rootMountPoint': '/tmp/target',
                  'bootLoader': {'installPath': '/dev/sda'},
                  'partitions': [{'device': '/dev/sda1', 'fs': 'ext4', 'mountPoint': '/', 'uuid': 'root-uuid'}],
                  'branding': {'bootloaderEntryName': 'Edukasaun'}}
        configuration = yaml.safe_load((PROFILE / 'modules/bootloader.conf').read_text())
        fake = fake_calamares(values, configuration, lambda args, *rest: calls.append(list(args)) or 0)
        module = load_module('bootloader', fake)
        module.check_target_env_call = lambda args, *rest: calls.append(list(args)) or 0
        with patch.object(module, 'run_grub_mkconfig', lambda *args: None):
            module.prepare_bootloader('bios', False)
        installs = [c for c in calls if c and c[0].endswith('grub-install')]
        self.assertEqual(len(installs), 1, calls)
        self.assertIn('--target=i386-pc', installs[0])
        self.assertEqual(installs[0][-1], '/dev/sda')
        self.assertFalse(any('Cannot install BIOS bootloader' in w for w in fake.log.warnings), fake.log.warnings)

    def test_grub_modules_step_aside_for_another_loader(self):
        for name in ['grubcfg', 'bootloader']:
            fake = fake_calamares({'corrySystem': {'bootloader': {'id': 'refind'}}, 'firmwareType': 'efi',
                                   'rootMountPoint': '/nowhere'})
            module = load_module(name, fake)
            self.assertIsNone(module.run(), name)
            self.assertEqual(fake.log.warnings, [], name)
            # With GRUB chosen (or after a fallback) the modules work as before.
            fake = fake_calamares({'corrySystem': {'bootloader': {'id': 'grub'}}, 'firmwareType': 'bios'})
            self.assertFalse(load_module(name, fake).corry_other_bootloader(), name)


class PreflightTests(unittest.TestCase):
    def preflight(self):
        spec = importlib.util.spec_from_file_location('preflight', ROOT / 'tools/preflight.py')
        preflight = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preflight)
        return preflight

    def test_exit_codes_are_distinct_and_documented(self):
        launcher = (ROOT / 'tools/corry-installer').read_text()
        self.assertIn('exit 2', launcher)   # preflight failed
        self.assertIn('exit 4', launcher)   # engine missing
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp)
            (config / 'modules').mkdir()
            (config / 'settings.conf').write_text('branding: corry\n')
            (config / 'modules/unpackfs.conf').write_text('unpack:\n- source: /missing/corry.squashfs\n')
            result = subprocess.run([sys.executable, str(ROOT / 'tools/preflight.py'), '--config', temp],
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Corry cannot start', result.stderr)
        development = (ROOT / 'docs/CORRY-DEVELOPMENT.md').read_text()
        for code in ['| 0 |', '| 1 |', '| 2 |', '| 4 |', '| 126, 127 |']:
            self.assertIn(code, development)

    def test_logs_are_kept_in_tmp_corry(self):
        # The launcher saves a failed preflight check; corry-session saves the log
        # of an engine that crashed. Both go to /tmp/Corry (here CORRY_LOG_DIR).
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            logs, stubs = temp / 'Corry', temp / 'stubs'
            stubs.mkdir()
            (stubs / 'preflight.py').write_text('import sys\nprint("Live system image not found", file=sys.stderr)\nsys.exit(2)\n')
            launcher = (ROOT / 'tools/corry-installer').read_text() \
                .replace('/usr/lib/corry/preflight.py', str(stubs / 'preflight.py')).replace('-x /usr/bin/calamares', '-x /bin/sh')
            result = subprocess.run(['bash', '-c', launcher, 'corry-installer'], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True, env={'PATH': '/usr/bin:/bin', 'CORRY_LOG_DIR': str(logs), 'HOME': temp})
            self.assertEqual(result.returncode, 2)
            self.assertIn('Live system image not found', (logs / 'preflight-error.log').read_text())

            session_log = temp / 'cache/calamares/session.log'
            session_log.parent.mkdir(parents=True)
            session_log.write_text('12:00:01 [6]: unpackfs ...\n12:00:02 [1]: something broke\n')
            # 87: a second start while Corry runs, not a crash.
            for code, crashed in [(0, False), (87, False), (139, True)]:
                (stubs / 'engine').write_text(f'#!/bin/sh\nexit {code}\n')
                (stubs / 'engine').chmod(0o755)
                session = (ROOT / 'tools/corry-session').read_text().replace('/usr/bin/calamares', str(stubs / 'engine'))
                result = subprocess.run(['sh', '-c', session, 'corry-session'], stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True,
                                        env={'PATH': '/usr/bin:/bin', 'CORRY_LOG_DIR': str(logs),
                                             'XDG_CACHE_HOME': str(temp / 'cache')})
                self.assertEqual(result.returncode, code)
                crashes = sorted(logs.glob('crash-*.log'))
                self.assertEqual(bool(crashes), crashed)
            text = crashes[0].read_text()
            self.assertIn('stopped unexpectedly (exit code 139)', text)
            self.assertIn('something broke', text)
            self.assertEqual(crashes[0].stat().st_mode & 0o777, 0o600)
            self.assertIn(str(crashes[0]), result.stderr)

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
            # A Debian live image without GRUB (as Debian ships them): fine when the
            # ISO's package pool or the internet can provide it, an error otherwise.
            bare = Path(temp) / 'bare'
            for relative in ['boot/vmlinuz-6.12.0-1-amd64', 'usr/sbin/update-initramfs']:
                (bare / relative).parent.mkdir(parents=True, exist_ok=True)
                (bare / relative).write_text('x')
            medium = Path(temp) / 'medium'
            bare_image = str(medium / 'live/filesystem.squashfs')
            (medium / 'live').mkdir(parents=True)
            subprocess.run(['mksquashfs', str(bare), bare_image, '-quiet', '-noappend'], check=True,
                           stdout=subprocess.DEVNULL)
            config = Path(temp) / 'config'
            (config / 'modules').mkdir(parents=True)
            (config / 'modules/corrygrub.conf').write_text(f'medium: {medium}\n')
            errors = preflight.boot_problems(bare_image, config, True, 'amd64', has_internet=False)
            self.assertEqual(len(errors), 1)
            self.assertIn('grub-efi-amd64', errors[0])
            self.assertIn('Connect to the internet', errors[0])
            self.assertEqual(preflight.boot_problems(bare_image, config, True, 'amd64', has_internet=True), [])
            (medium / 'dists/forky').mkdir(parents=True)
            (medium / 'dists/forky/Release').write_text('Suite: testing\n')
            (medium / 'pool/main/g/grub2').mkdir(parents=True)
            (medium / 'pool/main/g/grub2/grub-efi-amd64_2.12-9_amd64.deb').write_text('')
            self.assertEqual(preflight.boot_problems(bare_image, config, True, 'amd64', has_internet=False), [])
            # Still required in the image: a kernel and initramfs-tools.
            (bare / 'boot/vmlinuz-6.12.0-1-amd64').unlink()
            subprocess.run(['mksquashfs', str(bare), bare_image, '-quiet', '-noappend'], check=True,
                           stdout=subprocess.DEVNULL)
            errors = preflight.boot_problems(bare_image, config, True, 'amd64', has_internet=True)
            self.assertEqual(len(errors), 1)
            self.assertIn('Linux kernel', errors[0])


if __name__ == '__main__':
    unittest.main()
