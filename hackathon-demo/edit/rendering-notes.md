# Rendering Notes

The final MP4 was rendered with:

```powershell
python hackathon-demo/edit/render_video.py
```

The script uses `imageio` and `imageio-ffmpeg`, which invokes a bundled FFmpeg binary internally. No system-level FFmpeg installation was available on this Windows machine.

Render settings:

- Container: MP4
- Codec: H.264 (`libx264`)
- Resolution: 1920 x 1080
- FPS: 30
- Audio: none
- Duration: 103 seconds

Equivalent conceptual FFmpeg flow:

```text
full-HD browser screenshots + title/final cards + text overlays
-> H.264 MP4 at 30 fps
-> hackathon-demo/final-demo.mp4
```
