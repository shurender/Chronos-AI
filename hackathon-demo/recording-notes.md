# Recording Notes

- Recording method: clean browser viewport screenshots captured through the Codex in-app browser automation API.
- Viewport: 1920 x 1080.
- Editing method: programmatic MP4 render from full-HD screenshots using `hackathon-demo/edit/render_video.py`.
- Audio: none. The final video uses text overlays instead of narration.
- Secrets: no terminal, `.env`, API key, browser chrome, unrelated tabs, or local files are visible.
- Demo data: the workflow uses an isolated temporary backend data directory plus the app's sample/demo-safe ingestion path, so private repositories and personal files are not shown.
- External providers: local Fireworks/Tavily live-mode validation passed, but the recorded UI avoids exposing keys or provider diagnostics.
- Waiting periods: ingestion and simulation loading states are represented briefly and labelled as accelerated.
- Known limitation: the MP4 is a polished browser-capture edit, not a raw continuous webcam/screen recording.
- Safety correction: an earlier capture showed a personal uploaded CV citation and was discarded. The final render was recaptured from isolated demo storage.
