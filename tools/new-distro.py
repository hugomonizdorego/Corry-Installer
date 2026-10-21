#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Create a new distribution profile for Corry from an existing one.

    python3 tools/new-distro.py mydistro "My Distro" --accent '#0b6bcb' --tint '#e8f1fb'

Copies config/distros/debion (or --from ID), sets the name and colors in its
distro.yaml and recolors the default slides, video and music. Then edit
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
    parser.add_argument('--accent', default='#0b6bcb')
    parser.add_argument('--tint', default='#e8f1fb')
    parser.add_argument('--from', dest='source', default='debion')
    parser.add_argument('--no-media', action='store_true', help='keep the copied media instead of recoloring it')
    args = parser.parse_args()
    if not re.fullmatch(r'[a-z0-9][a-z0-9-]*', args.id):
        parser.error('id must be lowercase letters, digits and dashes')
    for color in (args.accent, args.tint):
        if not re.fullmatch(r'#[0-9a-fA-F]{6}', color):
            parser.error('colors must look like #rrggbb')
    source, target = ROOT / 'config/distros' / args.source, ROOT / 'config/distros' / args.id
    if target.exists():
        parser.error(f'{target} already exists')
    shutil.copytree(source, target)
    text = (target / 'distro.yaml').read_text()
    old = re.search(r'^name: (.*)$', text, re.M).group(1)
    text = text.replace(old, args.name).replace(f'--distro {args.source}', f'--distro {args.id}')
    text = re.sub(r"accent: '#[0-9a-fA-F]{6}'", f"accent: '{args.accent}'", text)
    text = re.sub(r"tint: '#[0-9a-fA-F]{6}'", f"tint: '{args.tint}'", text)
    (target / 'distro.yaml').write_text(text)
    if not args.no_media:
        subprocess.run([sys.executable, str(ROOT / 'tools/generate-default-media.py'), args.id], check=True)
    subprocess.run([sys.executable, str(ROOT / 'tools/corry-branding.py'), '--check', str(target)], check=True)
    print(f'Created {target}. Edit distro.yaml, then: sudo bash tools/install-profile.sh --distro {args.id}')


if __name__ == '__main__':
    main()
