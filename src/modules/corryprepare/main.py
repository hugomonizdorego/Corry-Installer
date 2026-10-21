# SPDX-License-Identifier: GPL-3.0-or-later
import sys
sys.path.insert(0, '/usr/lib/corry')
import apt_support
import libcalamares


def pretty_name():
    return "Checking repositories and downloading additional software before partitioning"


def run():
    try:
        return apt_support.prepare(libcalamares)
    except (OSError, ValueError, RuntimeError) as exc:
        return ("Corry software preparation failed" if True else "Corry software installation failed", str(exc))
