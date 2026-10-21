# SPDX-License-Identifier: GPL-3.0-or-later
"""Screenshot-only job: runs the real installation slideshow without touching any disk."""
import time
import libcalamares


def pretty_name():
    return "Unpacking the system image"


def run():
    for i in range(30):
        libcalamares.job.setprogress(i / 30)
        time.sleep(1)
    return None
