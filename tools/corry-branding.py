#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Turn a distribution's distro.yaml into Corry's branding and module settings.

    corry-branding.py --check config/distros/edukasaun     # validate only
    corry-branding.py FOLDER CONFIG IMAGE VERSION          # used by install-profile.sh

Prints the product's short name on success.
"""
import json
import re
import shutil
import sys
from pathlib import Path, PurePosixPath
import yaml

MIN_SLIDES = 5
IMAGE = ('.svg', '.png', '.jpg', '.jpeg')
VIDEO = ('.webm', '.mp4', '.mkv', '.ogv')
SOUND = ('.ogg', '.oga', '.mp3', '.wav', '.flac', '.opus')
COLOR = re.compile(r'^#[0-9a-fA-F]{6}$')
# Placeholder colors in src/branding/corry, replaced by the distribution's.
ACCENT, TINT = '#6445a4', '#f0ecf8'
THEMED = ['stylesheet.qss', 'corry-mark.svg', 'calamares-sidebar.qml', 'show.qml', 'SlideControl.qml',
          'welcome-media.qml']


class BrandingError(ValueError):
    pass


def local_file(folder, value, kinds, what):
    path = PurePosixPath(value)
    if path.is_absolute() or '..' in path.parts:
        raise BrandingError(f'{what} must be a path inside the distribution folder: {value}')
    if path.suffix.lower() not in kinds:
        raise BrandingError(f'{what} must be one of {", ".join(kinds)}: {value}')
    if not (folder / path).is_file():
        raise BrandingError(f'{what} not found: {folder / path}')
    return str(path)


def load(folder):
    folder = Path(folder)
    try:
        data = yaml.safe_load((folder / 'distro.yaml').read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise BrandingError(f'Cannot read {folder / "distro.yaml"}: {exc}')
    if not isinstance(data, dict):
        raise BrandingError('distro.yaml must be a mapping')
    for key in ['name', 'colors', 'slides']:
        if not data.get(key):
            raise BrandingError(f'distro.yaml needs "{key}"')
    data.setdefault('short-name', data['name'])
    data.setdefault('bootloader-name', data['name'])
    for key in ['accent', 'tint']:
        if not COLOR.match(str(data['colors'].get(key, ''))):
            raise BrandingError(f'colors.{key} must be a #rrggbb color')
    slides = data['slides']
    if not isinstance(slides, list) or len(slides) < MIN_SLIDES:
        raise BrandingError(f'The installation slideshow needs at least {MIN_SLIDES} slides (found {len(slides)})')
    for slide in slides:
        if not slide.get('title'):
            raise BrandingError('Every slide needs a title')
        slide['image'] = local_file(folder / 'slides', slide.get('image', ''), IMAGE, 'Slide image')
        slide.setdefault('description', '')
    welcome = data.setdefault('welcome', {}) or {}
    data['welcome'] = welcome
    welcome['image'] = local_file(folder, welcome.get('image') or 'slides/' + slides[0]['image'], IMAGE, 'Welcome image')
    welcome['video'] = local_file(folder, welcome['video'], VIDEO, 'Welcome video') if welcome.get('video') else ''
    sound = data.setdefault('sound', {}) or {}
    data['sound'] = sound
    sound['file'] = local_file(folder, sound['file'], SOUND, 'Sound file') if sound.get('file') else ''
    # Only slides/ and media/ are copied into the installer.
    for what, value in [('welcome.image', welcome['image']), ('welcome.video', welcome['video']),
                        ('sound.file', sound['file'])]:
        if value and PurePosixPath(value).parts[0] not in ('slides', 'media'):
            raise BrandingError(f'{what} must be inside slides/ or media/: {value}')
    volume = float(sound.get('volume', 0.3))
    if not 0 <= volume <= 1:
        raise BrandingError('sound.volume must be between 0.0 and 1.0')
    sound['volume'] = volume
    data['logo'] = local_file(folder, data['logo'], IMAGE, 'Logo') if data.get('logo') else ''
    data.setdefault('links', {})
    data.setdefault('internet-check-url', 'http://deb.debian.org/debian/')
    if not re.match(r'^https?://', data['internet-check-url']):
        raise BrandingError('internet-check-url must start with http:// or https://')
    return data


def branding_desc(data):
    links = data['links'] or {}
    logo = 'logo' + Path(data['logo']).suffix if data['logo'] else 'corry-mark.svg'
    version = data.get('version') or '${VERSION_ID}'
    return {
        'componentName': 'corry',
        'welcomeStyleCalamares': False,
        'welcomeExpandingLogo': True,
        'windowExpanding': 'normal',
        'windowSize': '1120px,780px',
        'windowPlacement': 'center',
        'sidebar': 'qml,top',
        'navigation': 'widget',
        'strings': {
            'productName': data['name'],
            'shortProductName': data['short-name'],
            'version': version,
            'shortVersion': version,
            'versionedName': data['name'],
            'shortVersionedName': data['short-name'],
            'bootloaderEntryName': data['bootloader-name'],
            'productUrl': links.get('website') or '',
            'supportUrl': links.get('support') or '',
            'knownIssuesUrl': links.get('known-issues') or '',
            'releaseNotesUrl': links.get('release-notes') or '',
            'donateUrl': '',
        },
        'images': {'productIcon': logo, 'productLogo': logo, 'productWelcome': data['welcome']['image']},
        'style': {'SidebarBackground': '#ffffff', 'SidebarText': '#6b7280',
                  'SidebarTextCurrent': data['colors']['accent'], 'SidebarBackgroundCurrent': data['colors']['tint']},
        'slideshow': 'show.qml',
        'slideshowAPI': 2,
        'uploadServer': {'type': 'none'},
    }


def update_conf(path, change):
    data = yaml.safe_load(path.read_text())
    change(data)
    path.write_text('# Generated by tools/install-profile.sh from distro.yaml.\n---\n'
                    + yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def apply(folder, config, image, version):
    folder, config = Path(folder), Path(config)
    data = load(folder)
    brand = config / 'branding/corry'
    accent, tint = data['colors']['accent'], data['colors']['tint']
    for name in THEMED:
        path = brand / name
        path.write_text(path.read_text().replace(ACCENT, accent).replace(TINT, tint)
                        .replace('@CORRY_VERSION@', version))
    if data['logo']:
        shutil.copyfile(folder / data['logo'], brand / ('logo' + Path(data['logo']).suffix))
    (brand / 'branding.desc').write_text('# Generated by tools/install-profile.sh from distro.yaml.\n---\n'
                                         + yaml.safe_dump(branding_desc(data), sort_keys=False, allow_unicode=True))
    slides = [{k: s[k] for k in ['image', 'title', 'description']} for s in data['slides']]
    (brand / 'slides/Slides.js').write_text('// SPDX-License-Identifier: CC0-1.0\n// Generated from distro.yaml.\nvar slides = '
                                            + json.dumps(slides, ensure_ascii=False) + ';\n')
    media = {'poster': data['welcome']['image'], 'video': data['welcome']['video'],
             'sound': data['sound']['file'], 'volume': data['sound']['volume']}
    (brand / 'media.js').write_text('// SPDX-License-Identifier: CC0-1.0\n// Generated from distro.yaml.\nvar media = '
                                    + json.dumps(media) + ';\n')
    modules = config / 'modules'
    url = data['internet-check-url']
    (modules / 'unpackfs.conf').write_text(yaml.safe_dump(
        {'unpack': [{'source': image, 'sourcefs': 'squashfs', 'destination': ''}]}, sort_keys=False))
    # The boot medium is the directory that holds live/filesystem.squashfs.
    medium = str(PurePosixPath(image).parent.parent)
    update_conf(modules / 'corrygrub.conf', lambda d: d.update(medium=medium, checkUrl=url))
    update_conf(modules / 'corryupdate.conf', lambda d: d.update(checkUrl=url))
    for name in ['welcome.conf', 'welcomecheck.conf']:
        update_conf(modules / name, lambda d: d['requirements'].update(internetCheckUrl=url))
    (config / 'corry-distro').write_text(folder.name + '\n')
    return data['short-name']


def main(argv):
    try:
        if len(argv) == 2 and argv[0] == '--check':
            data = load(argv[1])
            print(f'{data["name"]}: OK ({len(data["slides"])} slides, video: {data["welcome"]["video"] or "none"}, '
                  f'sound: {data["sound"]["file"] or "none"})')
            return 0
        if len(argv) != 4:
            print(__doc__, file=sys.stderr)
            return 2
        print(apply(*argv))
        return 0
    except BrandingError as exc:
        print('Branding error: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
