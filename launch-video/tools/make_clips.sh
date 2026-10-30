#!/bin/bash
# Retimed footage clips + crisp stills from the virtual-clock recordings. Run from launch-video/.
R=/Volumes/Venus/GREIA_LAUNCH_VIDEO/rec; V=hf/assets/video; S=hf/assets/shots
clip(){ # name start speed dur
  ffmpeg -hide_banner -loglevel error -y -framerate 30 -start_number 0 -i $R/vv_$1/f%05d.png \
    -vf "trim=start=$2,setpts=(PTS-STARTPTS)/$3,crop=1920:1080:0:22,fps=30,trim=duration=$4,setpts=PTS-STARTPTS" \
    -c:v libx264 -crf 14 -pix_fmt yuv420p -g 8 -an $V/$5.mp4; }
clip paint 0.12 2.4 1.0 paint
clip stelle 0.12 2.6 1.0 stelle
clip orch 0.05 1.2 1.0 orchestra
clip orca 2.1 1.0 1.3 orca
clip delfino 1.25 1.0 1.2 delfino
clip enc 0.5 1.0 2.0 enc
for a in costruiamo_ponti acquario_magico treno_numeri pasticceria_magica; do last=$(ls $R/st_$a/f*.png | tail -1); python3 -c "
from PIL import Image; Image.open('$last').convert('RGB').save('$S/$a.jpg', quality=93)"; done
python3 -c "
from PIL import Image; Image.open('$R/vv_orch/f00001.png').convert('RGB').save('$S/orchestra_animali.jpg', quality=93)"
ls -la $V
python3 -c "
from PIL import Image
for n,src in (('home_stelle','$R/vv_stelle/f00000.png'),('home_paint','$R/vv_paint/f00000.png')):
    Image.open(src).convert('RGB').save('$S/%s.jpg'%n, quality=93)"

ffmpeg -hide_banner -loglevel error -y -i /Volumes/Venus/GREIA_LAUNCH_VIDEO/phone/app.mp4 -vf "scale=412:896,fps=30,tpad=stop_mode=clone:stop_duration=3.6" -c:v libx264 -crf 16 -pix_fmt yuv420p -g 15 -an $V/phone.mp4
