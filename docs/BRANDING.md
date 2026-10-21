<!-- SPDX-License-Identifier: CC0-1.0 -->
# Branding a distribution

Everything Corry shows for a distribution lives in one folder:

```
config/distros/<id>/
├── distro.yaml        names, colors, links, video, music, slides
├── slides/            slideshow images (SVG, PNG or JPEG photos)
└── media/             welcome video and background music (optional)
```

Nothing in the installation engine needs to change.

## Change an existing distribution

1. Edit `config/distros/edukasaun/distro.yaml` (or `debion`).
2. Replace images in `slides/` or files in `media/` if you like.
3. Check it: `python3 tools/corry-branding.py --check config/distros/edukasaun`
4. Install it into the ISO root: `sudo bash tools/install-profile.sh --distro edukasaun`

## Add a new distribution

```bash
python3 tools/new-distro.py mydistro "My Distro" --accent '#0b6bcb' --tint '#e8f1fb'
sudo bash tools/install-profile.sh --distro mydistro
```

This copies the DebION profile, renames it, and recolors the default slides, video
and music. A profile can also live outside the repository:
`install-profile.sh --distro-dir /path/to/profile`.

## distro.yaml fields

| Field | Meaning |
| --- | --- |
| `name`, `short-name` | Product name in the installer and the window title |
| `bootloader-name` | Name of the GRUB menu entry |
| `version` | Shown version; empty takes `VERSION_ID` from the live system's `/etc/os-release` |
| `colors.accent` | Buttons, progress, highlights (`#rrggbb`) |
| `colors.tint` | Soft backgrounds (`#rrggbb`) |
| `logo` | Square SVG/PNG logo; empty uses the Corry mark in the accent color |
| `links.website`, `links.support`, `links.known-issues`, `links.release-notes` | Welcome-page buttons; empty hides a button |
| `internet-check-url` | HTTP(S) address of the package mirror; used for the internet check and to decide whether to update packages |
| `welcome.image` | Poster and fallback image on the welcome page (in `slides/` or `media/`) |
| `welcome.video` | Muted, looping WebM/MP4 video on the welcome page; empty shows only the image |
| `sound.file` | Background music during installation (Ogg, MP3, WAV, FLAC, Opus); empty for silence |
| `sound.volume` | 0.0 to 1.0 (default 0.3) |
| `slides` | At least **5** entries, each with `image` (in `slides/`), `title` and `description` |

## Media sizes

| Media | Shown in the installer | Provide | Limits checked |
| --- | --- | --- | --- |
| Welcome video | Fixed 560×315 frame (16:9), muted, looping | 1280×720 WebM (VP9) or MP4, 5–15 s, no audio | 16:9, at least 960×540, 3–30 s, under 10 MB |
| Welcome image (poster) | Same 560×315 frame | 1600×900 PNG/JPEG, or SVG with a 16:9 viewBox | 16:9 |
| Slides | 16:9 card, about 600×338 | 1600×900 JPEG/PNG photos, or SVG with a 16:9 viewBox | 16:9, at least 1280×720 for photos, under 2 MB |
| Logo | 34×34 in the header | Square SVG (or PNG of at least 128×128) | — |
| Music | — | Ogg Vorbis, 30–90 s, made to loop, quiet | under 5 MB |

Images in another shape are letterboxed, not stretched. `corry-branding.py --check`
and `install-profile.sh` print a warning for every file outside these limits; they
only refuse a profile that is broken (missing files, fewer than five slides, wrong
colors). Use only media you have the rights to distribute.

`install-profile.sh` refuses a profile with fewer than five slides, missing files,
paths outside the folder or invalid colors, and tells you which field is wrong.

The default artwork, video and music were made by `tools/generate-default-media.py`
and are CC0-1.0. Re-run it after changing a profile's colors to recolor them.
