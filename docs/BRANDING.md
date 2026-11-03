<!-- SPDX-License-Identifier: CC0-1.0 -->
# Branding a distribution

Everything Corry shows for a distribution lives in one folder:

```
config/distros/<id>/
├── distro.yaml        names, Debian base, theme, colors, links, music, slides
├── slides/            slideshow images (SVG, PNG or JPEG photos)
└── media/             background music (optional)
```

The look comes from a **theme** in `config/themes/`. Nothing in the installation
engine needs to change.

## Change an existing distribution

1. Edit `config/distros/edukasaun/distro.yaml` (or `debion`).
2. Replace images in `slides/` or the music in `media/` if you like.
3. Check it: `python3 tools/corry-branding.py --check config/distros/edukasaun`
4. Install it into the ISO root: `sudo bash tools/install-profile.sh --distro edukasaun`

## Add a new distribution

```bash
python3 tools/new-distro.py mydistro "My Distro" --debian stable --theme warm-pastel
python3 tools/new-distro.py mydistro "My Distro" --debian testing --theme soft-blue --accent '#0b6bcb'
sudo bash tools/install-profile.sh --distro mydistro
```

This copies the DebION profile, renames it, sets the base and theme, and redraws
the default slides in the theme's colors. A profile can also live outside the
repository: `install-profile.sh --distro-dir /path/to/profile`.

## distro.yaml fields

| Field | Meaning |
| --- | --- |
| `name`, `short-name` | Product name in the installer and the window title |
| `bootloader-name` | The GRUB menu entry (GRUB adds " GNU/Linux"). Its first word must be a plain ASCII word (letters, digits, `.` `_` `-`): lowercased, it is also GRUB's EFI directory (`EFI/debion`), as Debian's GRUB upgrades expect. `new-distro.py` sets it from the first word of the name |
| `version` | Shown version; empty takes `VERSION_ID` from the live system's `/etc/os-release` |
| `debian` | **Required.** The Debian base, `stable` or `testing`. The Init system and Boot loader pages offer only what this base's archive has |
| `theme` | `soft-blue` or `warm-pastel` (see below); default `soft-blue` |
| `colors` | Optional overrides of single theme colors, for example `{accent: '#0b6bcb'}`. A new `accent` without its own `accent-light`/`accent-dark` gets matching shades |
| `logo` | Square SVG/PNG logo; empty uses the Corry mark in the accent color |
| `links.website`, `links.support`, `links.known-issues`, `links.release-notes` | Welcome-page buttons; empty hides a button |
| `internet-check-url` | HTTP(S) address of the package mirror; used for the internet check and to decide whether to update, switch the init system or download a boot loader |
| `welcome.image` | The image on the welcome page (in `slides/` or `media/`); default: the first slide |
| `sound.file` | Background music during installation (Ogg, MP3, WAV, FLAC, Opus); empty for silence |
| `sound.volume` | 0.0 to 1.0 (default 0.3) |
| `slides` | At least **5** entries, each with `image` (in `slides/`), `title` and `description` |

Corry 1.0 shows images only. A `welcome.video` line from an older profile is
ignored with a note.

## Themes

| Theme | Used by | Layout | Look |
| --- | --- | --- | --- |
| `soft-blue` | DebION GNU/Linux | Header on top with the steps as a timeline; 1120×780 window | Soft-blue neumorphic UI: pale blue page, raised cards with a light upper edge and a soft lower shadow, blue gradient pill for the main action, font Inter |
| `warm-pastel` | Edukasaun OS | Rounded mint side menu of numbered steps and an "About" card; 1240×780 window | Warm cream page, salmon welcome card, coral pill buttons, mint/salmon/yellow/blue cards and step tiles, font Quicksand |

A theme file (`config/themes/<name>.yaml`) holds `layout` (`top` or `left`),
`font` (a list, first choice first), `radius` (card corners, in pixels) and these
colors (`#rrggbb`, `highlight` may be `transparent`):

| Colors | Used for |
| --- | --- |
| `page`, `surface`, `surface-alt`, `border` | Window background, cards, fields and panels, lines |
| `text`, `text-muted`, `text-faint` | Headings and body, secondary text, hints and disabled text |
| `accent`, `accent-light`, `accent-dark`, `on-accent`, `tint` | Main action gradient, hover/pressed shade, text on the accent, soft selection background |
| `shadow`, `highlight` | The card's soft shadow and, for neumorphic themes, its light upper edge |
| `nav`, `nav-text`, `nav-active`, `hero` | The header or side menu, its text, the current step, the welcome card |
| `tone-1` … `tone-4`, `mark-1` … `mark-4` | Pastel cards (summary, slides) and the step tiles, used in turn |
| `warning-bg`, `warning-text`, `danger-bg`, `danger-text`, `success` | Requirement rows and badges |

The branding sources (`src/branding/corry`: `stylesheet.qss`, the QML header or
side menu, slideshow and welcome card, the SVG mark, arrow and tick) contain
`@token@` placeholders: every color above plus `font`, `font-family` and
`radius`. `tools/corry-branding.py` fills them in when a profile is installed and
refuses unknown tokens; `tools/test-profile.py` checks that every theme defines
every token and that text has a contrast of at least 4.5:1 on its background.
`tools/preview.py --distro <id>` shows the result with sample data;
`tools/screenshots/capture.sh` captures the real build.

## Media sizes

| Media | Shown in the installer | Provide | Limits checked |
| --- | --- | --- | --- |
| Welcome image | Fixed 16:9 card: 560×315, or 480×270 next to a side menu | 1600×900 PNG/JPEG, or SVG with a 16:9 viewBox | 16:9 |
| Slides | 16:9 card, about 600×338 | 1600×900 JPEG/PNG photos, or SVG with a 16:9 viewBox | 16:9, at least 1280×720 for photos, under 2 MB |
| Logo | About 46×46 in the logo tile | Square SVG (or PNG of at least 128×128) | — |
| Music | — | Ogg Vorbis, 30–90 s, made to loop, quiet | under 5 MB |

Images in another shape are letterboxed, not stretched. `corry-branding.py --check`
and `install-profile.sh` print a warning for every file outside these limits; they
only refuse a profile that is broken (missing files, fewer than five slides, an
unknown theme, color or token, no Debian base). Use only media you have the rights
to distribute.

The default artwork and music were made by `tools/generate-default-media.py` and
are CC0-1.0. Re-run it (`--no-sound` keeps the music) after changing a profile's
theme to redraw the slides in its colors.
