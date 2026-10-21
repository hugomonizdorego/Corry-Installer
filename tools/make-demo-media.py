#!/usr/bin/env python3
# SPDX-License-Identifier: CC0-1.0
"""Create original, compact welcome clips and a calm synthesized installation loop.
These example assets may be replaced independently for each distro.
"""
import math
from pathlib import Path
import struct
import subprocess
import tempfile
import wave
import yaml

ROOT=Path(__file__).resolve().parents[1]


def main():
    for folder in (ROOT/'config/distros').iterdir():
        config=yaml.safe_load((folder/'branding.yaml').read_text());name=config['product']['name'];accent=config['palette']['accent']
        with tempfile.TemporaryDirectory(prefix='corry-media-') as temp:
            temp=Path(temp);title=temp/'title.txt';title.write_text(name)
            video=folder/config['welcome']['video'];video.parent.mkdir(exist_ok=True)
            filters=("drawbox=x=40:y=40:w=560:h=280:color="+accent+":t=fill,"+
                "drawbox=x=65:y=65:w=510:h=230:color=0x163c39:t=fill,"+
                "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='Corry Installer':fontcolor=0xa8d4c6:fontsize=18:x=(w-text_w)/2:y=112,"+
                "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:textfile="+str(title)+":fontcolor=white:fontsize=30:x=(w-text_w)/2:y=155,"+
                "drawtext=fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:text='Learn. Create. Share.':fontcolor=0xcde4dd:fontsize=16:x=(w-text_w)/2:y=210,"+
                "fade=t=in:st=0:d=0.5,fade=t=out:st=5.5:d=0.5")
            subprocess.run(['ffmpeg','-y','-v','error','-f','lavfi','-i','color=c=0x102e2d:s=640x360:r=15:d=6','-vf',filters,'-an','-c:v','libvpx','-b:v','140k','-pix_fmt','yuv420p',str(video)],check=True)
            wav=temp/'loop.wav';rate=22050;notes=[60,64,67,72,67,64,60,55];samples=[]
            for i in range(rate*16):
                t=i/rate;local=t%2;note=notes[int(t/2)];f=440*2**((note-69)/12)
                envelope=min(1,local/.3,(2-local)/.6)*min(1,t/.8,(16-t)/.8)
                pad=(math.sin(2*math.pi*f*t)+.18*math.sin(4*math.pi*f*t))*.12
                bass=math.sin(2*math.pi*130.8128*t)*.045
                samples.append(struct.pack('<h',int(max(-1,min(1,(pad+bass)*envelope))*32767)))
            with wave.open(str(wav),'wb') as out:out.setparams((1,2,rate,0,'NONE','not compressed'));out.writeframes(b''.join(samples))
            music=folder/config['installation']['music'];music.parent.mkdir(exist_ok=True)
            subprocess.run(['ffmpeg','-y','-v','error','-i',str(wav),'-c:a','libvorbis','-q:a','2',str(music)],check=True)
            print(folder.name,video.stat().st_size,music.stat().st_size)

if __name__=='__main__':main()
