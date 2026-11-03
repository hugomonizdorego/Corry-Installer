#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Create a new distribution profile for Corry from an existing one.

    python3 tools/new-distro.py mydistro "My Distro" --theme soft-blue --accent '#0b6bcb'

Copies config/distros/debion (or --from ID), sets the name, theme, Debian base
and colors in its distro.yaml and recolors the default slides. Then edit
config/distros/<id>/distro.yaml and replace any images with your own.
"""
import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('id', help='lowercase id, for example mydistro')
    parser.add_argument('name', help='product name, for example "My Distro"')
    parser.add_argument('--theme', default=None, help='a theme from config/themes (default: the copied one)')
    parser.add_argument('--debian', choices=['stable', 'testing'], default=None, help='the Debian base')
    parser.add_argument('--accent', default=None, help='override the theme accent, #rrggbb')
    parser.add_argument('--tint', default=None, help='override the theme tint, #rrggbb')
    parser.add_argument('--from', dest='source', default='debion')
    parser.add_argument('--no-media', action='store_true', help='keep the copied media instead of recoloring it')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', args.id):
        parser.error('id must be lowercase letters, digits and dashes')
    for color in (args.accent, args.tint):
        if color is not None and not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            parser.error('colors must look like #rrggbb')
    if args.theme and not (ROOT / 'config/themes' / f'{args.theme}.yaml').is_file():
        parser.error(f'no theme {args.theme} in config/themes')
    source, target = ROOT / 'config/distros' / args.source, ROOT / 'config/distros' / args.id
    if target.exists():
        parser.error(f'{target} already exists')
    shutil.copytree(source, target)
    text = (target / 'distro.yaml').read_text()
    old = re.search(r'^name: (.*)$', text, re.M).group(1)
    text = text.replace(old, args.name).replace(f'--distro {args.source}', f'--distro {args.id}')
    if args.theme:
        text = re.sub(r'^theme: .*$', f'theme: {args.theme}', text, flags=re.M)
    if args.debian:
        text = re.sub(r'^debian: .*$', f'debian: {args.debian}', text, flags=re.M)
    overrides = {k: v for k, v in (('accent', args.accent), ('tint', args.tint)) if v}
    if overrides:
        text = re.sub(r'^colors: .*$', 'colors:\n' + ''.join(f"  {k}: '{v}'\n" for k, v in overrides.items()).rstrip('\n'),
                      text, flags=re.M)
    (target / 'distro.yaml').write_text(text)
    if not args.no_media:
        subprocess.run([sys.executable, str(ROOT / 'tools/generate-default-media.py'), args.id], check=True)
    subprocess.run([sys.executable, str(ROOT / 'tools/corry-branding.py'), '--check', str(target)], check=True)
    print(f'Created {target}. Edit distro.yaml, then: sudo bash tools/install-profile.sh --distro {args.id}')


if __name__ == '__main__':
    main()
