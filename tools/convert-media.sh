#!/usr/bin/env bash
# SPDX-License-Identifier: GPL-3.0-or-later
set -euo pipefail
[[ $# == 3 ]] || { echo 'Usage: convert-media.sh video|music INPUT OUTPUT.webm|OUTPUT.ogg' >&2; exit 2; }
mode=$1; input=$2; output=$3
[[ -f $input && ! -e $output ]] || { echo 'Input must exist and output must be a new file.' >&2; exit 1; }
case "$mode:$output" in
 video:*.webm) args=(-map 0:v:0 -map '0:a:0?' -vf 'scale=trunc(min(1280\,iw)/2)*2:-2' -c:v libvpx -b:v 1200k -pix_fmt yuv420p -c:a libvorbis -q:a 4) ;;
 music:*.ogg) args=(-vn -c:a libvorbis -q:a 4) ;;
 *) echo 'Use video with .webm output, or music with .ogg output.' >&2; exit 2 ;;
esac
ffmpeg -nostdin -n -i "$input" "${args[@]}" "$output"
