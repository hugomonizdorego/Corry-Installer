# SPDX-License-Identifier: GPL-3.0-or-later
"""Corry's isolated APT preparation and offline target installation.

APT never changes the live system. Downloads finish before the partition job.
Only signed sources from the installation image are used for preparation.
"""
import hashlib
import json
import os
import pwd
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import yaml

PACKAGE = re.compile(r'^[a-z0-9][a-z0-9+.-]*(?::[a-z0-9-]+)?$')


def sha256_file(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def run_command(args, *, env=None, timeout=1800):
    try:
        result = subprocess.run(args, env=env, stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT, text=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError('Repository operation timed out. Check the connection and retry before installing.') from exc
    if result.returncode:
        # Repository URLs may contain credentials. Do not put raw APT output in the UI/log.
        raise RuntimeError('Repository or package operation failed. Check internet, repository signatures, release, free space and package availability, then retry. No partition changes have started during preparation.')
    return result.stdout


def installed_packages(status):
    packages = set()
    for entry in status.split('\n\n'):
        fields = dict(line.split(': ', 1) for line in entry.splitlines() if ': ' in line and not line.startswith(' '))
        if fields.get('Status') == 'install ok installed' and fields.get('Package'):
            packages.add(fields['Package'])
            packages.add(fields['Package'] + ':' + fields.get('Architecture', 'all'))
    return packages


def selected_packages(catalog, selection):
    groups = {group['id']: group['packages'] for group in catalog['groups']}
    ids = [item for item in (selection or '').split(',') if item]
    if any(item not in groups for item in ids):
        raise ValueError('Unknown software selection. Return to Software and choose a listed group.')
    packages = list(dict.fromkeys(catalog.get('required', []) + [p for key in ids for p in groups[key]]))
    if any(not isinstance(p, str) or not PACKAGE.fullmatch(p) for p in packages):
        raise ValueError('The software catalog contains an invalid Debian package name.')
    return packages


def apt_environment(folder):
    """Disable live apt.conf hooks; retain signed sources and preferences in etc/apt."""
    folder = Path(folder)
    for name in ['lists/partial', 'archives/partial', 'state', 'cache', 'log']:
        (folder / name).mkdir(parents=True, exist_ok=True)
    config = folder / 'apt.conf'
    # JSON quoting also produces valid APT quoted strings, including spaces.
    q = lambda p: json.dumps(str(p))
    config.write_text('\n'.join([
        'Dir::Etc ' + q(folder / 'etc/apt') + ';',
        'Dir::Etc::parts "-";', 'Dir::Etc::main "-";',
        'Dir::State ' + q(folder / 'state') + ';',
        'Dir::Cache ' + q(folder / 'cache') + ';',
        'Dir::Log ' + q(folder / 'log') + ';',
        'Dir::State::status ' + q(folder / 'status') + ';',
        'Dir::State::lists ' + q(folder / 'lists') + ';',
        'Dir::Cache::archives ' + q(folder / 'archives') + ';',
        'Dir::Cache::pkgcache "";', 'Dir::Cache::srcpkgcache "";',
        'APT::Sandbox::User ' + q(pwd.getpwuid(os.geteuid()).pw_name) + ';',
        'Acquire::Retries "1";', 'Acquire::http::Timeout "15";',
        'Acquire::Source-Symlinks "false";',
        'Acquire::https::Timeout "15";', 'APT::Update::Error-Mode "any";',
        'APT::Get::AllowUnauthenticated "false";',
        'Acquire::AllowInsecureRepositories "false";',
        'Acquire::AllowDowngradeToInsecureRepositories "false";',
    ]) + '\n')
    env = os.environ.copy()
    env.update(APT_CONFIG=str(config), DEBIAN_FRONTEND='noninteractive', LC_ALL='C')
    return env


def require_signed_sources(folder):
    apt = Path(folder) / 'etc/apt'
    sources = ([apt / 'sources.list'] if (apt / 'sources.list').exists() else [])
    sources += sorted((apt / 'sources.list.d').glob('*.list')) + sorted((apt / 'sources.list.d').glob('*.sources'))
    if not sources:
        raise RuntimeError('No APT repositories are configured. Add signed repositories to the distribution image.')
    for source in sources:
        data = source.read_text()
        active = '\n'.join(line for line in data.splitlines() if not line.lstrip().startswith('#'))
        if re.search(r'(?i)trusted\s*=\s*(yes|true|1)|(?:^|\n)\s*Trusted:\s*(yes|true|1)|allow-insecure\s*=\s*(yes|true|1)|(?:^|\n)\s*Allow-Insecure:\s*(yes|true|1)', active):
            raise RuntimeError('An APT source bypasses signature verification. Configure a signed repository before selecting additional software.')
        # Use the exact key material from the image, not an unrelated live keyring.
        for prefix in ['/usr/share/keyrings/', '/etc/apt/keyrings/']:
            data = data.replace(prefix, str(Path(folder) / prefix.lstrip('/')))
        source.write_text(data)


def check_repositories():
    """Read-only live-session check shown on the Software page."""
    with tempfile.TemporaryDirectory(prefix='corry-repository-') as temp:
        folder = Path(temp)
        shutil.copytree('/etc/apt', folder / 'etc/apt')
        shutil.copytree('/usr/share/keyrings', folder / 'usr/share/keyrings')
        (folder / 'status').write_text('')
        require_signed_sources(folder)
        run_command(['apt-get', 'update'], env=apt_environment(folder), timeout=110)


def prepare(calamares):
    config = calamares.job.configuration
    catalog = yaml.safe_load(Path(config['catalog']).read_text())
    packages = selected_packages(catalog, calamares.globalstorage.value('packagechooser_packagechooser'))
    image = Path(config['image'])
    if not image.is_file():
        raise ValueError('The live system image is missing.')
    previous = calamares.globalstorage.value('corryPrepared')
    if previous:
        old = Path(previous)
        if old.name.startswith('corry-apt-') and old.parent == Path(tempfile.gettempdir()):
            shutil.rmtree(old, ignore_errors=True)
    folder = Path(tempfile.mkdtemp(prefix='corry-apt-'))
    try:
        status = run_command(['unsquashfs', '-cat', str(image), 'var/lib/dpkg/status'], timeout=120)
        installed = installed_packages(status)
        if not any(p.startswith('linux-image-') for p in installed):
            raise RuntimeError('The installation image has no installed Debian kernel. Rebuild the ISO with its kernel before installing.')
        (folder / 'status').write_text(status)
        missing = [p for p in packages if p not in installed]
        if missing:
            # Only extract APT configuration/key material; never execute image shell hooks.
            run_command(['unsquashfs', '-no-progress', '-d', str(folder / 'payload'), str(image),
                         'etc/apt', 'usr/share/keyrings'], timeout=120)
            shutil.move(str(folder / 'payload/etc'), folder / 'etc')
            shutil.move(str(folder / 'payload/usr'), folder / 'usr')
            require_signed_sources(folder)
            env = apt_environment(folder)
            run_command(['apt-get', 'update'], env=env, timeout=120)
            # Resolve against the IMAGE status, not the live session's installed packages.
            run_command(['apt-get', '--simulate', '--no-remove', 'install'] + missing, env=env)
            run_command(['apt-get', '-y', '--download-only', '--no-remove', 'install'] + missing, env=env)
        archives = {p.name: sha256_file(p) for p in (folder / 'archives').glob('*.deb')}
        if missing and not archives:
            raise RuntimeError('APT did not create a local package cache. No partition changes have started.')
        (folder / 'manifest.json').write_text(json.dumps({'packages':packages, 'installPackages':missing, 'install':bool(missing), 'archives':archives}))
        calamares.globalstorage.insert('corryPrepared', str(folder))
        return None
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise


def install(calamares):
    target = Path(calamares.globalstorage.value('rootMountPoint') or '/')
    if not target.is_absolute() or target.resolve() == Path('/'):
        raise ValueError('Refusing to install packages into the live root.')
    folder = Path(calamares.globalstorage.value('corryPrepared') or '/')
    if folder.parent != Path(tempfile.gettempdir()) or not folder.name.startswith('corry-apt-'):
        raise ValueError('Software was not prepared before partitioning.')
    manifest = json.loads((folder / 'manifest.json').read_text())
    if manifest['install']:
        for name, expected in manifest['archives'].items():
            if Path(name).name != name or sha256_file(folder / 'archives' / name) != expected:
                raise RuntimeError('A prepared package is missing or has changed. Installation stopped.')
        cache = target / 'var/lib/corry/install-cache'
        cache.mkdir(parents=True, exist_ok=True, mode=0o700)
        for name in ['archives', 'lists']:
            shutil.copytree(folder / name, cache / name, dirs_exist_ok=True)
        conf = cache / 'offline.conf'
        conf.write_text('Dir::Etc::parts "-";\nDir::Etc::main "-";\nDir::Cache::archives "/var/lib/corry/install-cache/archives";\nDir::State::lists "/var/lib/corry/install-cache/lists";\nDir::Cache::pkgcache "";\nDir::Cache::srcpkgcache "";\n')
        base = ['env', 'DEBIAN_FRONTEND=noninteractive', 'APT_CONFIG=/var/lib/corry/install-cache/offline.conf', 'apt-get']
        if calamares.utils.target_env_call(base + ['-y', '--no-download', '--no-remove', 'install'] + manifest['installPackages']):
            raise RuntimeError('APT could not install the prepared packages. See the installer log; no package failure was ignored.')
        if calamares.utils.target_env_call(base + ['check']):
            raise RuntimeError('The installed system has unresolved package dependencies.')
    installed = installed_packages((target / 'var/lib/dpkg/status').read_text())
    if any(p not in installed for p in manifest['packages']):
        raise RuntimeError('A requested package is not fully installed in the target system.')
    shutil.rmtree(target / 'var/lib/corry/install-cache', ignore_errors=True)
    shutil.rmtree(folder)
    return None
