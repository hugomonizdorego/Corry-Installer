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

Recommended media:

- Slides: 16:9, for example 1600×900 JPEG photos or SVG illustrations, under 1 MB each.
- Welcome video: 960×540 or 1280×720 WebM (VP9), 5–15 seconds, no audio track, under 5 MB.
- Music: Ogg Vorbis, 30–90 seconds, made to loop, under 2 MB. Use music you have the
  rights to distribute.

`install-profile.sh` refuses a profile with fewer than five slides, missing files,
paths outside the folder or invalid colors, and tells you which field is wrong.

The default artwork, video and music were made by `tools/generate-default-media.py`
and are CC0-1.0. Re-run it after changing a profile's colors to recolor them.
