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
| `bootloader-name` | Name of the boot menu entry |
| `version` | Shown version; empty takes `VERSION_ID` from the live system's `/etc/os-release` |
| `colors.accent` | Buttons, progress, highlights, the current step (`#rrggbb`) |
| `colors.tint` | Soft backgrounds behind selected items (`#rrggbb`) |
| `colors.accent-light`, `colors.accent-dark` | Optional. The light end of the gradients and the pressed/hover shade. Derived from `accent` when absent |
| `logo` | Square SVG/PNG logo; empty uses the Corry mark in the accent color |
| `links.website`, `links.support`, `links.known-issues`, `links.release-notes` | Welcome-page buttons; empty hides a button |
| `internet-check-url` | HTTP(S) address of the package mirror; used for the internet check and to decide whether to update, switch the init system or download a boot loader |
| `welcome.image` | Poster and fallback image on the welcome page (in `slides/` or `media/`) |
| `welcome.video` | Muted, looping WebM/MP4 video on the welcome page; empty shows only the image |
| `sound.file` | Background music during installation (Ogg, MP3, WAV, FLAC, Opus); empty for silence |
| `sound.volume` | 0.0 to 1.0 (default 0.3) |
| `slides` | At least **5** entries, each with `image` (in `slides/`), `title` and `description` |

## The look

Corry's pages share one design, defined in `src/branding/corry/stylesheet.qss` and
the QML header, slideshow and welcome media:

| Element | Value |
| --- | --- |
| Page background | `#edf3fb`, a light blue |
| Page card | White, 22 px corners, soft shadow painted by `Calamares::CorryCard` (no images) |
| Panels inside a card | `#f5f8fd`, 16 px corners |
| Text | `#1f2a44` (headings), `#64748b` (secondary), `#94a3b8` (muted) |
| Main action (Next, Install) | Gradient from `accent` to `accent-light`, white text, pill |
| Other buttons | White pills with a light border; hover shows the tint and the accent |
| Fields | `#f5f8fd`, 12 px corners; focus: 2 px accent border on white |
| Header | Logo tile, product name, "Step x of y", timeline of steps; the current step is a gradient pill |

The four placeholder colors in the branding sources (`#6445a4` accent, `#8a6fd0`
light accent, `#4e3585` dark accent, `#f0ecf8` tint) are replaced per distribution
by `tools/install-profile.sh`; `tools/preview.py` shows the result with sample data.

## Media sizes

| Media | Shown in the installer | Provide | Limits checked |
| --- | --- | --- | --- |
| Welcome video | Fixed 560×315 frame (16:9), muted, looping | 1280×720 WebM (VP9) or MP4, 5–15 s, no audio | 16:9, at least 960×540, 3–30 s, under 10 MB |
| Welcome image (poster) | Same 560×315 frame | 1600×900 PNG/JPEG, or SVG with a 16:9 viewBox | 16:9 |
| Slides | 16:9 card, about 600×338 | 1600×900 JPEG/PNG photos, or SVG with a 16:9 viewBox | 16:9, at least 1280×720 for photos, under 2 MB |
| Logo | 30×30 in the header tile | Square SVG (or PNG of at least 128×128) | — |
| Music | — | Ogg Vorbis, 30–90 s, made to loop, quiet | under 5 MB |

Images in another shape are letterboxed, not stretched. `corry-branding.py --check`
and `install-profile.sh` print a warning for every file outside these limits; they
only refuse a profile that is broken (missing files, fewer than five slides, wrong
colors). Use only media you have the rights to distribute.

The default artwork, video and music were made by `tools/generate-default-media.py`
and are CC0-1.0. Re-run it after changing a profile's colors to recolor them.
