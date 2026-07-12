# Hackathon Demo Video

Final video:

- `final-demo.mp4`

Supporting files:

- `storyboard.md` — timing and scene plan.
- `narration-script.md` — optional voiceover script.
- `recording-notes.md` — capture and safety notes.
- `quality-check.md` — final export verification.
- `demo-runbook.md` — service startup and workflow.
- `assets/screens/` — full-HD screenshots captured from the live app workflow.
- `scripts/capture-workflow.codex-browser.js` — automation snippet used in the Codex browser runtime.
- `edit/render_video.py` — source used to render the MP4.
- `edit/rendering-notes.md` — render settings and FFmpeg-equivalent notes.

## Re-render

Install the local render helper if needed:

```powershell
python -m pip install imageio imageio-ffmpeg pillow
```

Then run:

```powershell
python hackathon-demo/edit/render_video.py
```

The script writes:

```text
hackathon-demo/final-demo.mp4
```

## Revise

To revise the video:

1. Start backend and frontend from `demo-runbook.md`.
2. Recapture screenshots into `hackathon-demo/assets/screens/`.
3. Edit scene durations or overlays in `hackathon-demo/edit/render_video.py`.
4. Re-run the render script.
