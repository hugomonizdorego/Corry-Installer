#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Generate Corry's default CC0 media for one distribution.

Writes slide illustrations (SVG), a short looping welcome video (WebM/VP9)
and a calm background soundtrack (Ogg Vorbis) into config/distros/<id>/.
Distributions can replace any of these with their own photos, video or music;
see docs/BRANDING.md. Requires PySide6 and ffmpeg.

    python3 tools/generate-default-media.py edukasaun
"""
import argparse
import math
import random
import struct
import subprocess
import sys
import tempfile
import wave
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parents[1]
HEAD = '<!-- SPDX-License-Identifier: CC0-1.0; original Corry illustration -->\n'


def frame(a, t, body, shift=0.0):
    dx, dy = 30 * math.sin(shift), 20 * math.cos(shift)
    return (HEAD + '<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450" viewBox="0 0 800 450">'
            f'<defs><linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{t}"/>'
            '<stop offset="1" stop-color="#ffffff"/></linearGradient></defs>'
            '<rect width="800" height="450" rx="32" fill="url(#bg)"/>'
            f'<circle cx="{96 + dx:.1f}" cy="{88 + dy:.1f}" r="150" fill="{a}" opacity=".06"/>'
            f'<circle cx="{720 - dx:.1f}" cy="{400 - dy:.1f}" r="190" fill="{a}" opacity=".07"/>'
            + body + '</svg>\n')


def check(x, y, size, color, width):
    s = size / 36
    return (f'<path d="M{x - 14 * s:.1f} {y:.1f}l{10 * s:.1f} {10 * s:.1f} {20 * s:.1f} {-22 * s:.1f}" fill="none" '
            f'stroke="{color}" stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round"/>')


def welcome(a, t, phase=0.0):
    pulse = 1 + 0.04 * math.sin(phase * 2)
    size = 72 * pulse
    return frame(a, t,
        f'<path d="M0 360 C180 {300 + 10 * math.sin(phase):.1f} 300 330 420 360 S660 400 800 330 V450 H0Z" fill="{a}" opacity=".12"/>'
        f'<rect x="230" y="92" width="340" height="220" rx="22" fill="#ffffff" stroke="{a}" stroke-width="6"/>'
        f'<rect x="250" y="112" width="300" height="164" rx="12" fill="{t}"/>'
        f'<rect x="355" y="312" width="90" height="28" fill="{a}" opacity=".35"/>'
        f'<rect x="320" y="336" width="160" height="14" rx="7" fill="{a}" opacity=".55"/>'
        f'<rect x="{400 - size / 2:.1f}" y="{194 - size / 2:.1f}" width="{size:.1f}" height="{size:.1f}" rx="{20 * pulse:.1f}" fill="{a}"/>'
        f'<path d="M418 178a24 24 0 1 0 1 32" fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round"/>'
        f'<path d="M398 192l7 7 18-19" fill="none" stroke="#fff" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" opacity=".8"/>'
        f'<circle cx="{640 + 12 * math.sin(phase):.1f}" cy="120" r="30" fill="{a}" opacity=".25"/>'
        f'<circle cx="160" cy="{250 + 10 * math.cos(phase):.1f}" r="16" fill="{a}" opacity=".3"/>', phase)


def debian(a, t):
    return frame(a, t,
        f'<circle cx="400" cy="210" r="118" fill="#ffffff" stroke="{a}" stroke-width="6"/>'
        f'<path d="M430 150a62 62 0 1 0 22 92" fill="none" stroke="{a}" stroke-width="16" stroke-linecap="round"/>'
        f'<path d="M418 182a26 26 0 1 0 6 40" fill="none" stroke="{a}" stroke-width="10" stroke-linecap="round" opacity=".55"/>'
        + ''.join(f'<rect x="{x}" y="{360 - h}" width="56" height="{h}" rx="10" fill="{a}" opacity="{o}"/>'
                  for x, h, o in [(170, 60, .2), (240, 90, .3), (500, 90, .3), (570, 60, .2)]))


def learn(a, t):
    return frame(a, t,
        f'<path d="M400 140 C340 110 260 104 190 118 V330 C260 316 340 322 400 352Z" fill="#ffffff" stroke="{a}" stroke-width="6" stroke-linejoin="round"/>'
        f'<path d="M400 140 C460 110 540 104 610 118 V330 C540 316 460 322 400 352Z" fill="#ffffff" stroke="{a}" stroke-width="6" stroke-linejoin="round"/>'
        + ''.join(f'<path d="M{x1} {y} C{x1 + 40} {y - 8} {x1 + 90} {y - 8} {x1 + 130} {y}" fill="none" stroke="{a}" stroke-width="5" stroke-linecap="round" opacity=".35"/>'
                  for x1 in (230, 440) for y in (172, 208, 244, 280))
        + f'<circle cx="400" cy="78" r="34" fill="{a}"/>' + check(404, 78, 36, '#fff', 6))


def update(a, t):
    return frame(a, t,
        f'<path d="M260 270a70 70 0 0 1 20-138 92 92 0 0 1 172-18 76 76 0 0 1 96 76 64 64 0 0 1-12 80Z" fill="#ffffff" stroke="{a}" stroke-width="6" stroke-linejoin="round"/>'
        f'<path d="M400 170v130M352 256l48 48 48-48" fill="none" stroke="{a}" stroke-width="16" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<rect x="250" y="360" width="300" height="14" rx="7" fill="{a}" opacity=".15"/>'
        f'<rect x="250" y="360" width="200" height="14" rx="7" fill="{a}" opacity=".7"/>')


def shield(a, t):
    return frame(a, t,
        f'<path d="M400 70 L540 120 V220 C540 300 480 350 400 380 C320 350 260 300 260 220 V120Z" fill="#ffffff" stroke="{a}" stroke-width="6" stroke-linejoin="round"/>'
        f'<path d="M400 100 L512 140 V220 C512 284 466 324 400 350Z" fill="{a}" opacity=".12"/>'
        + check(405, 225, 80, a, 16)
        + f'<rect x="590" y="250" width="110" height="80" rx="12" fill="#ffffff" stroke="{a}" stroke-width="5"/>'
        f'<rect x="606" y="268" width="78" height="10" rx="5" fill="{a}" opacity=".35"/>'
        f'<rect x="606" y="290" width="54" height="10" rx="5" fill="{a}" opacity=".35"/>')


def community(a, t):
    people = ''.join(
        f'<circle cx="{x}" cy="{y}" r="{r}" fill="{a}" opacity="{o}"/>'
        f'<path d="M{x - r * 1.6:.0f} {y + r * 3.4:.0f}a{r * 1.6:.0f} {r * 1.6:.0f} 0 0 1 {r * 3.2:.0f} 0" fill="{a}" opacity="{o}"/>'
        for x, y, r, o in [(300, 170, 34, .45), (500, 170, 34, .45), (400, 150, 42, 1)])
    return frame(a, t, f'<rect x="170" y="100" width="460" height="270" rx="28" fill="#ffffff"/>' + people
                 + f'<path d="M250 340 H550" stroke="{a}" stroke-width="6" stroke-linecap="round" opacity=".25"/>')


def ready(a, t):
    return frame(a, t,
        f'<circle cx="400" cy="215" r="120" fill="#ffffff"/>'
        f'<circle cx="400" cy="215" r="120" fill="none" stroke="{a}" stroke-width="16" opacity=".18"/>'
        f'<path d="M400 95 A120 120 0 1 1 296 275" fill="none" stroke="{a}" stroke-width="16" stroke-linecap="round"/>'
        + check(402, 216, 100, a, 18)
        + f'<rect x="200" y="378" width="400" height="14" rx="7" fill="{a}" opacity=".15"/>'
        f'<rect x="200" y="378" width="290" height="14" rx="7" fill="{a}" opacity=".7"/>')


ART = {'welcome.svg': welcome, 'debian.svg': debian, 'learn.svg': learn, 'update.svg': update,
       'secure.svg': shield, 'community.svg': community, 'ready.svg': ready}


def render_video(accent, tint, target, seconds=8, fps=24):
    from PySide6.QtCore import QByteArray, QRectF
    from PySide6.QtGui import QGuiApplication, QImage, QPainter, QColor
    from PySide6.QtSvg import QSvgRenderer
    app = QGuiApplication.instance() or QGuiApplication(['corry-media'])
    with tempfile.TemporaryDirectory() as temp:
        count = seconds * fps
        for n in range(count):
            # A full sine period over the clip, so the video loops seamlessly.
            svg = welcome(accent, tint, 2 * math.pi * n / count)
            image = QImage(960, 540, QImage.Format_RGB32)
            image.fill(QColor('#ffffff'))
            painter = QPainter(image)
            QSvgRenderer(QByteArray(svg.encode())).render(painter, QRectF(0, 0, 960, 540))
            painter.end()
            image.save(f'{temp}/{n:04d}.png')
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-framerate', str(fps), '-i', f'{temp}/%04d.png',
                        '-c:v', 'libvpx-vp9', '-b:v', '0', '-crf', '40', '-row-mt', '1', '-pix_fmt', 'yuv420p',
                        '-an', str(target)], check=True)
    del app


def render_sound(target, seconds=48, rate=22050, seed=7):
    """A slow, quiet pad: four chords, soft attack and release, seamless loop."""
    random.seed(seed)
    chords = [[220.0, 277.18, 329.63], [196.0, 246.94, 293.66], [174.61, 220.0, 261.63], [196.0, 246.94, 329.63]]
    length = seconds * rate
    per = length // len(chords)
    samples = []
    for i in range(length):
        chord = chords[min(i // per, len(chords) - 1)]
        position = (i % per) / per
        envelope = math.sin(math.pi * position) ** 1.5
        value = sum(math.sin(2 * math.pi * f * i / rate) + 0.3 * math.sin(2 * math.pi * 2 * f * i / rate + 0.5)
                    for f in chord)
        shimmer = 0.15 * math.sin(2 * math.pi * 0.2 * i / rate)
        samples.append(int(4200 * envelope * (value / 4) * (1 + shimmer)))
    with tempfile.TemporaryDirectory() as temp:
        raw = Path(temp) / 'pad.wav'
        with wave.open(str(raw), 'wb') as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(rate)
            out.writeframes(struct.pack('<%dh' % len(samples), *samples))
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', str(raw), '-c:a', 'libvorbis', '-q:a', '1',
                        str(target)], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('distro')
    parser.add_argument('--no-video', action='store_true')
    parser.add_argument('--no-sound', action='store_true')
    args = parser.parse_args()
    folder = ROOT / 'config/distros' / args.distro
    colors = yaml.safe_load((folder / 'distro.yaml').read_text())['colors']
    (folder / 'slides').mkdir(exist_ok=True)
    (folder / 'media').mkdir(exist_ok=True)
    for name, draw in ART.items():
        (folder / 'slides' / name).write_text(draw(colors['accent'], colors['tint']))
    if not args.no_video:
        render_video(colors['accent'], colors['tint'], folder / 'media/welcome.webm')
    if not args.no_sound:
        render_sound(folder / 'media/ambient.ogg')
    print('Media written to', folder)


if __name__ == '__main__':
    sys.exit(main())
