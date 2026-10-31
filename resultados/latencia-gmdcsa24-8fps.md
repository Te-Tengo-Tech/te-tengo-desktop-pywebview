# Detection pipeline latency on this machine

- CPU: Apple M5 Pro (15 logical cores); OS: macOS-27.0.1-arm64-arm-64bit
- Python 3.11.16; MediaPipe 0.10.35; OpenCV 5.0.0; model `pose_landmarker_lite.task`, VIDEO mode, CPU delegate (XNNPACK)
- Videos: 160 (gmdcsa24), 1288 s of video, 10333 sampled frames at 8 fps; one process, videos in sequence

| Stage | Mean (ms) | Median (ms) | p95 (ms) | Max (ms) | Frames |
|---|---|---|---|---|---|
| decodificar | 1.63 | 0.85 | 5.68 | 108.19 | 10333 |
| preprocesar | 1.54 | 1.43 | 2.20 | 13.79 | 10333 |
| mediapipe | 7.56 | 6.43 | 12.10 | 61.72 | 10173 |
| clasificar | 0.04 | 0.04 | 0.06 | 1.07 | 10333 |

- First MediaPipe frame of each video (graph warm-up, excluded above): mean 14.9 ms, max 43.2 ms.
- Agent cost per frame (preprocess + MediaPipe + classifier): mean 9.13 ms, p95 14.15 ms: 7.3 % of the 125 ms budget per frame at 8 fps (MediaPipe may use several threads, so this is wall time, not single-core load).
- Wall-clock throughput including file decoding and landmarker creation: 68.9 sampled frames/s; real-time factor 8.6× (149.9 s for 1288 s of video).
