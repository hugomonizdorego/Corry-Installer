#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Turn a distribution's distro.yaml into Corry's branding and module settings.

    corry-branding.py --check config/distros/edukasaun     # validate only
    corry-branding.py FOLDER CONFIG IMAGE VERSION          # used by install-profile.sh

Prints the product's short name on success.

A distribution picks a theme from config/themes/ ("theme:" in distro.yaml)
and may override any of its colors ("colors:"). Every @name@ token in the
branding sources (stylesheet, QML, logo) is replaced by the theme's value.
"""
import colorsys
import json
import re
import shutil
import sys
from pathlib import Path, PurePosixPath
import yaml

ROOT = Path(__file__).resolve().parents[1]
THEMES = ROOT / 'config/themes'
DEFAULT_THEME = 'soft-blue'
MIN_SLIDES = 5
IMAGE = ('.svg', '.png', '.jpg', '.jpeg')
SOUND = ('.ogg', '.oga', '.mp3', '.wav', '.flac', '.opus')
COLOR = re.compile(r'^#[0-9a-fA-F]{6}$')
TOKEN = re.compile(r'@([a-z][a-z0-9-]*)@')
BASES = ('stable', 'testing')
LAYOUTS = ('top', 'left')
# Colors every theme defines (tools/test-profile.py checks the theme files).
THEME_COLORS = ('page', 'surface', 'surface-alt', 'border', 'text', 'text-muted', 'text-faint', 'accent',
                'accent-light', 'accent-dark', 'on-accent', 'tint', 'shadow', 'highlight', 'nav', 'nav-text',
                'nav-active', 'hero', 'tone-1', 'tone-2', 'tone-3', 'tone-4', 'mark-1', 'mark-2', 'mark-3', 'mark-4',
                'warning-bg', 'warning-text', 'danger-bg', 'danger-text', 'success')
# Branding sources with theme tokens. The header is chosen by the theme's layout
# and installed as calamares-sidebar.qml.
THEMED = ['stylesheet.qss', 'corry-mark.svg', 'combo-arrow.svg', 'show.qml', 'SlideControl.qml', 'welcome-media.qml']
HEADERS = {'top': 'sidebar-top.qml', 'left': 'sidebar-left.qml'}
# The side menu takes about 250px, so that layout gets a wider window (both
# shrink to fit smaller screens; pages then scroll instead of being cut).
WINDOW_SIZES = {'top': '1120px,780px', 'left': '1240px,780px'}

# Display sizes in the 1120x780 window, and what to provide for sharp results.
# Slides: shown in a 16:9 card of about 600x338; provide 1600x900 (minimum 1280x720).
# Welcome image: shown at 560x315 (16:9); provide 1600x900 or an SVG.
SLIDE_SIZE = (1600, 900)
MIN_RASTER = (1280, 720)
MAX_BYTES = {'slide': 2_000_000, 'sound': 5_000_000}


class BrandingError(ValueError):
    pass


def shade(color, lightness, saturation=1.0):
    """The same hue as #rrggbb @color with its lightness multiplied by @lightness."""
    r, g, b = (int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    h, l, s = colorsys.rgb_to_hls(r, g, b)
    l = min(0.92, max(0.08, l * lightness))
    s = min(1.0, s * saturation)
    return '#' + ''.join(f'{round(c * 255):02x}' for c in colorsys.hls_to_rgb(h, l, s))


def valid_color(value):
    return value == 'transparent' or bool(COLOR.match(str(value)))


def load_theme(name):
    path = THEMES / f'{name}.yaml'
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', str(name)) or not path.is_file():
        available = ', '.join(sorted(p.stem for p in THEMES.glob('*.yaml')))
        raise BrandingError(f'Unknown theme "{name}"; available: {available}')
    theme = yaml.safe_load(path.read_text())
    if theme.get('layout') not in LAYOUTS:
        raise BrandingError(f'Theme {name}: layout must be one of {", ".join(LAYOUTS)}')
    missing = [key for key in THEME_COLORS if key not in theme.get('colors', {})]
    if missing:
        raise BrandingError(f'Theme {name} lacks colors: {", ".join(missing)}')
    for key, value in theme['colors'].items():
        if not valid_color(value):
            raise BrandingError(f'Theme {name}: color {key} must be #rrggbb or transparent')
    return theme


def tokens(data):
    """Every @token@ value for the branding sources."""
    theme = data['theme-data']
    fonts = theme.get('font') or ['Noto Sans']
    values = dict(data['colors'])
    values.update({'font': ', '.join(f'"{f}"' for f in fonts) + ', sans-serif', 'font-family': fonts[0],
                   'radius': str(int(theme.get('radius', 22)))})
    return values


def image_size(path):
    """(width, height) of a PNG, JPEG or SVG file, or None if unknown."""
    data = Path(path).read_bytes()
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return int.from_bytes(data[16:20], 'big'), int.from_bytes(data[20:24], 'big')
    if data[:2] == b'\xff\xd8':
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker, length = data[i + 1], int.from_bytes(data[i + 2:i + 4], 'big')
            if marker in (0xC0, 0xC1, 0xC2):
                return int.from_bytes(data[i + 7:i + 9], 'big'), int.from_bytes(data[i + 5:i + 7], 'big')
            i += 2 + length
        return None
    match = re.search(rb'viewBox="\s*[-\d.]+[ ,]+[-\d.]+[ ,]+([\d.]+)[ ,]+([\d.]+)', data[:2000])
    return (float(match.group(1)), float(match.group(2))) if match else None


def media_warnings(folder, data):
    """Advice about sizes, aspect ratios and retired fields; never blocks an installation."""
    folder = Path(folder)
    warnings = list(data.get('notes', []))

    def aspect(size, what):
        if size and abs(size[0] / size[1] - 16 / 9) > 0.03:
            warnings.append(f'{what} is {size[0]:g}x{size[1]:g}, not 16:9; it will be letterboxed.')

    for slide in data['slides']:
        path = folder / 'slides' / slide['image']
        size = image_size(path)
        aspect(size, 'Slide ' + slide['image'])
        if size and path.suffix.lower() != '.svg' and (size[0] < MIN_RASTER[0] or size[1] < MIN_RASTER[1]):
            warnings.append(f'Slide {slide["image"]} is {size[0]}x{size[1]}; use at least '
                            f'{MIN_RASTER[0]}x{MIN_RASTER[1]} (recommended {SLIDE_SIZE[0]}x{SLIDE_SIZE[1]}).')
        if path.stat().st_size > MAX_BYTES['slide']:
            warnings.append(f'Slide {slide["image"]} is larger than 2 MB.')
    aspect(image_size(folder / data['welcome']['image']), 'Welcome image')
    if data['sound']['file'] and (folder / data['sound']['file']).stat().st_size > MAX_BYTES['sound']:
        warnings.append('The background music is larger than 5 MB.')
    return warnings


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
    for key in ['name', 'slides']:
        if not data.get(key):
            raise BrandingError(f'distro.yaml needs "{key}"')
    notes = data.setdefault('notes', [])
    data.setdefault('short-name', data['name'])
    data.setdefault('bootloader-name', data['name'])
    if data.get('debian') not in BASES:
        raise BrandingError(f'distro.yaml needs "debian: stable" or "debian: testing" (the Debian base); '
                            f'found {data.get("debian")!r}')
    # Theme, then the distribution's own color overrides.
    data['theme'] = data.get('theme') or DEFAULT_THEME
    theme = load_theme(data['theme'])
    data['theme-data'] = theme
    overrides = data.get('colors') or {}
    if not isinstance(overrides, dict):
        raise BrandingError('colors must be a mapping of color names to #rrggbb')
    for key, value in overrides.items():
        if key not in THEME_COLORS:
            raise BrandingError(f'colors.{key} is not a theme color; known: {", ".join(THEME_COLORS)}')
        if not valid_color(value):
            raise BrandingError(f'colors.{key} must be a #rrggbb color')
    colors = dict(theme['colors'])
    colors.update(overrides)
    # A new accent without its own shades gets matching ones.
    if 'accent' in overrides:
        if 'accent-light' not in overrides:
            colors['accent-light'] = shade(colors['accent'], 1.45, 1.1)
        if 'accent-dark' not in overrides:
            colors['accent-dark'] = shade(colors['accent'], 0.72)
    data['colors'] = colors
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
    if welcome.pop('video', None):
        notes.append('welcome.video is no longer used: Corry 1.0 shows the welcome image only. Remove the line.')
    welcome['image'] = local_file(folder, welcome.get('image') or 'slides/' + slides[0]['image'], IMAGE, 'Welcome image')
    sound = data.setdefault('sound', {}) or {}
    data['sound'] = sound
    sound['file'] = local_file(folder, sound['file'], SOUND, 'Sound file') if sound.get('file') else ''
    # Only slides/ and media/ are copied into the installer.
    for what, value in [('welcome.image', welcome['image']), ('sound.file', sound['file'])]:
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
    colors = data['colors']
    return {
        'componentName': 'corry',
        'welcomeStyleCalamares': False,
        'welcomeExpandingLogo': True,
        'windowExpanding': 'normal',
        'windowSize': WINDOW_SIZES[data['theme-data']['layout']],
        'windowPlacement': 'center',
        'sidebar': 'qml,' + data['theme-data']['layout'],
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
        'style': {'SidebarBackground': colors['nav'], 'SidebarText': colors['nav-text'],
                  'SidebarTextCurrent': colors['accent'], 'SidebarBackgroundCurrent': colors['tint']},
        'slideshow': 'show.qml',
        'slideshowAPI': 2,
        'uploadServer': {'type': 'none'},
    }


def efi_directory(bootloader_name):
    """The EFI/<id> directory for GRUB: the lowercased first word of the boot menu
    name (GRUB_DISTRIBUTOR), as Debian's grub-install and grub-efi-* postinst
    derive it, so package upgrades refresh the copy Corry installed."""
    words = str(bootloader_name).split()
    first = words[0].lower() if words else 'debian'
    first = {'kubuntu': 'ubuntu', 'devuan': 'debian'}.get(first, first)
    return re.sub(r'[^a-z0-9._-]', '', first) or 'debian'


def update_conf(path, change):
    data = yaml.safe_load(path.read_text())
    change(data)
    path.write_text('# Generated by tools/install-profile.sh from distro.yaml.\n---\n'
                    + yaml.safe_dump(data, sort_keys=False, allow_unicode=True))


def themed_text(text, values, what):
    """@text with every theme token replaced; unknown tokens are an error."""
    def replace(match):
        name = match.group(1)
        if name == 'CORRY_VERSION':
            return match.group(0)
        if name not in values:
            raise BrandingError(f'{what}: unknown theme token @{name}@')
        return values[name]
    return TOKEN.sub(replace, text)


def apply(folder, config, image, version):
    folder, config = Path(folder), Path(config)
    data = load(folder)
    brand = config / 'branding/corry'
    values = tokens(data)
    layout = data['theme-data']['layout']
    header = brand / HEADERS[layout]
    shutil.copyfile(header, brand / 'calamares-sidebar.qml')
    for source in HEADERS.values():
        (brand / source).unlink(missing_ok=True)
    for name in THEMED + ['calamares-sidebar.qml']:
        path = brand / name
        text = themed_text(path.read_text(), values, name).replace('@CORRY_VERSION@', version)
        path.write_text(text)
    if data['logo']:
        shutil.copyfile(folder / data['logo'], brand / ('logo' + Path(data['logo']).suffix))
    (brand / 'branding.desc').write_text('# Generated by tools/install-profile.sh from distro.yaml.\n---\n'
                                         + yaml.safe_dump(branding_desc(data), sort_keys=False, allow_unicode=True))
    slides = [{k: s[k] for k in ['image', 'title', 'description']} for s in data['slides']]
    (brand / 'slides/Slides.js').write_text('// SPDX-License-Identifier: CC0-1.0\n// Generated from distro.yaml.\nvar slides = '
                                            + json.dumps(slides, ensure_ascii=False) + ';\n')
    media = {'poster': data['welcome']['image'], 'sound': data['sound']['file'], 'volume': data['sound']['volume']}
    (brand / 'media.js').write_text('// SPDX-License-Identifier: CC0-1.0\n// Generated from distro.yaml.\nvar media = '
                                    + json.dumps(media) + ';\n')
    modules = config / 'modules'
    url = data['internet-check-url']
    (modules / 'unpackfs.conf').write_text(yaml.safe_dump(
        {'unpack': [{'source': image, 'sourcefs': 'squashfs', 'destination': ''}]}, sort_keys=False))
    # The boot medium is the directory that holds live/filesystem.squashfs.
    medium = str(PurePosixPath(image).parent.parent)
    update_conf(modules / 'corrygrub.conf', lambda d: d.update(medium=medium, checkUrl=url))
    for name in ['corryupdate.conf', 'corryinit.conf', 'corrybootloader.conf']:
        update_conf(modules / name, lambda d: d.update(checkUrl=url))
    efi = efi_directory(data['bootloader-name'])
    update_conf(modules / 'bootloader.conf', lambda d: d.update(efiBootloaderId=efi))
    update_conf(modules / 'corrybootloader.conf', lambda d: d.update(grubEfiDirectory=efi))
    # The init system and boot loader pages offer only what the base's archive has.
    for name in ['corrysystem-init.conf', 'corrysystem-bootloader.conf']:
        update_conf(modules / name, lambda d: d.update(base=data['debian']))
    for name in ['welcome.conf', 'welcomecheck.conf']:
        update_conf(modules / name, lambda d: d['requirements'].update(internetCheckUrl=url))
    (config / 'corry-distro').write_text(folder.name + '\n')
    return data['short-name']


def main(argv):
    try:
        if len(argv) == 2 and argv[0] == '--check':
            data = load(argv[1])
            for warning in media_warnings(argv[1], data):
                print('Warning: ' + warning, file=sys.stderr)
            print(f'{data["name"]}: OK (Debian {data["debian"]}, theme {data["theme"]}, {len(data["slides"])} slides, '
                  f'sound: {data["sound"]["file"] or "none"})')
            return 0
        if len(argv) != 4:
            print(__doc__, file=sys.stderr)
            return 2
        for warning in media_warnings(argv[0], load(argv[0])):
            print('Branding warning: ' + warning, file=sys.stderr)
        print(apply(*argv))
        return 0
    except BrandingError as exc:
        print('Branding error: ' + str(exc), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
