"""Offline, reproducible fallback preview. Requires system FFmpeg with flite/libass.

This cannot reconstruct the unavailable source footage. All narration is editorial.
"""
import json
import pathlib
import subprocess

ROOT = pathlib.Path(__file__).resolve().parents[1]
OUT = ROOT / 'artifacts'
OUT.mkdir(exist_ok=True)

def run(args):
    subprocess.run(args, cwd=ROOT, check=True)

def probe(path):
    return json.loads(subprocess.check_output([
        'ffprobe', '-v', 'error', '-show_format', '-show_streams',
        '-of', 'json', str(path)], cwd=ROOT))

scenes = [
    ('THE PREMISE', 'BITCOIN IN', 'MINECRAFT', [
        'Bitcoin trading, inside Minecraft.',
        'This is a source preview of a video by noah two fifty.']),
    ('THE BUILD', 'AN IN-GAME', 'TRADING TOOL', [
        "The creator's title says he built a way",
        'to trade Bitcoin in Minecraft.']),
    ('THE CHALLENGE', 'TRY TO MAKE', '$100', [
        'The description sets the challenge:',
        'make one hundred dollars inside the game.']),
    ('THE THUMBNAIL', 'A CHART IN', 'A BLOCK WORLD', [
        'The official thumbnail shows a large trading chart',
        'built into a Minecraft landscape.']),
    ('THE LIMITATION', 'THE OUTCOME', 'IS UNVERIFIED', [
        'The footage could not be retrieved,',
        'so the trades, reactions, and final result are unverified.']),
    ('SOURCE REQUIRED', 'HIGHLIGHT EDIT', 'INCOMPLETE', [
        'This is not the requested highlight edit.',
        'Original audio and a verified transcript are unavailable.']),
]

def stamp(t):
    cs = round(t * 100)
    return f'{cs//360000}:{cs//6000%60:02}:{cs//100%60:02}.{cs%100:02}'

header = '''[Script Info]
ScriptType: v4.00+
PlayResX: 720
PlayResY: 1280
WrapStyle: 0

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,DejaVu Sans,33,&H00FFFFFF,&H00FFFFFF,&H001B120B,&H001B120B,0,0,0,0,100,100,0,0,3,12,0,2,65,75,195,1
Style: Label,DejaVu Sans,21,&H00AAEECB,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,2,0,1,0,0,7,0,0,0,1
Style: Title,DejaVu Sans,54,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Accent,DejaVu Sans,54,&H007CEC9B,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1
Style: Small,DejaVu Sans,20,&H00C4BDB4,&H00FFFFFF,&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,7,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
'''
events = []
def event(start, end, style, text, pos=None):
    tag = r'{\fad(120,120)' + (f'\\pos({pos[0]},{pos[1]})' if pos else '') + '}'
    events.append(f'Dialogue: 0,{stamp(start)},{stamp(end)},{style},,0,0,0,,{tag}{text}')

event(0,45,'Small','SOURCE PREVIEW  /  NOT ORIGINAL FOOTAGE',(48,72))
event(0,45,'Small','Official source thumbnail',(48,755))
event(0,45,'Small','noah250  /  YouTube',(48,1140))
event(0,45,'Small','Editorial narration • source audio unavailable',(48,1174))

audio_paths = []
caption_records = []
for i, (label, title, accent, lines) in enumerate(scenes):
    start = i * 7.5
    event(start,start+7.5,'Label',f'{i+1:02}  /  {label}',(48,150))
    event(start,start+7.5,'Title',title,(48,203))
    event(start,start+7.5,'Accent',accent,(48,267))
    for j, line in enumerate(lines):
        k = i*2+j
        txt = OUT / f'narration-{k:02}.txt'
        txt.write_text(line)
        raw = OUT / f'voice-{k:02}.wav'
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','lavfi','-i',
             f'flite=textfile=artifacts/{txt.name}:voice=slt',str(raw)])
        duration = float(probe(raw)['format']['duration'])
        # Each line has a 3.75-second slot; speed up only if needed.
        tempo = max(1.0, duration / 3.4)
        ready = OUT / f'line-{k:02}.wav'
        run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(raw),
             '-af',f'atempo={tempo},aresample=48000,apad,atrim=duration=3.75',
             '-ac','2',str(ready)])
        audio_paths.append(ready)
        t = start+j*3.75
        event(t,t+3.75,'Caption',line)
        caption_records.append({'start':t,'end':t+3.75,'text':line})

(OUT/'captions.ass').write_text(header+'\n'.join(events)+'\n')
(OUT/'editorial-captions.json').write_text(json.dumps(caption_records,indent=2)+'\n')
(OUT/'audio-concat.txt').write_text(''.join(f"file '{p.name}'\n" for p in audio_paths))
run(['ffmpeg','-hide_banner','-loglevel','error','-y','-f','concat','-safe','0',
     '-i','artifacts/audio-concat.txt','-c:a','pcm_s16le','artifacts/narration.wav'])

graph = (
    '[0:v]drawbox=x=0:y=0:w=720:h=10:color=0x9bec7c:t=fill,'
    'drawbox=x=48:y=1100:w=612:h=3:color=0x314238:t=fill[base];'
    '[1:v]scale=1440:810,zoompan=z=1.025+0.015*sin(on/200):'
    "x='iw/2-iw/zoom/2':y='ih/2-ih/zoom/2':d=1:s=720x405:fps=30[thumb];"
    '[base][thumb]overlay=0:350,'
    "drawtext=fontfile=assets/DejaVuSans.ttf:text='':fontsize=1,"
    'ass=artifacts/captions.ass:fontsdir=assets[v]'
)
run(['ffmpeg','-hide_banner','-loglevel','error','-y',
     '-f','lavfi','-i','color=c=0x0b121b:s=720x1280:r=30:d=45',
     '-loop','1','-framerate','30','-i','assets/source-thumbnail.jpg',
     '-i','artifacts/narration.wav','-filter_complex',graph,
     '-map','[v]','-map','2:a','-t','45','-c:v','libx264','-preset','fast',
     '-crf','21','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-ar','48000',
     '-movflags','+faststart','-threads','2','artifacts/video.mp4'])
info = probe('artifacts/video.mp4')
(OUT/'probe.json').write_text(json.dumps(info,indent=2)+'\n')
video = next(s for s in info['streams'] if s['codec_type']=='video')
audio = next(s for s in info['streams'] if s['codec_type']=='audio')
assert video['codec_name']=='h264' and video['pix_fmt']=='yuv420p'
assert (video['width'],video['height']) == (720,1280)
assert audio['codec_name']=='aac'
assert abs(float(info['format']['duration'])-45)<0.1
assert (OUT/'video.mp4').stat().st_size < 64*1024*1024
print('PASS: 45 seconds, 720x1280, H.264 yuv420p, AAC, below 64 MiB')
