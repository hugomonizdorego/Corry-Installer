# Configuration source snapshot

Source: https://github.com/CatalystDevOrg/calamares-settings-debian
Commit: `2b13f3458dd7ab8254ee0223c87467e18961e02c` (master, imported 2026-10-21).
License: ISC; see COPYING. The modules, settings and scripts here are an unmodified
source reference. They are NOT installed or executed by Corry.

The maintained fork is `config/corry`, with product overlays in `config/distros`.
Its prepare / install / finish sequence is derived from this source. Hardcoded
bookworm repositories, trusted=yes media hooks and mount-output parsing were
replaced with signed existing APT sources, target GlobalStorage paths and staged
downloads. Catalyst artwork is intentionally excluded.

Linux Mint Live Installer reference: https://github.com/linuxmint/live-installer
commit `e73310ffb6d180c552989cd40d9d1014457493f0`.
Corry reimplements its guided preference → disk → account → review flow and local
installation slideshow in Calamares/Qt. No Mint Python engine or artwork is copied.
The Mint repository has no root license notice in this snapshot, so it is used
as a behavioral reference rather than imported code.

This is an in-repository configuration fork, not a separate GitHub network fork.
