#!/bin/zsh
# Render a .blend from render.py with N Blender processes sharing the Metal GPU (Cycles),
# then encode the PNG frames to an H.264 MP4.
#   ./render.sh turntable.blend ../docs/media/blender/turntable.mp4 [N] [frames dir]
set -e
BLEND=${1:A}; OUTPUT=${2:?usage: render.sh file.blend out.mp4 [N] [frames dir]}
OUTPUT=${OUTPUT:A}; N=${3:-3}
FRAMES=${4:-${TMPDIR:-/tmp}/eink-frames/${BLEND:t:r}}
BLENDER=/Applications/Blender.app/Contents/MacOS/Blender

range=($("$BLENDER" -b "$BLEND" --python-expr \
    "import bpy; s = bpy.context.scene; print('RANGE', s.frame_start, s.frame_end, s.render.fps)" \
    2>/dev/null | awk '/^RANGE/ {print $2, $3, $4}'))
FIRST=$range[1]; LAST=$range[2]; FPS=$range[3]
rm -rf "$FRAMES" && mkdir -p "$FRAMES"

# Device choice is a user preference, not saved in the .blend: GPU only
SETUP='import bpy
prefs = bpy.context.preferences.addons["cycles"].preferences
prefs.compute_device_type = "METAL"
prefs.refresh_devices()
for device in prefs.get_devices_for_type("METAL"):
    device.use = device.type != "CPU"
bpy.context.scene.cycles.device = "GPU"'

started=$(date +%s)
count=$((LAST - FIRST + 1))
for i in $(seq 0 $((N - 1))); do
    s=$((FIRST + i * count / N)); e=$((FIRST + (i + 1) * count / N - 1))
    "$BLENDER" -b "$BLEND" --python-expr "$SETUP" \
        -o "$FRAMES/####" -s $s -e $e -a > "$FRAMES/log$i.txt" 2>&1 &
done
wait
seconds=$(( $(date +%s) - started ))
rendered=$(ls "$FRAMES"/*.png | wc -l | tr -d ' ')
echo "$rendered of $count frames in $seconds s ($(( seconds * 1000 / count )) ms/frame, N=$N)"
[ "$rendered" = "$count" ] || { echo "missing frames, see $FRAMES/log*.txt"; exit 1; }
ffmpeg -y -loglevel error -framerate $FPS -start_number $FIRST -i "$FRAMES/%04d.png" \
    -c:v libx264 -crf 18 -preset slow -pix_fmt yuv420p -movflags +faststart "$OUTPUT"
echo "wrote $OUTPUT"
