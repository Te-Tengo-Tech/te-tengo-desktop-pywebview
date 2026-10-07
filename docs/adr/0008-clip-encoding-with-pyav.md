# 0008. Encode clips with PyAV instead of the FFmpeg executable

**Status:** accepted (2026-10-07, task T10).

## Context
- Clips (6 s before and 6 s after an event, CA-18.1) were encoded by piping JPEG frames into an `ffmpeg` subprocess. That worked for the cloud service, whose Docker image installed FFmpeg.
- The agent is packaged with PyInstaller for the household PC (Windows first). It cannot assume `ffmpeg` in `PATH`, and shipping a separate `ffmpeg.exe` adds a binary to locate, update and sign.
- The clip format must not change: H.264 in MP4, `yuv420p`, even width and height (a 16:9 webcam at 480p gives 853 px).

## Decision
- Encode with **PyAV** (`av`), whose binary wheels for Windows, macOS and Linux bundle the FFmpeg libraries, including `libx264`. PyInstaller collects them like any other extension module.
- Keep the output identical in substance: `libx264`, `yuv420p`, the clip's average frame rate, odd sizes cropped to even, and **fragmented MP4** (`frag_keyframe+empty_moov`), as before, because it is written in one pass to memory without a temporary file.
- The function keeps its name and signature (`te_tengo_deteccion.clips.codificar.codificar_mp4`), so the capture loop does not change. The detection logic is untouched.

## Consequences
- No system dependency: `ffmpeg` is no longer needed in CI, in the cloud or on the household PC.
- The test opens the result with PyAV and checks the codec, pixel format, dimensions and frame count.
- **License:** the PyAV wheels bundle `libx264` (GPL-2.0-or-later) and other FFmpeg components. Distributing the packaged agent therefore carries GPL obligations for those libraries. This is acceptable for the thesis pilot but must be reviewed before any wider distribution (recorded in `docs/BLOCKERS.md`); the alternative is an LGPL build with OpenH264 or the platform encoder (Media Foundation on Windows).
- The wheels add about 60 MB to the packaged app.
