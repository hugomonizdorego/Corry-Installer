# SPDX-License-Identifier: GPL-3.0-or-later
import sys
sys.path.insert(0, '/usr/lib/corry')
import apt_support
import libcalamares


def pretty_name():
    return "Installing additional software from the verified local cache"


def run():
    try:
        return apt_support.install(libcalamares)
    except (OSError, ValueError, RuntimeError) as exc:
        return ("Corry software preparation failed" if False else "Corry software installation failed", str(exc))
