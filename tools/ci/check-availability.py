#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Check Corry's init-system and boot-loader options against the Debian archive.

    check-availability.py stable|testing

Run on a Debian system of that base after "apt-get update". Every package of
every option offered on that base (availableOn) must exist in the archive;
otherwise the page would offer something that cannot be installed, and the
command fails. An option not offered on the base whose packages have since
appeared is reported, so the list can be widened.
"""
import subprocess
import sys
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[2]
PAGES = {'init': 'corrysystem-init.conf', 'bootloader': 'corrysystem-bootloader.conf'}


def available(package):
    result = subprocess.run(['apt-cache', 'show', '--no-all-versions', package], stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, text=True)
    return result.returncode == 0 and f'Package: {package}' in result.stdout


def main(argv):
    if len(argv) != 1 or argv[0] not in ('stable', 'testing'):
        print(__doc__, file=sys.stderr)
        return 2
    base = argv[0]
    failures = []
    for section, name in PAGES.items():
        page = yaml.safe_load((ROOT / 'config/corry/modules' / name).read_text())
        for option in page[section]:
            if option.get('default'):
                print(f'{section}: {option["id"]}: default, already in the live image')
                continue
            missing = [p for p in option['packages'] if not available(p)]
            offered = base in option.get('availableOn', [])
            if offered and missing:
                failures.append(f'{option["id"]} is offered on {base} but {", ".join(missing)} '
                                f'{"is" if len(missing) == 1 else "are"} not in the archive')
                print(f'{section}: {option["id"]}: MISSING {" ".join(missing)}')
            elif offered:
                print(f'{section}: {option["id"]}: offered, all packages available')
            elif missing:
                print(f'{section}: {option["id"]}: not offered on {base} (missing {" ".join(missing)})')
            else:
                print(f'{section}: {option["id"]}: not offered on {base}, but every package is now available: '
                      f'consider adding {base} to availableOn')
    for failure in failures:
        print('ERROR: ' + failure, file=sys.stderr)
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
